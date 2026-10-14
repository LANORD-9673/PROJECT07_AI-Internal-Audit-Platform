export async function api(path,options={}){
 const r=await fetch('/api'+path,options);let body;
 try{body=await r.json()}catch{throw Error(`HTTP ${r.status}: invalid response`)}
 if(!r.ok||body.status==='error'){const e=body.errors?.[0]||body.detail||{};throw Error(`${e.code||r.status}: ${e.message||JSON.stringify(e)}`)}
 return body.data;
}
export const post=(path,data={})=>api(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
export async function upload(path,file,fields){const d=new FormData();d.append('file',file);Object.entries(fields).forEach(([k,v])=>d.append(k,v));return api(path,{method:'POST',body:d});}
