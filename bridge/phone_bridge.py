#!/usr/bin/env python3
import json, os, re, subprocess, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST=os.getenv("BRIDGE_HOST","127.0.0.1")
PORT=int(os.getenv("BRIDGE_PORT","8765"))
TOKEN=os.getenv("BRIDGE_TOKEN","")
MAX_BODY=256*1024
MAX_OUTPUT=512*1024
AUDIT="/data/local/tmp/naang_bridge_audit.log"

BLOCKED=[
 r"(^|\s)rm\s+(-[A-Za-z]*\s+)*-[A-Za-z]*r[A-Za-z]*\s+/(\s|$)",
 r"(^|\s)mkfs(\.|\s)",
 r"\bdd\b.*\bof=/dev/block/",
 r"\bfastboot\s+(flash|erase|format)\b",
 r"\bparted\s+/dev/block",
 r"\bsgdisk\b.*\b(zap|delete)\b",
 r"\bshred\b.*?/dev/block/",
 r"\breboot\s+(bootloader|edl)\b",
 r"\b(factory-reset|wipe\s+userdata)\b",
]
BLOCKED_RX=[re.compile(x,re.I) for x in BLOCKED]
SAFE_FS_PREFIXES=("/sdcard/","/storage/emulated/0/","/data/local/tmp/","/data/local/naang_bridge/")

def blocked(cmd):
    return any(rx.search(cmd) for rx in BLOCKED_RX)

def audit(method, ok, detail=""):
    try:
        with open(AUDIT,"a",encoding="utf-8") as f:
            f.write(json.dumps({"ts":time.time(),"method":method,"ok":ok,"detail":detail[:500]},separators=(",",":"))+"\n")
    except Exception:
        pass

def root(cmd, timeout=30):
    if blocked(cmd):
        return {"code":126,"stdout":"","stderr":"blocked by on-device safety policy"}
    timeout=max(1,min(int(timeout),120))
    p=subprocess.run(["su","-c",cmd],capture_output=True,text=True,timeout=timeout)
    out=p.stdout[-MAX_OUTPUT:]
    err=p.stderr[-MAX_OUTPUT:]
    return {"code":p.returncode,"stdout":out,"stderr":err}

def prop(name):
    p=subprocess.run(["getprop",name],capture_output=True,text=True)
    return p.stdout.strip()

def info():
    return {k:prop(k) for k in (
        "ro.product.manufacturer","ro.product.model","ro.build.version.release",
        "ro.build.version.sdk","ro.build.version.security_patch",
        "ro.boot.verifiedbootstate","ro.boot.flash.locked")}

def safe_path(path):
    if not isinstance(path,str) or len(path)>2048 or "\x00" in path: return False
    if not path.startswith("/"): return False
    return any(path==p.rstrip("/") or path.startswith(p) for p in SAFE_FS_PREFIXES)

def fs_read(path, max_bytes=65536):
    if not safe_path(path): return {"error":"path denied by filesystem policy"}
    n=max(1,min(int(max_bytes),MAX_OUTPUT))
    r=root("python3 -c "+repr("import sys; p=sys.argv[1]; n=int(sys.argv[2]); sys.stdout.buffer.write(open(p,'rb').read(n))")+" "+repr(path)+" "+str(n),30)
    return r

def fs_list(path):
    if not safe_path(path): return {"error":"path denied by filesystem policy"}
    return root("ls -la -- "+subprocess.list2cmdline([path]),30)

def dispatch(method, params):
    params=params or {}
    if method=="device.info": return info()
    if method=="policy.test":
        cmd=str(params.get("command",""))
        return {"blocked":blocked(cmd)}
    if method=="shell.exec":
        cmd=str(params.get("command",""))
        if not cmd or len(cmd)>8192: return {"error":"invalid command"}
        return root(cmd,params.get("timeout",30))
    if method=="system.logcat":
        lines=max(1,min(int(params.get("lines",200)),2000))
        return root("logcat -d -t "+str(lines),30)
    if method=="packages.list":
        return root("pm list packages",30)
    if method=="process.list":
        return root("ps -A",30)
    if method=="fs.read":
        return fs_read(params.get("path",""),params.get("max_bytes",65536))
    if method=="fs.list":
        return fs_list(params.get("path",""))
    if method=="app.launch":
        pkg=str(params.get("package",""))
        if not re.fullmatch(r"[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+",pkg): return {"error":"invalid package"}
        return root("monkey -p "+pkg+" -c android.intent.category.LAUNCHER 1",30)
    if method=="app.stop":
        pkg=str(params.get("package",""))
        if not re.fullmatch(r"[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+",pkg): return {"error":"invalid package"}
        return root("am force-stop "+pkg,30)
    return {"error":"unknown method"}

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def do_POST(self):
        if TOKEN and self.headers.get("Authorization")!="Bearer "+TOKEN:
            self.send_error(401); return
        try: n=int(self.headers.get("Content-Length","-1"))
        except ValueError: self.send_error(400); return
        if n<0 or n>MAX_BODY: self.send_error(413); return
        try:
            req=json.loads(self.rfile.read(n))
            rid=req.get("id")
            method=req.get("method","")
            result=dispatch(method,req.get("params",{}))
            ok=not (isinstance(result,dict) and "error" in result and result.get("error")=="unknown method")
            audit(method,ok)
            body={"jsonrpc":"2.0","id":rid,"result":result}
        except subprocess.TimeoutExpired:
            body={"jsonrpc":"2.0","id":None,"error":{"code":-32001,"message":"command timeout"}}
        except Exception as e:
            audit("request",False,type(e).__name__)
            body={"jsonrpc":"2.0","id":None,"error":{"code":-32000,"message":"request failed"}}
        raw=json.dumps(body,separators=(",",":")).encode()
        self.send_response(200); self.send_header("Content-Type","application/json")
        self.send_header("Content-Length",str(len(raw))); self.end_headers(); self.wfile.write(raw)

if __name__=="__main__":
    if not TOKEN:
        raise SystemExit("BRIDGE_TOKEN is required")
    ThreadingHTTPServer((HOST,PORT),Handler).serve_forever()
