#!/usr/bin/env python3
import json, os, re, subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST=os.getenv("BRIDGE_HOST","127.0.0.1")
PORT=int(os.getenv("BRIDGE_PORT","8765"))
TOKEN_FILE=os.getenv("BRIDGE_TOKEN_FILE","/data/adb/naang_phone_bridge/token")
MAX_BODY=256*1024

def token():
    try:
        with open(TOKEN_FILE,"r",encoding="utf-8") as f: return f.read().strip()
    except OSError: return ""

def run(args, timeout=30):
    p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=max(1,min(int(timeout),120)))
    return {"code":p.returncode,"stdout":p.stdout[-524288:],"stderr":p.stderr[-524288:]}

PKG_RE=re.compile(r"^[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+$")
def pkg(v):
    if not isinstance(v,str) or not PKG_RE.fullmatch(v): raise ValueError("invalid package")
    return v
def integer(v,lo,hi,name):
    if isinstance(v,bool) or not isinstance(v,int) or not lo<=v<=hi: raise ValueError("invalid "+name)
    return v

def call(method,p):
    if method=="device.info":
        return {k:subprocess.run(["getprop",k],capture_output=True,text=True).stdout.strip() for k in
                ("ro.product.manufacturer","ro.product.model","ro.build.version.release","ro.build.version.sdk")}
    if method=="packages.list": return run(["cmd","package","list","packages"])
    if method=="process.list": return run(["ps","-A"])
    if method=="system.logcat": return run(["logcat","-d","-t",str(integer(p.get("lines",200),1,2000,"lines"))])
    if method=="app.launch": return run(["monkey","-p",pkg(p.get("package")),"-c","android.intent.category.LAUNCHER","1"])
    if method=="app.stop": return run(["am","force-stop",pkg(p.get("package"))])
    if method=="ui.tap":
        x=integer(p.get("x"),0,10000,"x"); y=integer(p.get("y"),0,10000,"y")
        return run(["input","tap",str(x),str(y)])
    if method=="ui.swipe":
        a=[integer(p.get(k),0,10000,k) for k in ("x1","y1","x2","y2")]
        d=integer(p.get("duration_ms",300),1,10000,"duration_ms")
        return run(["input","swipe",*(str(x) for x in a),str(d)])
    if method=="ui.keyevent": return run(["input","keyevent",str(integer(p.get("keycode"),0,300,"keycode"))])
    if method=="ui.text":
        t=p.get("text")
        if not isinstance(t,str) or len(t)>4096: raise ValueError("invalid text")
        return run(["input","text",t.replace("%","%25").replace(" ","%s").replace("&","\\&")])
    if method=="fs.list":
        path=p.get("path")
        if not isinstance(path,str) or not any(path.startswith(x) for x in ("/sdcard/","/storage/emulated/0/","/data/local/tmp/")):
            raise ValueError("path outside permitted locations")
        return run(["ls","-la",path])
    if method=="policy.test":
        c=p.get("command")
        if not isinstance(c,str) or len(c)>8192: raise ValueError("invalid command")
        blocked=[r"rm\s+-rf\s+/(?:\s|$)",r"mkfs(?:\.[A-Za-z0-9_-]+)?\s+/dev/block",r"dd\s+.*of=/dev/block",
                 r"fastboot\s+(?:flash|erase|format)",r"parted\s+/dev/block",r"sgdisk\s+.*(?:zap|delete)",
                 r"shred\s+.*?/dev/block",r"reboot\s+(?:bootloader|edl)",r"factory.?reset",r"wipe\s+(?:data|userdata)"]
        return {"allowed":not any(re.search(x,c,re.I) for x in blocked)}
    raise ValueError("unknown method")

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def send(self,status,obj):
        raw=json.dumps(obj,separators=(",",":")).encode()
        self.send_response(status); self.send_header("Content-Type","application/json")
        self.send_header("Content-Length",str(len(raw))); self.end_headers(); self.wfile.write(raw)
    def do_POST(self):
        if self.path!="/rpc": return self.send(404,{"ok":False,"error":"not found"})
        if self.headers.get("Authorization")!="Bearer "+token(): return self.send(401,{"ok":False,"error":"unauthorized"})
        try:
            n=int(self.headers.get("Content-Length","0"))
            if n<1 or n>MAX_BODY: raise ValueError("invalid body size")
            b=json.loads(self.rfile.read(n))
            self.send(200,{"ok":True,"result":call(b.get("method"),b.get("params") or {})})
        except Exception as e: self.send(400,{"ok":False,"error":str(e)})

if __name__=="__main__": ThreadingHTTPServer((HOST,PORT),Handler).serve_forever()
