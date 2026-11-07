const {test} = require('node:test');
const assert = require('node:assert/strict');
const {JSDOM} = require('jsdom');
const fs = require('node:fs');
const html = fs.readFileSync('templates/index.html', 'utf8');
function setup(fetch) {
  const dom = new JSDOM(html, {runScripts:'dangerously', url:'http://localhost', beforeParse(window){window.fetch=fetch;}});
  const d=dom.window.document;
  d.getElementById('exampleBtn').click();
  return {dom,d,form:d.getElementById('predictionForm')};
}
const tick = () => new Promise(resolve=>setImmediate(resolve));
test('400 explains fields, hides previous result, preserves valid input',async()=>{
 const {dom,d,form}=setup(async()=>({ok:false,json:async()=>({error:'Неверное значение',fields:['chol']})}));
 d.getElementById('resultBlock').hidden=false;
 form.dispatchEvent(new dom.window.Event('submit',{cancelable:true}));
 await tick();
 assert.equal(d.getElementById('resultBlock').hidden,true);
 assert.match(d.getElementById('errorMessage').textContent,/Холестерин/);
 assert.equal(form.elements.chol.getAttribute('aria-invalid'),'true');
 assert.equal(form.elements.age.value,'59');
 assert.equal(d.getElementById('submitBtn').disabled,false);
 dom.window.close();
});
