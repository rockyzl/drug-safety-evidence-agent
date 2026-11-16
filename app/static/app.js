'use strict';
const $=id=>document.getElementById(id);
const el=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;};
let busy=false;
function link(text,url){const a=el('a',text);try{const u=new URL(url,location.origin);if(!['https:','http:'].includes(u.protocol))return a;a.href=u.href;}catch{return a;}a.target='_blank';a.rel='noopener noreferrer';return a;}
function setBusy(value){busy=value;$('run').disabled=value;$('example').disabled=value;$('question').disabled=value;$('cutoff').disabled=value;$('run').textContent=value?'Agent is working…':'Run agent ↗';}
function progress(stage,message){const stages=['plan','retrieve','verify','finalize'];const i=stages.indexOf(stage==='draft'?'retrieve':stage);for(const [j,n]of [...$('steps').children].entries()){n.className=j<i?'done':j===i?'active':'';}$('status').textContent=message;$('status').className='';}
function renderSources(sources){$('sources').replaceChildren();for(const s of sources){const row=el('article',undefined,'source');row.id='source-'+s.id;row.append(el('p',s.source_type==='research'?'Research abstract':s.source_type==='label'?'Prescribing information':'FDA communication','source-kind'),el('h3',s.title));const meta=el('p',undefined,'source-date');meta.append(el('span',s.published),link('Open original ↗',s.url));row.append(meta,el('p',s.scope,'scope'));$('sources').append(row);}}
function renderClaim(c,index,sources){const row=el('article',undefined,'claim');row.append(el('span',String(index+1).padStart(2,'0'),'number'));const content=el('div');content.append(el('p',c.text),el('small',c.included_in_brief?'Passed automated checks':'Withheld — '+c.verdict+'. '+c.reason));if(c.included_in_brief){const check=el('details',undefined,'check-detail');check.append(el('summary','Check details'),el('p',c.reason,'meta'));content.append(check);}for(const ref of c.citations){const source=sources.find(s=>s.id===ref.source_id);if(!source)continue;const details=el('details',undefined,'citation');details.append(el('summary',source.title+' · '+ref.section));if(ref.quote)details.append(el('blockquote',ref.quote));else details.append(el('p','Open the original source to inspect this passage. Short excerpt allowance reached, or quote check failed.','meta'));details.append(el('p',ref.passage_id+' · '+source.published,'meta'),link('Read original source ↗',source.url));content.append(details);}row.append(content);return row;}
const sections=[['research','Research evidence','Findings and study context from the research abstracts.'],['regulatory','FDA regulatory communication','What the dated FDA communication states.'],['label','Prescribing information','Warnings and context in the indexed label version.'],['synthesis','Cross-source interpretation','A model-generated comparison, linked to both research and regulatory or label evidence.']];
function renderResult(r,saved=false){
  $('badge').textContent=saved?'Saved run · human review needed':'Live run · human review needed';
  $('run-meta').textContent=`${r.provider} · ${r.model} · ${r.elapsed_seconds}s · ${new Date(r.created_at).toLocaleString()} · cutoff ${r.as_of} · preloaded index`;
  for(const id of ['answer','withheld','limitations','coverage'])$(id).replaceChildren();
  $('coverage').hidden=false;
  $('coverage').append(el('strong','Source coverage'));
  for(const c of r.coverage||[]){const row=el('div',undefined,'coverage-row');row.append(el('span',c.title),el('span',`${c.retrieved_sources} source${c.retrieved_sources===1?'':'s'} retrieved · ${c.supported_claims} claim${c.supported_claims===1?'':'s'} passed`));$('coverage').append(row);}
  const accepted=r.claims.filter(c=>c.included_in_brief);
  if(!accepted.length)$('answer').append(el('p',r.answer));
  let index=0;
  for(const [key,title,description] of sections){
    const block=el('section',undefined,'brief-section');block.dataset.section=key;
    const dates=[...new Set(r.sources.filter(source=>source.source_type===key).map(source=>source.published))].sort();block.append(el('h3',title),el('p',description+(dates.length?' Source dates: '+dates.join(', ')+'.':''),'meta'));
    const claims=accepted.filter(c=>(c.section||'research')===key);
    if(claims.length)claims.forEach(c=>block.append(renderClaim(c,index++,r.sources)));
    else block.append(el('p',key==='synthesis'?'No cross-source interpretation passed the checks.':'No supported claim was produced for this section. Check the retrieved sources and date cutoff.','meta'));
    $('answer').append(block);
  }
  const withheld=r.claims.filter(c=>!c.included_in_brief);
  if(withheld.length){const details=el('details',undefined,'withheld');details.append(el('summary',`${withheld.length} drafted claim${withheld.length===1?'':'s'} withheld from the brief`));withheld.forEach((c,i)=>details.append(renderClaim(c,i,r.sources)));$('withheld').append(details);}
  const notice=el('div',undefined,'notice');notice.append(el('h3','Questions for human review'),el('p','Model-suggested review prompts, not verified findings.','review-label'));
  if(r.limitations.length){const list=el('ul');r.limitations.forEach(t=>list.append(el('li',t)));notice.append(list);}
  notice.append(el('p',r.verification_notice));$('limitations').append(notice);
  renderSources(r.sources);$('source-note').textContent='Preloaded snapshots retrieved for this run. Document dates and original links are shown below.';
  $('trace-panel').hidden=false;$('trace').textContent=JSON.stringify(r.trace,null,2);
  progress('finalize',saved?'Showing a saved real model run over preloaded sources. Run agent makes a new model request.':'Model run finished over the preloaded index. Review the source categories, claims and open questions.');
}
async function jsonGet(path){const r=await fetch(path);if(!r.ok)throw Error('The requested information is temporarily unavailable.');return r.json();}
function fail(error){$('status').textContent=error.message||'The request failed. Please try again.';$('status').className='error';$('badge').textContent='Run incomplete';}
$('research-form').addEventListener('submit',async event=>{event.preventDefault();if(busy)return;const body={question:$('question').value,as_of:$('cutoff').value,mode:'safety_brief'};setBusy(true);$('answer').replaceChildren(el('p','The agent is reading the evidence. This usually takes 15–40 seconds.','meta'));$('withheld').replaceChildren();$('limitations').replaceChildren();$('coverage').hidden=true;$('run-meta').textContent='';$('trace-panel').hidden=true;$('badge').textContent='Live run in progress';progress('plan','Connecting to the research agent…');try{const response=await fetch('/api/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});if(!response.ok){const err=await response.json();throw Error(typeof err.detail==='string'?err.detail:'Please check the question and date.');}const reader=response.body.getReader();const decoder=new TextDecoder();let buffer='',gotResult=false;while(true){const {value,done}=await reader.read();if(done)break;buffer+=decoder.decode(value,{stream:true});let boundary;while((boundary=buffer.indexOf('\n\n'))!==-1){const packet=buffer.slice(0,boundary);buffer=buffer.slice(boundary+2);if(!packet.startsWith('data: '))continue;const data=JSON.parse(packet.slice(6));if(data.type==='progress')progress(data.stage,data.message);if(data.type==='error')throw Error(data.message);if(data.type==='result'){renderResult(data.result);gotResult=true;}}}if(!gotResult)throw Error('The connection ended before a result arrived. Please try again.');}catch(error){fail(error);}finally{setBusy(false);}});
$('example').addEventListener('click',async()=>{if(busy)return;setBusy(true);try{const r=await jsonGet('/api/example');$('question').value=r.question;$('cutoff').value=r.as_of;renderResult(r,true);}catch(error){fail(error);}finally{setBusy(false);}});
document.querySelectorAll('[data-question]').forEach(button=>button.addEventListener('click',()=>{$('question').value=button.dataset.question;$('question').focus();}));
jsonGet('/api/config').then(c=>{renderSources(c.sources);$('snapshot').textContent='Source snapshots loaded '+new Date(c.snapshot_loaded_at).toLocaleDateString()+'. Retrieval uses this prepared collection; it does not browse the web during a run.';$('runtime').textContent=`Live model: ${c.provider} / ${c.model}. Embeddings: ${c.embedding_provider} / ${c.embedding_model}. LangGraph · Chroma · ${c.passage_count} preloaded passages. AWS Bedrock: adapter implemented; not live-verified.`;}).catch(fail);
jsonGet('/api/evaluation').then(r=>{
  const box=$('eval-results');box.replaceChildren();
  if(!r.total_cases){box.append(el('p',r.status||'Evaluation is not available.'));return;}
  if(r.runtime_smoke){const s=r.runtime_smoke;box.append(el('h3','Current Vertex runtime checks'),el('p',`${s.completed_cases}/${s.total_cases} smoke cases completed · ${s.model} · ${s.embedding_model}`),el('p',s.caveat,'meta'));}
  box.append(el('h3','Historical OpenAI regression run'),el('p',r.scope_note,'meta'));
  const stats=el('div',undefined,'eval-grid');
  for(const [value,label]of [[r.completed_cases+'/'+r.total_cases,'regression cases completed'],[r.citation_checks_passed+'/'+r.published_claims,'published claims with valid references and quotes'],[r.out_of_scope_abstentions+'/'+r.out_of_scope_cases,'out-of-scope cases with no published claim']]){const item=el('div',undefined,'eval-stat');item.append(el('strong',value),el('span',label));stats.append(item);}
  box.append(stats,el('p',r.caveat,'meta'));
}).catch(()=>{$('eval-results').textContent='Evaluation report is temporarily unavailable.';});
