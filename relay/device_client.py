#!/usr/bin/env python3
"""Outbound device transport for the typed localhost Android bridge."""
import http.client,json,os,socket,ssl,time

def load_relay_env():
    try:
        with open("/data/adb/naang_phone_bridge/relay.env",encoding="utf-8") as f:
            for line in f:
                line=line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k,v=line.split("=",1); os.environ[k.strip()]=v.strip()
    except OSError: pass
load_relay_env()

RELAY_HOST=os.getenv("RELAY_HOST")
RELAY_PORT=int(os.getenv("RELAY_PORT","443"))
RELAY_PATH=os.getenv("RELAY_PATH","/device")
DEVICE_TOKEN=os.getenv("DEVICE_TOKEN")
DEVICE_ID=os.getenv("DEVICE_ID")
BRIDGE_HOST=os.getenv("BRIDGE_HOST","127.0.0.1")
BRIDGE_PORT=int(os.getenv("BRIDGE_PORT","8765"))
BRIDGE_TOKEN_FILE=os.getenv("BRIDGE_TOKEN_FILE","/data/adb/naang_phone_bridge/token")
ALLOWED_METHODS=frozenset({"bridge.status","device.info","packages.list","process.list","system.logcat","app.launch","app.stop","app.current","ui.tap","ui.swipe","ui.keyevent","ui.back","ui.home","ui.recents","ui.text","ui.dump","ui.screenshot","fs.list","fs.read","policy.test"})

def is_allowed_method(m): return isinstance(m,str) and m in ALLOWED_METHODS
def read_bridge_token():
    with open(BRIDGE_TOKEN_FILE,encoding="utf-8") as f:return f.read().strip()
def call_local_bridge(method,params):
    if not is_allowed_method(method): raise ValueError("method is not allowed")
    body=json.dumps({"method":method,"params":params or {}}).encode()
    c=http.client.HTTPConnection(BRIDGE_HOST,BRIDGE_PORT,timeout=35)
    try:
        c.request("POST","/rpc",body=body,headers={"Authorization":"Bearer "+read_bridge_token(),"Content-Type":"application/json","Content-Length":str(len(body))})
        r=c.getresponse(); raw=r.read(1024*1024)
        if r.status!=200: raise RuntimeError("bridge HTTP %d: %s"%(r.status,raw.decode("utf-8","replace")[:4096]))
        x=json.loads(raw.decode())
        if not x.get("ok"): raise RuntimeError(x.get("error","bridge request failed"))
        return x.get("result")
    finally:c.close()
def connect_relay():
    if not RELAY_HOST or not DEVICE_TOKEN or not DEVICE_ID: raise RuntimeError("relay configuration incomplete")
    raw=socket.create_connection((RELAY_HOST,RELAY_PORT),timeout=20)
    s=ssl.create_default_context().wrap_socket(raw,server_hostname=RELAY_HOST)
    s.sendall(("GET %s HTTP/1.1\r\nHost: %s\r\nAuthorization: Bearer %s\r\nUpgrade: naang-device\r\nConnection: Upgrade\r\n\r\n"%(RELAY_PATH,RELAY_HOST,DEVICE_TOKEN)).encode())
    h=s.recv(4096)
    if b"101 Switching Protocols" not in h: s.close(); raise RuntimeError("relay upgrade failed")
    s.sendall((json.dumps({"type":"hello","device":DEVICE_ID})+"\n").encode()); return s
def serve_once():
    s=connect_relay(); buf=b""
    try:
        while True:
            chunk=s.recv(65536)
            if not chunk: raise RuntimeError("relay disconnected")
            buf+=chunk
            while b"\n" in buf:
                line,buf=buf.split(b"\n",1)
                if not line.strip():continue
                m=json.loads(line.decode()); rid=m.get("id"); method=m.get("method"); params=m.get("params") or {}
                if not rid or not is_allowed_method(method): out={"id":rid,"ok":False,"error":"method is not allowed"}
                else:
                    try:out={"id":rid,"ok":True,"result":call_local_bridge(method,params)}
                    except Exception as e:out={"id":rid,"ok":False,"error":str(e)}
                s.sendall((json.dumps(out,separators=(",",":"))+"\n").encode())
    finally:s.close()
def main():
    while True:
        try:serve_once()
        except Exception:time.sleep(5)
if __name__=="__main__":main()
