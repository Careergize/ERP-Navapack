import assert from 'node:assert/strict';
import {createServer} from 'vite';
import {fileURLToPath} from 'node:url';
class Storage{values=new Map();getItem(k){return this.values.get(k)??null;}setItem(k,v){this.values.set(k,String(v));}removeItem(k){this.values.delete(k);}}
globalThis.localStorage=new Storage();globalThis.sessionStorage=new Storage();globalThis.window=new EventTarget();
const server=await createServer({configFile:false,resolve:{alias:{'@':fileURLToPath(new URL('../src',import.meta.url))}},optimizeDeps:{noDiscovery:true},server:{middlewareMode:true,hmr:false},appType:'custom'});
try{
 const {api,loginRequest,currentUserRequest,logoutRequest}=await server.ssrLoadModule('/src/lib/api.ts');
 const {saveTokens,clearSession}=await server.ssrLoadModule('/src/lib/authSession.ts');
 const {masterPage,masterSchema,masterDetail,saveMaster}=await server.ssrLoadModule('/src/lib/mastersApi.ts');
 if(process.env.MASTERS_LIVE_URL){
  assert.match(process.env.MASTERS_LIVE_URL,/^http:\/\/(localhost|127\.0\.0\.1):\d+\/api\/v1$/);
  api.defaults.baseURL=process.env.MASTERS_LIVE_URL;
  const credentials={email:'integration@example.test',password:'long-development-password'};
  let auth=await loginRequest(credentials);saveTokens(auth.access,auth.refresh,false);
  assert.equal((await currentUserRequest()).email,credentials.email);
  const schema=await masterSchema('customers');assert.equal(schema.id.read_only,true);assert.equal(schema.name.required,true);
  const body={name:'Synthetic React HTTP customer',code:'SYN-HTTP-'+crypto.randomUUID()};const key=crypto.randomUUID();
  const created=await saveMaster('customers',body,key);
  assert.equal((await saveMaster('customers',body,key)).id,created.id);
  const changed=await saveMaster('customers',{name:'Synthetic persisted HTTP edit'},crypto.randomUUID(),created);
  assert.equal(changed.version,created.version+1);
  await assert.rejects(saveMaster('customers',{name:'Stale edit'},crypto.randomUUID(),created),e=>e.response.status===412);
  await logoutRequest();clearSession();auth=await loginRequest(credentials);saveTokens(auth.access,auth.refresh,false);
  assert.equal((await masterDetail('customers',created.id)).name,changed.name);
  const list=await masterPage('customers',1,body.code,'true');assert.equal(list.count,1);assert.equal(list.results[0].id,created.id);
  await assert.rejects(api.get('/employees/'),e=>e.response.status===403);
  console.log('LIVE MASTERS PASS: production React adapters, JWT HTTP, create/edit/replay/conflict, refresh reads and reauthentication persistence; employee access denied.');
 }else{
  const calls=[];api.defaults.adapter=async config=>{calls.push(config);return{config,data:{id:'opaque-uuid',version:3},status:200,statusText:'OK',headers:{}};};
  await masterPage('raw-materials',2,'exact grade','true');assert.equal(calls[0].params.page,2);assert.equal(calls[0].params.search,'exact grade');
  await masterSchema('customers');assert.equal(calls[1].url,'/customers/schema/');
  await saveMaster('raw-materials',{min_level:'0.123456'},'stable-intent',{id:'opaque-uuid',version:2});
  assert.equal(calls[2].headers['If-Match'],'"2"');assert.equal(calls[2].headers['Idempotency-Key'],'stable-intent');
  assert.equal(JSON.parse(calls[2].data).min_level,'0.123456');
  api.defaults.adapter=async()=>{throw new Error('offline');};await assert.rejects(saveMaster('customers',{name:'Retained draft'},'retry-key'),/offline/);
  console.log('PASS: master pagination/search/active filters, schema, opaque identities, exact decimal strings, optimistic versions, stable retries and save-error propagation.');
 }
}finally{await server.close();}
