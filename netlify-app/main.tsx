import React,{useEffect,useState} from "react";
import {createRoot} from "react-dom/client";
import Observatory from "../app/observatory";
import "../app/globals.css";

function App(){
 const[ready,setReady]=useState(false),[signedIn,setSignedIn]=useState(false),[key,setKey]=useState(""),[error,setError]=useState(""),[busy,setBusy]=useState(false);
 useEffect(()=>{(async()=>{try{
  if(location.pathname==="/logout"){await fetch("/api/auth/logout",{method:"POST"});history.replaceState(null,"","/")}
  const r=await fetch("/api/auth/session",{cache:"no-store"});
  if(r.ok)setSignedIn(true);else if(r.status!==401){const b=await r.json();setError(b.error||"Authentication is not configured")}
 }catch{setError("Unable to reach the server. Use Netlify Dev locally, or open your deployed Netlify URL.")}finally{setReady(true)}})()},[]);
 async function login(e:React.FormEvent){e.preventDefault();setBusy(true);setError("");try{const r=await fetch("/api/auth/login",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({key})});const b=await r.json();if(!r.ok)throw Error(b.error||"Sign-in failed");setKey("");setSignedIn(true)}catch(e){setError(e instanceof Error?e.message:"Sign-in failed")}finally{setBusy(false)}}
 if(signedIn)return <Observatory signOutHref="/logout"/>;
 return <main style={{margin:"auto",maxWidth:520,padding:"70px 24px"}}><section className="panel"><p className="eyebrow">AITIZEN OBSERVATORY</p><h1>Welcome back.</h1><p className="subtle">Sign in with your owner access key. Your simulation data stays private.</p>{!ready?<p role="status">Checking session…</p>:<form onSubmit={login}><label style={{display:"block",marginTop:25}}>Owner access key<input className="search" type="password" autoComplete="current-password" required minLength={32} maxLength={256} value={key} onChange={e=>setKey(e.target.value)}/></label>{error&&<p className="notice danger" role="alert">{error}</p>}<button className="outline" disabled={busy}>{busy?"Signing in…":"Sign in securely"}</button><p className="subtle">This is the OBSERVATORY_ADMIN_KEY configured by the owner in Netlify—not the connector token. Your session expires after 12 hours.</p></form>}</section></main>
}
createRoot(document.getElementById("root")!).render(<App/>);
