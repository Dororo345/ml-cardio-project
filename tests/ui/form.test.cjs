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

test('XAI unavailable displays explicit message and no invented factors',async()=>{
 const {dom,d,form}=setup(async()=>({ok:true,json:async()=>({probability_percent:20.93,predicted_class:0,factors:[],xai_status:'unavailable',xai_message:'Объяснение временно недоступно'})}));
 form.dispatchEvent(new dom.window.Event('submit',{cancelable:true})); await tick();
 assert.equal(d.getElementById('resultBlock').hidden,false);
 assert.equal(d.getElementById('xaiMessage').hidden,false);
 assert.equal(d.getElementById('xaiList').children.length,0);
 dom.window.close();
});

test('reset clears all 13 inputs, error, prediction and XAI contents',async()=>{
 const {dom,d,form}=setup(async()=>({ok:true,json:async()=>({probability_percent:20.93,predicted_class:0,factors:[{name:'Возраст',direction:'увеличивает'}]})}));
 form.dispatchEvent(new dom.window.Event('submit',{cancelable:true}));await tick();
 d.getElementById('errorMessage').textContent='previous error';
 form.elements.age.setAttribute('aria-invalid','true');
 form.reset();
 const fields=[...form.querySelectorAll('input,select')];
 assert.equal(fields.length,13);
 assert.ok(fields.every(f=>f.value===''));
 assert.ok(fields.every(f=>!f.hasAttribute('aria-invalid')));
 for(const id of ['errorMessage','probabilityValue','classification','xaiList','xaiMessage']) assert.equal(d.getElementById(id).textContent,'');
 assert.equal(d.getElementById('resultBlock').hidden,true);
 assert.equal(d.getElementById('progressFill').style.width,'0%');
 dom.window.close();
});
test('late response cannot repopulate a reset form',async()=>{
 let finish;
 const pending=new Promise(resolve=>finish=resolve);
 const {dom,d,form}=setup(()=>pending);
 form.dispatchEvent(new dom.window.Event('submit',{cancelable:true}));
 form.reset();
 finish({ok:true,json:async()=>({probability_percent:90,predicted_class:1,factors:[]})});await tick();
 assert.equal(d.getElementById('resultBlock').hidden,true);
 assert.equal(d.getElementById('probabilityValue').textContent,'');
 assert.equal(d.getElementById('submitBtn').disabled,false);
 dom.window.close();
});
