import {getStore} from "@netlify/blobs";
export function store(){// Isolate deploy previews so they cannot read or prune production records.
 const context=process.env.CONTEXT;
 if(!context)throw new Error("Use Netlify Dev or a Netlify deployment");
 const name=context==="production"?"aitizen-observatory-production": "aitizen-observatory-"+(process.env.DEPLOY_ID||"local");
 return getStore({name,consistency:"strong"});
}
export const recordKey=(kind,id)=>kind+"/"+id;
export async function put(db,kind,id,payload,created=Date.now()){await db.setJSON(recordKey(kind,id),{...payload,id,received_at:created})}
export async function recent(db,kind,limit){const entries=await db.list({prefix:kind+"/"});const rows=await Promise.all(entries.blobs.map(b=>db.get(b.key,{type:"json"})));return rows.filter(Boolean).sort((a,b)=>b.received_at-a.received_at).slice(0,limit)}
export async function trim(db,kind,limit){const rows=await recent(db,kind,10000);for(const row of rows.slice(limit)){await db.delete(recordKey(kind,row.id));if(kind==="picture")await db.delete("jpeg/"+row.id)}}
