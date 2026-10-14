import test from "node:test";
import assert from "node:assert/strict";
import {store,storeName} from "../server/storage.mjs";
test("runtime deployment metadata selects persistent production storage",()=>{
 assert.equal(storeName({deploy:{context:"production",id:"deploy-1"}}),"aitizen-observatory-production");
 assert.equal(storeName({deploy:{context:"production",id:"deploy-2"}}),"aitizen-observatory-production");
});
test("previews and branches cannot select production storage",()=>{
 assert.equal(storeName({deploy:{context:"deploy-preview",id:"preview-1"}}),"aitizen-observatory-preview-1");
 assert.equal(storeName({deploy:{context:"branch-deploy",id:"branch-1"}}),"aitizen-observatory-branch-1");
 assert.throws(()=>storeName({}));
 assert.throws(()=>storeName({deploy:{context:"deploy-preview"}}));
});
test("storage opens with strong consistency without build environment variables",()=>{
 const result=store({deploy:{context:"production",id:"1"}},options=>options);
 assert.deepEqual(result,{name:"aitizen-observatory-production",consistency:"strong"});
});
