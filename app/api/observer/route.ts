import { env } from "cloudflare:workers";
import { z } from "zod";

export const dynamic = "force-dynamic";
const json = (data: unknown, status = 200) => Response.json(data, { status, headers: { "Cache-Control": "no-store" } });
const row = z.object({id:z.string().max(160),tick:z.number(),severity:z.string().max(20),title:z.string().max(200),summary:z.string().max(1000)}).passthrough();
const snapshot = z.object({schema:z.literal(1),captured_at:z.string().max(50),state:z.string().max(40),tick:z.number().nonnegative(),citizens:z.array(z.object({id:z.string(),name:z.string(),active:z.boolean()}).passthrough()).max(500),alerts:z.array(row).max(120),metrics:z.array(z.record(z.unknown())).max(120)}).passthrough();
const ingest = z.object({ snapshot: snapshot.optional(), report:z.object({id:z.string().uuid(),text:z.string().max(12000),mode:z.string().max(50),tick:z.number()}).optional(), picture:z.object({id:z.string().uuid(),base64:z.string().max(1100000),captured_at:z.number(),tick:z.number()}).optional(), answers:z.array(z.object({id:z.string().uuid(),text:z.string().max(12000),mode:z.string().max(50),tick:z.number()})).max(5).default([])});
async function recent(kind:string, limit:number) { const result=await env.DB!.prepare("SELECT id, created, payload FROM observer_records WHERE kind=? ORDER BY created DESC LIMIT ?").bind(kind,limit).all<{id:string,created:number,payload:string}>(); return result.results.map(r=>({...JSON.parse(r.payload),id:r.id,received_at:r.created})); }
async function put(id:string,kind:string,payload:unknown,time=Date.now()) { await env.DB!.prepare("INSERT INTO observer_records(id,kind,created,payload) VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload,created=excluded.created").bind(id,kind,time,JSON.stringify(payload)).run(); }
async function trim(kind:string, limit:number) { await env.DB!.prepare("DELETE FROM observer_records WHERE kind=? AND id NOT IN (SELECT id FROM observer_records WHERE kind=? ORDER BY created DESC LIMIT ?)").bind(kind,kind,limit).run(); }

export async function GET(request:Request) {
  if(!request.headers.get("oai-authenticated-user-id")) return json({error:"Sign in to view this private Observatory."},401);
  if(!env.DB) return json({error:"Monitoring storage is not ready."},503);
  const [latest,reports,pictures,questions,alerts]=await Promise.all([recent("snapshot",1),recent("report",48),recent("picture",24),recent("question",30),recent("alert",200)]);
  return json({snapshot:latest[0]||null,reports,pictures,questions,alerts,server_time:Date.now()});
}

export async function POST(request:Request) {
  if(!env.DB) return json({error:"Storage unavailable"},503);
  const mode=new URL(request.url).searchParams.get("mode");
  // Sites dispatch authenticates this OWNER-PRIVATE site before routing requests.
  // Connector access uses the dispatch service bearer; never make this site public.
  if(mode === "ingest") {
    if(request.headers.get("oai-authenticated-user-id")) return json({error:"Browser sessions cannot publish telemetry."},403);
    const bytes=await request.arrayBuffer(); if(bytes.byteLength>1500000)return json({error:"Payload too large"},413);
    let data; try {data=ingest.parse(JSON.parse(new TextDecoder().decode(bytes)));}catch{return json({error:"Invalid monitoring payload"},400);}
    if(data.snapshot) {
      await put("latest","snapshot",data.snapshot);
      if(data.snapshot.alerts.length) await env.DB.batch(data.snapshot.alerts.map(a=>env.DB!.prepare("INSERT OR IGNORE INTO observer_records(id,kind,created,payload) VALUES(?,?,?,?)").bind("alert:"+a.id,"alert",Date.now(),JSON.stringify(a))));
      await trim("alert",500);
    }
    if(data.report){await put(data.report.id,"report",data.report);await trim("report",96);}
    if(data.picture && env.BUCKET) {
      let bytes:Uint8Array;try{bytes=Uint8Array.from(atob(data.picture.base64),c=>c.charCodeAt(0));}catch{return json({error:"Invalid image"},400);}
      if(bytes.length>800000||bytes[0]!==255||bytes[1]!==216||bytes[2]!==255)return json({error:"JPEG required"},400);
      await env.BUCKET.put(data.picture.id,bytes,{httpMetadata:{contentType:"image/jpeg"}});
      await put(data.picture.id,"picture",{captured_at:data.picture.captured_at,tick:data.picture.tick});
      const all=await recent("picture",50);for(const image of all.slice(24)){await env.BUCKET.delete(image.id);await env.DB.prepare("DELETE FROM observer_records WHERE id=? AND kind='picture'").bind(image.id).run();}
    }
    for(const answer of data.answers) {
      const old=await env.DB.prepare("SELECT payload FROM observer_records WHERE id=? AND kind='question'").bind(answer.id).first<{payload:string}>();
      if(old){const q=JSON.parse(old.payload);if(q.status==="pending")await put(answer.id,"question",{...q,status:"answered",answer:answer.text,mode:answer.mode,tick:answer.tick});}
    }
    const questions=(await recent("question",100)).filter(q=>q.status==="pending"&&Date.now()-q.received_at<900000).slice(0,3);
    return json({accepted:true,questions});
  }
  if(!request.headers.get("oai-authenticated-user-id"))return json({error:"Sign in required"},401);
  if(request.headers.get("origin")!==new URL(request.url).origin)return json({error:"Same-origin requests only"},403);
  if(mode!=="ask")return json({error:"Unknown operation"},404);
  const raw=await request.text();if(raw.length>2500)return json({error:"Question too long"},413);
  let question:string;try{question=z.object({question:z.string().trim().min(3).max(1000)}).parse(JSON.parse(raw)).question;}catch{return json({error:"Enter a question of 3–1000 characters."},400);}
  const previous=await recent("question",100);
  if(previous.filter(q=>Date.now()-q.received_at<3600000).length>=20)return json({error:"Please wait: 20 questions per hour."},429);
  const latest=(await recent("snapshot",1))[0];
  if(!latest)return json({error:"Connect the local observer before asking about this world."},409);
  const id=crypto.randomUUID();await put(id,"question",{question,status:"pending",snapshot_tick:latest.tick});await trim("question",100);
  return json({id,status:"pending"});
}
