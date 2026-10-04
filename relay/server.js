import http from "node:http";
import crypto from "node:crypto";

const PORT = 8080;
const ADMIN_TOKEN = process.env.ADMIN_TOKEN;
const DEVICE_TOKEN = process.env.DEVICE_TOKEN;
if (!ADMIN_TOKEN || !DEVICE_TOKEN) throw new Error("ADMIN_TOKEN and DEVICE_TOKEN are required");

const devices = new Map();
const pending = new Map();
const ALLOWED_METHODS = new Set(["bridge.status","device.info","packages.list","process.list","system.logcat","app.launch","app.stop","app.current","ui.tap","ui.swipe","ui.keyevent","ui.back","ui.home","ui.recents","ui.text","ui.dump","ui.screenshot","fs.list","fs.read","policy.test"]);
const allowed = m => typeof m === "string" && ALLOWED_METHODS.has(m);
const auth = (req,t) => req.headers.authorization === "Bearer " + t;
const json = (res,status,obj) => { const b=JSON.stringify(obj); res.writeHead(status,{"content-type":"application/json","content-length":Buffer.byteLength(b)}); res.end(b); };
const body = req => new Promise((resolve,reject)=>{let b="";req.on("data",c=>{b+=c;if(b.length>65536)req.destroy()});req.on("end",()=>{try{resolve(b?JSON.parse(b):{})}catch{reject(new Error("invalid JSON"))}});req.on("error",reject)});
const id = () => crypto.randomBytes(16).toString("hex");

function state(device){let s=devices.get(device);if(!s){s={queue:[],waiters:[],online:false,lastSeen:0};devices.set(device,s)}return s}
function sendDevice(device,request){
  const s=devices.get(device);
  if(!s||!s.online) throw new Error("device offline");
  const rid=id();
  return new Promise((resolve,reject)=>{
    const timer=setTimeout(()=>{pending.delete(rid);reject(new Error("device timeout"))},30000);
    pending.set(rid,{resolve,timer});
    s.queue.push({...request,id:rid});
    if(s.waiters.length){const w=s.waiters.shift();clearTimeout(w.timer);w.resolve(s.queue.shift())}
  });
}

const server=http.createServer(async(req,res)=>{
  try{
    if(req.method==="GET"&&req.url==="/health"){
      return json(res,200,{ok:true,devices:[...devices].filter(([,s])=>s.online).map(([d])=>d)});
    }
    if(req.method==="POST"&&req.url==="/device.call"){
      if(!auth(req,ADMIN_TOKEN))return json(res,401,{error:"unauthorized"});
      const x=await body(req);
      if(x.action!=="device.call"||typeof x.device!=="string"||!allowed(x.method))return json(res,400,{error:"invalid request"});
      return json(res,200,{ok:true,result:await sendDevice(x.device,{jsonrpc:"2.0",method:x.method,params:x.params||{}})});
    }
    if(req.method==="POST"&&req.url==="/device/poll"){
      if(!auth(req,DEVICE_TOKEN))return json(res,401,{error:"unauthorized"});
      const x=await body(req);
      if(typeof x.device!=="string"||!x.device)return json(res,400,{error:"invalid device"});
      const s=state(x.device);s.online=true;s.lastSeen=Date.now();
      if(s.queue.length)return json(res,200,s.queue.shift());
      await new Promise(resolve=>{const timer=setTimeout(()=>{const i=s.waiters.findIndex(w=>w.resolve===resolve);if(i>=0)s.waiters.splice(i,1);resolve()},20000);s.waiters.push({resolve,timer})});
      if(s.queue.length)return json(res,200,s.queue.shift());
      return res.writeHead(204).end();
    }
    if(req.method==="POST"&&req.url==="/device/result"){
      if(!auth(req,DEVICE_TOKEN))return json(res,401,{error:"unauthorized"});
      const x=await body(req);
      if(typeof x.device!=="string"||typeof x.id!=="string")return json(res,400,{error:"invalid result"});
      const s=state(x.device);s.online=true;s.lastSeen=Date.now();
      const p=pending.get(x.id);
      if(p){pending.delete(x.id);clearTimeout(p.timer);p.resolve(x)}
      return json(res,200,{ok:true});
    }
    return json(res,404,{error:"not found"});
  }catch(e){return json(res,502,{error:e.message||"server error"})}
});
setInterval(()=>{const cutoff=Date.now()-45000;for(const[,s]of devices)if(s.lastSeen<cutoff)s.online=false},10000);
server.listen(PORT,()=>console.log("NAANG RELAY HTTP polling listening on :"+PORT));
