#!/system/bin/python
import json, os, re, shlex, subprocess, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST=os.getenv("BRIDGE_HOST","127.0.0.1")
PORT=int(os.getenv("BRIDGE_PORT","8765"))
TOKEN=os.getenv("BRIDGE_TOKEN","")
MAX_BODY=256*1024
MAX_OUTPUT=512*1024

BLOCKED=[
 r'(^|[;&|]\\s*)rm\\s+(-[^\\s]+\\s+)*-r[fF]\\s+/(?:\\s|$)',
 r'\\bmkfs(?:\\.[a-z0-9_+-]+)?\\b',
 r'\\bdd\\s+[^;&|]*\\bof=/dev/block\\b',
 r'\\bfastboot\\s+(?:flash|erase|format)\\b',
 r'\\bparted\\s+/dev/block\\b',
 r'\\bsgdisk\\s+.*(?:--zap|--delete)\\b',
 r'\\bshred\\s+.*?/dev/block\\b',
 r'\\breboot\\s+(?:bootloader|edl)\\b',
 r'\\b(?:factory[- ]reset|wipe userdata)\\b'
]
RX=[re.compile(x,re.I) for x in BLOCKED]

def audit(event,**kw):
    try:
        with open("/data/local/tmp/naang_bridge_audit.log","a") as f:
            f.write(json.dumps({"ts":time.time(),"event":event,**kw})+"\\n")
    except Exception: pass

def blocked(cmd):
    for rx in RX:
        if rx.search(cmd): return rx.pattern
    return None

def root(cmd,timeout=30):
    reason=blocked(cmd)
    if reason:
        audit("blocked",command=cmd,reason=reason)
        raise PermissionError("Blocked by on-device safety policy")
    p=subprocess.run(["su","-c",cmd],capture_output=True,text=True,
                     timeout=max(1,min(int(timeout),120)))
    return {"code":p.returncode,"stdout":p.stdout[-MAX_OUTPUT:],
            "stderr":p.stderr[-MAX_OUTPUT:]}

def info():
    keys=["ro.product.manufacturer","ro.product.model","ro.build.version.release",
          "ro.build.version.sdk","ro.build.version.security_patch",
          "ro.boot.verifiedbootstate","ro.boot.flash.locked"]
    return {k:subprocess.run(["getprop",k],capture_output=True,text=True).stdout.strip()
            for k in keys}

def dispatch(method,p):
    if method=="device.info": return info()
    if method=="shell.exec":
        c=str(p.get("command",""))
        if not c or len(c)>16384: raise ValueError("Invalid command")
        return root(c,p.get("timeout",30))
    if method=="system.logcat":
        n=max(1,min(int(p.get("lines",300)),5000))
        return root(f"logcat -d -t {n}",30)
    if method=="packages.list": return root("pm list packages -f")
    if method=="fs.read":
        path=str(p.get("path",""))
        if not path.startswith("/"): raise ValueError("Absolute path required")
        return root("cat -- "+shlex.quote(path),10)
    if method=="fs.list":
        path=str(p.get("path","/"))
        if not path.startswith("/"): raise ValueError("Absolute path required")
        return root("ls -la -- "+shlex.quote(path),10)
    if method=="policy.test":
        c=str(p.get("command","")); return {"blocked":bool(blocked(c)),"reason":blocked(c)}
    raise KeyError("Unknown method")

class H(BaseHTTPRequestHandler):
    def send_json(self,status,obj):
        b=json.dumps(obj,separators=(",",":")).encode()
        self.send_response(status); self.send_header("Content-Type","application/json")
        self.send_header("Content-Length",str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_POST(self):
        if TOKEN and self.headers.get("Authorization")!="Bearer "+TOKEN:
            self.send_json(401,{"error":"unauthorized"}); return
        try:
            n=int(self.headers.get("Content-Length","0"))
            if n<=0 or n>MAX_BODY: raise ValueError("invalid body size")
            req=json.loads(self.rfile.read(n))
            result=dispatch(req.get("method"),req.get("params") or {})
            self.send_json(200,{"jsonrpc":"2.0","id":req.get("id"),"result":result})
        except PermissionError as e: self.send_json(403,{"error":str(e)})
        except Exception as e: self.send_json(400,{"error":str(e)})
    def log_message(self,*a): pass

if __name__=="__main__":
    if not TOKEN: raise SystemExit("Set BRIDGE_TOKEN")
    audit("start",host=HOST,port=PORT)
    ThreadingHTTPServer((HOST,PORT),H).serve_forever()
