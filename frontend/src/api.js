let active=0;
function notify(delta){active=Math.max(0,active+delta);window.dispatchEvent(new CustomEvent('nexus:loading',{detail:active}));}
export async function api(path,options={}){
 notify(1);
 try{
 const r=await fetch('/api'+path,{cache:'no-store',...options});let body;
 try{body=await r.json()}catch{throw Error(`HTTP ${r.status}: không đọc được phản hồi máy chủ`)}
 if(!r.ok||body.status==='error'){const e=body.errors?.[0]||body.detail||{};throw Error(`${e.code||r.status}: ${e.message||JSON.stringify(e)}`)}
 return body.data;
 }finally{notify(-1)}
}
export const post=(path,data={})=>api(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
export async function upload(path,file,fields={}){const d=new FormData();d.append('file',file);Object.entries(fields).forEach(([k,v])=>d.append(k,v));return api(path,{method:'POST',body:d});}
export function saveFile(data,name,type='application/octet-stream',encoded=true){const raw=encoded?Uint8Array.from(atob(data),c=>c.charCodeAt(0)):data;const u=URL.createObjectURL(new Blob([raw],{type}));const a=document.createElement('a');a.href=u;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);}
