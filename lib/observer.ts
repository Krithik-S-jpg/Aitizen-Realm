export type Citizen={id:string;name:string;active:boolean;x:number;y:number;ai_mode:string;action:string;reason:string;needs:Record<string,number>;inventory:Record<string,number>;memories:{tick:number;summary:string;kind:string}[]};
export type Alert={id:string;tick:number;severity:string;title:string;summary:string;x?:number;y?:number;received_at?:number};
export type Report={id:string;text:string;mode:string;tick:number;received_at:number};
export type Picture={id:string;captured_at:number;tick:number};
export type Question={id:string;question:string;status:string;answer?:string;mode?:string;tick?:number;received_at:number};
export type Snapshot={received_at:number;captured_at:string;state:string;tick:number;population:number;world:{seed:number;width:number;height:number}|null;calendar:{day:number;hour:number;season:string;weather:string;temperature_c:number};citizens:Citizen[];supplies:Record<string,number>;buildings:{id:string;type:string;x:number;y:number;progress:number;condition:number}[];metrics:Record<string,number>[];scenario:{name?:string;status?:string;objectives?:Record<string,{label:string;value:number;target:number}>};conversations:{id:string;sender:string;recipient:string;tick:number;content:string}[];truncated?:boolean};
export type Feed={snapshot:Snapshot|null;reports:Report[];pictures:Picture[];questions:Question[];alerts:Alert[]};
export const time=(value:number|string)=>new Date(value).toLocaleString(undefined,{month:"short",day:"numeric",hour:"2-digit",minute:"2-digit"});
export const lower=(s:string|undefined)=>s?.replaceAll("_"," ").toLowerCase()||"—";
export function download(name:string,data:unknown){const url=URL.createObjectURL(new Blob([typeof data==="string"?data:JSON.stringify(data,null,2)],{type:typeof data==="string"?"text/plain":"application/json"}));const a=document.createElement("a");a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
