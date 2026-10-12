import { env } from "cloudflare:workers";
export const dynamic="force-dynamic";
export async function GET(request:Request,{params}:{params:Promise<{id:string}>}) {
 if(!request.headers.get("oai-authenticated-user-id"))return new Response("Sign in required",{status:401});
 const {id}=await params;if(!/^[0-9a-f-]{36}$/.test(id))return new Response("Not found",{status:404});
 const object=await env.BUCKET?.get(id);if(!object)return new Response("Not found",{status:404});
 return new Response(object.body,{headers:{"Content-Type":"image/jpeg","Cache-Control":"private, max-age=60","X-Content-Type-Options":"nosniff"}});
}
