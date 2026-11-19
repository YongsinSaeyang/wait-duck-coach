(() => {
  'use strict';
  const search=document.querySelector('#wiki-search');
  if(search){const entries=[...document.querySelectorAll('[data-wiki]')];search.addEventListener('input',()=>{const terms=search.value.normalize('NFKC').toLowerCase().trim().split(/\s+/).filter(Boolean);let count=0;entries.forEach(entry=>{entry.hidden=!terms.every(t=>entry.textContent.toLowerCase().includes(t));if(!entry.hidden)count++;});document.querySelector('#wiki-count').textContent=count+' 篇 Wiki';document.querySelector('#wiki-empty').hidden=count>0;});}
  const deck=document.querySelector('.deck');if(!deck)return;
  const slides=[...document.querySelectorAll('[data-slide]')],status=document.querySelector('#slide-status');let index=0,reading=false;
  function show(number,update=true){index=Math.max(0,Math.min(slides.length-1,number));slides.forEach((s,i)=>s.hidden=!reading&&i!==index);status.textContent=(index+1)+' / '+slides.length;document.querySelector('#previous').disabled=index===0;document.querySelector('#next').disabled=index===slides.length-1;if(update){history.replaceState(null,'','#'+slides[index].id);if(!reading)slides[index].scrollIntoView({block:'start'});}}
  function fromHash(){const found=slides.findIndex(s=>'#'+s.id===location.hash);show(found<0?0:found,false);if(found>=0&&!reading)slides[index].scrollIntoView({block:'start'});}
  document.querySelector('#previous').addEventListener('click',()=>show(index-1));document.querySelector('#next').addEventListener('click',()=>show(index+1));
  document.querySelector('#reading-mode').addEventListener('click',event=>{reading=!reading;deck.classList.toggle('reading-mode',reading);event.currentTarget.setAttribute('aria-pressed',String(reading));show(index);});
  const menu=document.querySelector('#slide-menu');document.querySelector('#contents').addEventListener('click',()=>menu.showModal());document.querySelector('#close-menu').addEventListener('click',()=>menu.close());menu.addEventListener('click',event=>{if(event.target.closest('a'))menu.close();});
  addEventListener('hashchange',fromHash);addEventListener('keydown',event=>{if(event.ctrlKey||event.metaKey||event.altKey||event.isComposing||menu.open||event.target.closest('input,textarea,select,[contenteditable]'))return;const delta={'ArrowRight':1,'PageDown':1,'ArrowLeft':-1,'PageUp':-1}[event.key];if(delta){event.preventDefault();show(index+delta);}if(event.key==='Home'){event.preventDefault();show(0);}if(event.key==='End'){event.preventDefault();show(slides.length-1);}});
  const check=document.querySelector('#quiz-check');check.addEventListener('click',()=>{const answer=document.querySelector('[name="lesson-quiz"]:checked');document.querySelector('#quiz-result').textContent=!answer?'先選一個答案。':answer.value==='activity'?'正確。沒有交易時，無法從這段零報酬判斷交易後的策略績效。':'再看第 13 頁：零交易的平線不代表策略沒有風險。';});
  fromHash();
})();
