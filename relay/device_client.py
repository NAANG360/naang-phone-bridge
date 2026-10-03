#!/usr/bin/env python3
"""Outbound transport prototype. Android bridge remains the policy authority."""
import json,os,socket,ssl
RELAY_HOST=os.environ["RELAY_HOST"]; RELAY_PORT=int(os.getenv("RELAY_PORT","443")); DEVICE_TOKEN=os.environ["DEVICE_TOKEN"]; DEVICE_ID=os.environ["DEVICE_ID"]
def main():
 raw=socket.create_connection((RELAY_HOST,RELAY_PORT),timeout=20)
 s=ssl.create_default_context().wrap_socket(raw,server_hostname=RELAY_HOST)
 s.sendall(("GET /device HTTP/1.1\r\nHost: "+RELAY_HOST+"\r\nAuthorization: Bearer "+DEVICE_TOKEN+"\r\nUpgrade: naang-device\r\nConnection: Upgrade\r\n\r\n").encode())
 if b"101 Switching Protocols" not in s.recv(4096): raise RuntimeError("relay upgrade failed")
 s.sendall((json.dumps({"type":"hello","device":DEVICE_ID})+"\n").encode())
 while s.recv(65536): pass
if __name__=="__main__": main()
