import http from "node:http";
import crypto from "node:crypto";

const PORT=8787;
const ADMIN_TOKEN=process.env.ADMIN_TOKEN;
const DEVICE_TOKEN=process.env.DEVICE_TOKEN;
if(!ADMIN_TOKEN||!DEVICE_TOKEN) throw new Error("ADMIN_TOKEN and DEVICE_TOKEN are required");
const devices=new Map(); const pending=new Map();
const ALLOWED_METHODS=new Set([
  "bridge.status","device.info","packages.list","process.list","system.logcat",
  "app.launch","app.stop","app.current",
  "ui.tap","ui.swipe","ui.keyevent","ui.back","ui.home","ui.recents","ui.text","ui.dump","ui.screenshot",
  "fs.list","fs.read","policy.test"
]);
const isAllowedMethod=(method)=>typeof method==="string"&&ALLOWED_METHODS.has(method);
const json=(res,status,obj)=>{const b=JSON.stringify(obj);res.writeHead(status,{"content-type":"application/json","content-length":Buffer.byteLength(b)});res.end(b)};
const auth=(req,token)=>req.headers.authorization==="Bearer "+token;
function id(){return crypto.randomBytes(16).toString("hex")}
function sendDevice(device,request){
 const socket=devices.get(device); if(!socket) throw new Error("device offline");
 const requestId=id();
 return new Promise((resolve,reject)=>{const timer=setTimeout(()=>{pending.delete(requestId);reject(new Error("device timeout"))},30000);pending.set(requestId,{resolve,reject,timer});socket.write(JSON.stringify({...request,id:requestId})+"\n")});
}
const server=http.createServer((req,res)=>{
 if(req.method==="GET"&&req.url==="/health") return json(res,200,{ok:true,devices:[...devices.keys()]});
 if(req.method!=="POST") return json(res,405,{error:"method not allowed"});
 if(!auth(req,ADMIN_TOKEN)) return json(res,401,{error:"unauthorized"});
 let body=""; req.on("data",c=>{body+=c;if(body.length>65536) req.destroy()});
 req.on("end",async()=>{try{const x=JSON.parse(body);if(x.action==="device.call"){if(typeof x.device!=="string"||!isAllowedMethod(x.method))return json(res,400,{error:"invalid request"});return json(res,200,{ok:true,result:await sendDevice(x.device,{jsonrpc:"2.0",method:x.method,params:x.params||{}})});}return json(res,400,{error:"unknown action"})}catch(e){return json(res,502,{error:e.message})}});
});
server.on("upgrade",(req,socket)=>{
 if(req.url!=="/device"||req.headers.authorization!=="Bearer "+DEVICE_TOKEN)return socket.destroy();
 socket.write("HTTP/1.1 101 Switching Protocols\r\nUpgrade: naang-device\r\nConnection: Upgrade\r\n\r\n");
 let device="";let buf="";socket.on("data",chunk=>{buf+=chunk.toString();let i;while((i=buf.indexOf("\n"))>=0){const line=buf.slice(0,i).trim();buf=buf.slice(i+1);if(!line)continue;try{const msg=JSON.parse(line);if(msg.type==="hello"){device=msg.device;if(device)devices.set(device,socket);continue}if(msg.id&&pending.has(msg.id)){const p=pending.get(msg.id);pending.delete(msg.id);clearTimeout(p.timer);p.resolve(msg)}}catch{}}});
 socket.on("close",()=>{if(device&&devices.get(device)===socket)devices.delete(device)});socket.on("error",()=>{if(device&&devices.get(device)===socket)devices.delete(device)});
});
server.listen(PORT,()=>console.log("NAANG RELAY v2 listening on :"+PORT));
