import {createHash,randomUUID} from "node:crypto";
import {z} from "zod";
import {settings,equal,sign,authenticated,sameOrigin,sessionCookie,response,readBody} from "../../server/security.mjs";
import {store,put,recent,trim,recordKey} from "../../server/storage.mjs";
const uuid=z.string().uuid();
const alert=z.object({id:z.string().max(160),tick:z.number(),severity:z.string().max(20),title:z.string().max(200),summary:z.string().max(1000)}).passthrough();
const schema=z.object({
 snapshot:z.object({schema:z.literal(1),captured_at:z.string().max(50),state:z.string().max(40),tick:z.number().nonnegative(),citizens:z.array(z.object({id:z.string(),name:z.string(),active:z.boolean()}).passthrough()).max(500),alerts:z.array(alert).max(120),metrics:z.array(z.record(z.unknown())).max(120)}).passthrough().optional(),
 report:z.object({id:uuid,text:z.string().max(12000),mode:z.string().max(50),tick:z.number()}).optional(),
 picture:z.object({id:uuid,base64:z.string().max(1100000),captured_at:z.number(),tick:z.number()}).optional(),
 answers:z.array(z.object({id:uuid,text:z.string().max(12000),mode:z.string().max(50),tick:z.number()})).max(5).default([])
});
export async function handle(req,dbFactory=store,env=process.env){
 let keys;try{keys=settings(env)}catch{return response({error:"Monitoring is not configured. Set the three server-side Observatory secrets in Netlify and redeploy."},503)}
 const url=new URL(req.url),path=url.pathname.replace(/^\/.netlify\/functions\/api/,"/api"),mode=url.searchParams.get("mode");
 if(path==="/api/auth/session")return response({authenticated:authenticated(req,keys.session)},authenticated(req,keys.session)?200:401);
 if(path==="/api/auth/login"||path==="/api/auth/logout"){
  if(req.method!=="POST")return response({error:"POST required"},405);
  if(!sameOrigin(req))return response({error:"Same-origin requests only"},403);
  if(path.endsWith("/logout"))return response({ok:true},200,{"Set-Cookie":sessionCookie("",0)});
  let body;try{body=await readBody(req,1024)}catch{return response({error:"Invalid sign-in request"},400)}
  if(typeof body?.key!=="string"||body.key.length>256||!equal(body.key,keys.admin))return response({error:"Invalid owner access key"},401);
  return response({ok:true},200,{"Set-Cookie":sessionCookie(sign(keys.session))});
 }
 const uploading=path==="/api/observer"&&req.method==="POST"&&mode==="ingest";
 if(uploading){if(!equal(req.headers.get("authorization")||"","Bearer "+keys.ingest))return response({error:"Invalid connector token"},401)}
 else if(!authenticated(req,keys.session))return response({error:"Session expired. Reload this page to sign in."},401);
 try{
  const db=dbFactory();
  if(path.startsWith("/api/picture/")){
   if(req.method!=="GET")return response({error:"GET required"},405);
   const id=path.slice("/api/picture/".length);if(!uuid.safeParse(id).success)return response({error:"Invalid picture ID"},400);
   const image=await db.get("jpeg/"+id,{type:"arrayBuffer"});return image?new Response(image,{headers:{"Content-Type":"image/jpeg","Cache-Control":"private, no-store","X-Content-Type-Options":"nosniff"}}):response({error:"Capture expired"},404);
  }
  if(path!=="/api/observer")return response({error:"Not found"},404);
  if(req.method==="GET"){const [snapshot,reports,pictures,questions,alerts]=await Promise.all([db.get("snapshot/latest",{type:"json"}),recent(db,"report",48),recent(db,"picture",24),recent(db,"question",30),recent(db,"alert",200)]);return response({snapshot,reports,pictures,questions,alerts,server_time:Date.now()})}
  if(uploading){
   let data;try{data=schema.parse(await readBody(req,1500000))}catch{return response({error:"Invalid or oversized monitoring payload"},400)}
   let jpeg;if(data.picture){jpeg=Buffer.from(data.picture.base64,"base64");if(jpeg.length>800000||jpeg[0]!==255||jpeg[1]!==216||jpeg[2]!==255)return response({error:"JPEG required"},400)}
   if(data.snapshot){await put(db,"snapshot","latest",data.snapshot);for(const a of data.snapshot.alerts){const id=createHash("sha256").update(a.id).digest("hex");if(!await db.get(recordKey("alert",id),{type:"json"}))await put(db,"alert",id,a)}await trim(db,"alert",500)}
   if(data.report){await put(db,"report",data.report.id,data.report);await trim(db,"report",96)}
   if(data.picture){await db.set("jpeg/"+data.picture.id,jpeg);await put(db,"picture",data.picture.id,{tick:data.picture.tick,captured_at:data.picture.captured_at});await trim(db,"picture",24)}
   for(const a of data.answers){const q=await db.get(recordKey("question",a.id),{type:"json"});if(q?.status==="pending"&&Date.now()-q.received_at<900000)await put(db,"question",a.id,{...q,status:"answered",answer:a.text,mode:a.mode,tick:a.tick},q.received_at)}
   return response({accepted:true,questions:(await recent(db,"question",100)).filter(q=>q.status==="pending"&&Date.now()-q.received_at<900000).slice(0,3)});
  }
  if(req.method!=="POST"||mode!=="ask")return response({error:"Unknown operation"},405);
  if(!sameOrigin(req))return response({error:"Same-origin requests only"},403);
  let question;try{question=z.object({question:z.string().trim().min(3).max(1000)}).parse(await readBody(req,2500)).question}catch{return response({error:"Enter 3–1000 characters"},400)}
  const previous=await recent(db,"question",100);if(previous.filter(q=>Date.now()-q.received_at<3600000).length>=20)return response({error:"Please wait: 20 questions per hour"},429);
  const snapshot=await db.get("snapshot/latest",{type:"json"});if(!snapshot)return response({error:"Connect the observer first"},409);
  const id=randomUUID();await put(db,"question",id,{question,status:"pending",snapshot_tick:snapshot.tick});await trim(db,"question",100);return response({id,status:"pending"});
 }catch{return response({error:"Monitoring storage is temporarily unavailable. Retry shortly."},503)}
}
export default (req,context) => handle(req,()=>store(context));
