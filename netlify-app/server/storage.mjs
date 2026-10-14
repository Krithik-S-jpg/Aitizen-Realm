import {getStore} from "@netlify/blobs";
export function storeName(runtime){
 // CONTEXT and DEPLOY_ID are build variables, not Functions runtime variables.
 const deploy=runtime?.deploy;
 if(deploy?.context==="production")return "aitizen-observatory-production";
 if(!deploy?.context||!deploy?.id)throw new Error("Missing Netlify deployment context");
 return "aitizen-observatory-"+deploy.id;
}
export function store(runtime,createStore=getStore){
 return createStore({name:storeName(runtime),consistency:"strong"});
}
export const recordKey=(kind,id)=>kind+"/"+id;
export async function put(db,kind,id,payload,created=Date.now()){await db.setJSON(recordKey(kind,id),{...payload,id,received_at:created})}
export async function recent(db,kind,limit){const entries=await db.list({prefix:kind+"/"});const rows=await Promise.all(entries.blobs.map(b=>db.get(b.key,{type:"json"})));return rows.filter(Boolean).sort((a,b)=>b.received_at-a.received_at).slice(0,limit)}
export async function trim(db,kind,limit){const rows=await recent(db,kind,10000);for(const row of rows.slice(limit)){await db.delete(recordKey(kind,row.id));if(kind==="picture")await db.delete("jpeg/"+row.id)}}
