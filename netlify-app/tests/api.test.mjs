import test from "node:test";
import assert from "node:assert/strict";
import {handle} from "../netlify/functions/api.mjs";
import {sign,verified,sessionCookie,settings} from "../server/security.mjs";
const env={OBSERVATORY_ADMIN_KEY:"a".repeat(48),OBSERVATORY_SESSION_SECRET:"b".repeat(48),OBSERVATORY_INGEST_TOKEN:"c".repeat(48)};
const origin="https://example.netlify.app";
const cookie=sessionCookie(sign(env.OBSERVATORY_SESSION_SECRET)).split(";")[0];
test("null sign-in payload is rejected without crashing",async()=>{const r=await handle(new Request(origin+"/api/auth/login",{method:"POST",headers:{Origin:origin,"Content-Type":"application/json"},body:"null"}),memory,env);assert.equal(r.status,401)});
function req(path,method="GET",data,headers={}){return new Request(origin+path,{method,headers:{Origin:origin,...(data?{"Content-Type":"application/json"}:{}),...headers},...(data?{body:JSON.stringify(data)}:{})})}
function memory(){const rows=new Map();return {get:async k=>rows.get(k)??null,setJSON:async(k,v)=>rows.set(k,structuredClone(v)),set:async(k,v)=>rows.set(k,v),delete:async k=>rows.delete(k),list:async({prefix})=>({blobs:[...rows.keys()].filter(k=>k.startsWith(prefix)).map(key=>({key}))})}}
test("session signatures expire and reject tampering",()=>{const key=env.OBSERVATORY_SESSION_SECRET;const token=sign(key,1000000000000);assert(verified(token,key,1000000000000));assert(!verified(token,key,1000000000000+43200001));assert(!verified(token+"x",key));assert.throws(()=>settings({}))});
test("missing configuration and forged platform identity fail closed",async()=>{assert.equal((await handle(req("/api/observer"),memory,{})).status,503);assert.equal((await handle(req("/api/observer","GET",null,{"oai-authenticated-user-id":"spoof"}),memory,env)).status,401)});
test("login uses secure cookie, rejects wrong key and cross-origin",async()=>{let r=await handle(req("/api/auth/login","POST",{key:env.OBSERVATORY_ADMIN_KEY}),memory,env);assert.equal(r.status,200);assert.match(r.headers.get("set-cookie"),/HttpOnly; Secure; SameSite=Strict/);assert.equal((await handle(req("/api/auth/login","POST",{key:"wrong"}),memory,env)).status,401);assert.equal((await handle(req("/api/auth/login","POST",{key:env.OBSERVATORY_ADMIN_KEY},{Origin:"https://evil.example"}),memory,env)).status,403)});
test("browser cannot ingest; connector cannot browse private records",async()=>{assert.equal((await handle(req("/api/observer?mode=ingest","POST",{}, {Cookie:cookie}),memory,env)).status,401);assert.equal((await handle(req("/api/observer","GET",null,{Authorization:"Bearer "+env.OBSERVATORY_INGEST_TOKEN}),memory,env)).status,401)});
test("snapshot, queued question, answer and picture round trip",async()=>{const db=memory(),factory=()=>db;const auth={Authorization:"Bearer "+env.OBSERVATORY_INGEST_TOKEN};const snapshot={schema:1,captured_at:new Date().toISOString(),state:"PAUSED",tick:5,citizens:[],alerts:[],metrics:[],world:null};let r=await handle(req("/api/observer?mode=ingest","POST",{snapshot},auth),factory,env);assert.equal(r.status,200);
r=await handle(req("/api/observer?mode=ask","POST",{question:"What happened?"},{Cookie:cookie}),factory,env);assert.equal(r.status,200);const q=await r.json();
r=await handle(req("/api/observer?mode=ingest","POST",{answers:[{id:q.id,text:"Paused at tick 5",mode:"Recorded facts",tick:5}]},auth),factory,env);assert.equal(r.status,200);
const feed=await (await handle(req("/api/observer","GET",null,{Cookie:cookie}),factory,env)).json();assert.equal(feed.snapshot.tick,5);assert.equal(feed.questions[0].answer,"Paused at tick 5");
assert.equal((await handle(req("/api/observer?mode=ingest","POST",{picture:{id:"11111111-1111-4111-8111-111111111111",base64:"not a jpeg",captured_at:1,tick:5}},auth),factory,env)).status,400);
assert.equal((await handle(req("/api/picture/../../secret","GET",null,{Cookie:cookie}),factory,env)).status,404);
});
test("cross-origin questions rejected and no-world startup returns clear error",async()=>{assert.equal((await handle(req("/api/observer?mode=ask","POST",{question:"Hello?"},{Cookie:cookie,Origin:"https://evil.example"}),memory,env)).status,403);assert.equal((await handle(req("/api/observer?mode=ask","POST",{question:"Hello?"},{Cookie:cookie}),memory,env)).status,409)});
