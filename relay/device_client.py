#!/usr/bin/env python3
"""HTTP polling device transport for the typed localhost Android bridge."""
import http.client,json,os,ssl,time

def load_relay_env():
    try:
        with open("/data/adb/naang_phone_bridge/relay.env",encoding="utf-8") as f:
            for line in f:
                line=line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k,v=line.split("=",1);os.environ[k.strip()]=v.strip()
    except OSError: pass
load_relay_env()
RELAY_HOST=os.getenv("RELAY_HOST");RELAY_PORT=int(os.getenv("RELAY_PORT","443"))
DEVICE_TOKEN=os.getenv("DEVICE_TOKEN");DEVICE_ID=os.getenv("DEVICE_ID")
BRIDGE_HOST=os.getenv("BRIDGE_HOST","127.0.0.1");BRIDGE_PORT=int(os.getenv("BRIDGE_PORT","8765"))
BRIDGE_TOKEN_FILE=os.getenv("BRIDGE_TOKEN_FILE","/data/adb/naang_phone_bridge/token")
ALLOWED_METHODS=frozenset(["bridge.status","device.info","packages.list","process.list","system.logcat","app.launch","app.stop","app.current","ui.tap","ui.swipe","ui.keyevent","ui.back","ui.home","ui.recents","ui.text","ui.dump","ui.screenshot","fs.list","fs.read","policy.test"])
def is_allowed_method(method): return isinstance(method,str) and method in ALLOWED_METHODS
def read_bridge_token():
    with open(BRIDGE_TOKEN_FILE,encoding="utf-8") as f:return f.read().strip()
def relay_post(path,obj,timeout):
    c=http.client.HTTPSConnection(RELAY_HOST,RELAY_PORT,timeout=timeout,context=ssl.create_default_context());b=json.dumps(obj,separators=(",",":")).encode()
    try:
        c.request("POST",path,body=b,headers={"Authorization":"Bearer "+DEVICE_TOKEN,"Content-Type":"application/json","Content-Length":str(len(b))})
        r=c.getresponse();return r.status,r.read(1024*1024)
    finally:c.close()
def call_local_bridge(method,params):
    if not is_allowed_method(method):raise ValueError("method is not allowed")
    b=json.dumps({"method":method,"params":params or {}}).encode();c=http.client.HTTPConnection(BRIDGE_HOST,BRIDGE_PORT,timeout=35)
    try:
        c.request("POST","/rpc",body=b,headers={"Authorization":"Bearer "+read_bridge_token(),"Content-Type":"application/json","Content-Length":str(len(b))})
        r=c.getresponse();raw=r.read(1024*1024)
        if r.status!=200:raise RuntimeError("bridge HTTP %d: %s"%(r.status,raw.decode("utf-8","replace")[:4096]))
        x=json.loads(raw.decode())
        if not x.get("ok"):raise RuntimeError(x.get("error","bridge request failed"))
        return x.get("result")
    finally:c.close()
def serve_once():
    status,raw=relay_post("/device/poll",{"device":DEVICE_ID},25)
    if status==204:return
    if status!=200:raise RuntimeError("relay poll HTTP %d: %s"%(status,raw.decode("utf-8","replace")[:4096]))
    m=json.loads(raw.decode());rid=m.get("id");method=m.get("method");params=m.get("params") or {}
    if not rid or not is_allowed_method(method):out={"id":rid,"ok":False,"error":"method is not allowed"}
    else:
        try:out={"id":rid,"ok":True,"result":call_local_bridge(method,params)}
        except Exception as e:out={"id":rid,"ok":False,"error":str(e)}
    relay_post("/device/result",{"device":DEVICE_ID,**out},15)
def main():
    if not RELAY_HOST or not DEVICE_TOKEN or not DEVICE_ID:raise RuntimeError("relay configuration incomplete")
    while True:
        try:serve_once()
        except Exception:time.sleep(5)
if __name__=="__main__":main()
