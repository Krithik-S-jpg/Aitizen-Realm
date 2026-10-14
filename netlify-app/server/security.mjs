import {createHash,createHmac,timingSafeEqual} from "node:crypto";
export const COOKIE="__Host-observatory";
export function equal(a,b){return timingSafeEqual(createHash("sha256").update(a).digest(),createHash("sha256").update(b).digest())}
export function settings(env=process.env){
 const names=["OBSERVATORY_ADMIN_KEY","OBSERVATORY_SESSION_SECRET","OBSERVATORY_INGEST_TOKEN"];
 if(names.some(n=>!env[n]||env[n].length<32)||new Set(names.map(n=>env[n])).size!==3)throw new Error("Configure three distinct Observatory secrets of at least 32 characters in Netlify.");
 return {admin:env[names[0]],session:env[names[1]],ingest:env[names[2]]};
}
export function sign(secret,now=Date.now()){const expires=String(now+12*3600000);return expires+"."+createHmac("sha256",secret).update(expires).digest("hex")}
export function verified(value,secret,now=Date.now()){const [expires,signature,...extra]=String(value||"").split(".");return !extra.length&&/^\d{13}$/.test(expires)&&Number(expires)>now&&Number(expires)<=now+12*3600000&&/^[a-f0-9]{64}$/.test(signature||"")&&equal(signature,createHmac("sha256",secret).update(expires).digest("hex"))}
export function authenticated(req,secret){const cookie=(req.headers.get("cookie")||"").split(";").map(v=>v.trim()).find(v=>v.startsWith(COOKIE+"="));return verified(cookie?.slice(COOKIE.length+1),secret)}
export function sameOrigin(req){return req.headers.get("origin")===new URL(req.url).origin}
export function sessionCookie(value,maxAge=43200){return COOKIE+"="+value+"; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age="+maxAge}
export const response=(data,status=200,headers={})=>Response.json(data,{status,headers:{"Cache-Control":"no-store","X-Content-Type-Options":"nosniff",...headers}});
export async function readBody(req,limit){const reader=req.body?.getReader();if(!reader)return {};let size=0;const chunks=[];while(true){const{done,value}=await reader.read();if(done)break;size+=value.byteLength;if(size>limit){await reader.cancel();throw new Error("body too large")}chunks.push(value)}return JSON.parse(Buffer.concat(chunks).toString("utf8"))}
