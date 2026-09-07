const samples = {
  pass: {
    id: "web-pass", task: "Deliver a launch note with a test result and rollback plan.",
    deliverable: "Release v1.4 is ready. Tests: 48 passed, 0 failed. Rollback: redeploy v1.3 if the health check fails.",
    criteria: [
      {id:"C1",text:"Delivery states test evidence",checks:[{type:"text_regex",pattern:"\\d+ passed",min_matches:1}]},
      {id:"C2",text:"Delivery includes rollback instructions",checks:[{type:"text_contains",value:"Rollback:"}]}
    ]
  },
  fail: {
    id: "web-fail", task: "Research brief must contain three cited sources and no unsupported certainty.",
    deliverable: "The market will definitely double next year. Sources: [1] Example A [2] Example B",
    criteria: [
      {id:"C1",text:"At least three source markers",checks:[{type:"text_regex",pattern:"\\[\\d+\\]",min_matches:3}]},
      {id:"C2",text:"Avoid forbidden certainty",checks:[{type:"text_not_contains",value:"definitely"}]}
    ]
  },
  unknown: {
    id: "web-unknown", task: "Confirm the submitted app passes its real integration suite.",
    deliverable: "The author says all integration tests pass.",
    criteria: [{id:"C1",text:"Run the real integration suite",checks:[{type:"command",argv:["npm","test"]}]}]
  }
};
const specEl=document.querySelector('#spec'), run=document.querySelector('#run');
const state=document.querySelector('#state'), empty=document.querySelector('#empty'), report=document.querySelector('#report');
function load(name){specEl.value=JSON.stringify(samples[name],null,2)}
document.querySelectorAll('[data-sample]').forEach(b=>b.onclick=()=>load(b.dataset.sample)); load('pass');
run.onclick=async()=>{state.textContent='VERIFYING';run.disabled=true;try{const r=await fetch('/api/verify',{method:'POST',headers:{'content-type':'application/json'},body:specEl.value});const data=await r.json();if(!r.ok)throw new Error(data.error||'Verification failed');render(data)}catch(e){alert(e.message);state.textContent='ERROR'}finally{run.disabled=false}};
function render(data){empty.hidden=true;report.hidden=false;state.textContent='COMPLETE';const v=document.querySelector('#verdict');v.textContent=data.verdict.toUpperCase();v.className='verdict '+data.verdict;document.querySelector('#score').textContent=data.score;const root=document.querySelector('#criteria');root.innerHTML='';data.criteria.forEach(c=>{const el=document.createElement('div');el.className='criterion';el.innerHTML=`<div class="criterion-top"><span>${c.id}</span><span class="${c.status}">${c.status.toUpperCase()}</span></div><p>${escapeHtml(c.text)}</p>${c.checks.map(x=>`<div class="check">${escapeHtml(x.type)} → ${escapeHtml(x.summary)}</div>`).join('')}`;root.appendChild(el)})}
function escapeHtml(s){return String(s).replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]))}
