/* Full Duplex site script: lazy beehiiv embeds, iframe titles, sticky subscribe bar. No trackers. */
(function(){
  var LOADER='https://subscribe-forms.beehiiv.com/v3/loader.js';
  // 1. Lazy-load the beehiiv form only when a Signal block nears the viewport (saves ~250 KB up front).
  function load(slot){
    if(slot.getAttribute('data-loaded'))return; slot.setAttribute('data-loaded','1');
    var s=document.createElement('script'); s.async=true; s.src=LOADER; s.setAttribute('data-beehiiv-form',slot.getAttribute('data-form'));
    slot.appendChild(s);
  }
  var slots=[].slice.call(document.querySelectorAll('.bh-slot'));
  if(slots.length){
    if('IntersectionObserver' in window){
      var io=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting){io.unobserve(e.target);load(e.target);}});},{rootMargin:'300px 0px'});
      slots.forEach(function(s){io.observe(s);});
    } else slots.forEach(load);
    // 2. Accessibility: give beehiiv's iframes a title.
    if('MutationObserver' in window){
      new MutationObserver(function(){
        [].forEach.call(document.querySelectorAll('.bh-slot iframe:not([title])'),function(f){f.setAttribute('title','Subscribe to Signal, the Full Duplex newsletter');});
      }).observe(document.body,{childList:true,subtree:true});
    }
  }
  // 3. Mobile sticky subscribe bar: appears after 40% scroll, dismissible, remembered for 30 days.
  var bar=document.querySelector('.stickybar'); if(!bar)return;
  var KEY='fd_bar_dismissed', until=0; try{until=+localStorage.getItem(KEY)||0;}catch(e){}
  if(Date.now()<until)return;
  var shown=false;
  function onScroll(){
    var h=document.documentElement.scrollHeight-innerHeight; var past=h>0&&scrollY/h>0.4;
    if(past&&!shown){bar.hidden=false;shown=true;} else if(!past&&shown&&scrollY/h<0.3){bar.hidden=true;shown=false;}
  }
  addEventListener('scroll',onScroll,{passive:true});
  bar.querySelector('.x').addEventListener('click',function(){bar.hidden=true;removeEventListener('scroll',onScroll);try{localStorage.setItem(KEY,String(Date.now()+30*864e5));}catch(e){}});
})();
/* Phone checker forms: fill the network list for the chosen country (data-ops is built from data/tracker.json). */
(function(){
  [].forEach.call(document.querySelectorAll('form[data-chk]'),function(f){
    var ops={}; try{ops=JSON.parse(f.getAttribute('data-ops')||'{}');}catch(e){}
    var c=f.querySelector('[name=c]'), o=f.querySelector('[name=o]');
    function fill(){
      var v=c.value, list=ops[v]||[], keep=o.value;
      o.innerHTML='<option value="">'+(v&&v!=='other'?'Any network':'Pick a network')+'</option>'+list.map(function(x){return '<option value="'+x[0]+'">'+x[1].replace(/&/g,'&amp;').replace(/</g,'&lt;')+'</option>';}).join('')+(v&&v!=='other'?'<option value=other>Another network</option>':'');
      o.disabled=!v||v==='other'; if(keep)o.value=keep;
    }
    c.addEventListener('change',fill); fill();
  });
})();
/* Glossary tooltips: hover or focus shows (CSS); tap or Enter toggles; Esc or a tap elsewhere closes. Kept inside the screen on phones. */
(function(){
  var tips=[].slice.call(document.querySelectorAll('.gw')); if(!tips.length)return;
  function place(w){
    var t=w.querySelector('.gt'); t.style.removeProperty('--dx');
    var r=t.getBoundingClientRect(), pad=8, dx=0;
    if(r.left<pad)dx=pad-r.left; else if(r.right>innerWidth-pad)dx=innerWidth-pad-r.right;
    if(dx)t.style.setProperty('--dx',Math.round(dx)+'px');
  }
  function close(except){tips.forEach(function(w){if(w!==except&&w.classList.contains('open')){w.classList.remove('open');w.querySelector('.gl').setAttribute('aria-expanded','false');}});}
  tips.forEach(function(w){
    var b=w.querySelector('.gl');
    b.addEventListener('keydown',function(ev){if(ev.key==='Enter'||ev.key===' '){ev.preventDefault();b.click();}});
    b.addEventListener('click',function(ev){ev.stopPropagation();var on=!w.classList.contains('open');close(w);w.classList.toggle('open',on);b.setAttribute('aria-expanded',on?'true':'false');if(on)place(w);});
    w.addEventListener('mouseenter',function(){place(w);}); b.addEventListener('focus',function(){place(w);});
  });
  document.addEventListener('click',function(ev){if(!ev.target.closest||!ev.target.closest('.gw'))close();});
  document.addEventListener('keydown',function(ev){if(ev.key==='Escape'){var o=document.querySelector('.gw.open');close();if(o)o.querySelector('.gl').focus();}});
})();
/* First-visit welcome. Home page: the D1 intro (assets/intro.js, loaded only there) plays once per browser, then the corner card.
   Any other page: just the corner card. The card is shown once per browser overall, wherever it was seen first, so a visitor who
   met it on an article still gets the intro on their first home visit, but no second card. Intro: skip button, Esc or click.
   Reduced motion: no intro, card with the still logo. ?nowelcome turns both off. */
(function(){
  var CK='fd_welcomed', IK='fd_intro', me=document.currentScript||document.querySelector('script[src*="assets/site.js"]');
  if(!me||/[?&]nowelcome\b/.test(location.search))return;
  if(document.body.classList.contains('is-game')||document.body.classList.contains('is-check'))return;
  var root=new URL('../',me.src).href, here=location.href.split(/[?#]/)[0], home=here===root||here===root+'index.html';
  var card, intro;
  try{
    var cv=localStorage.getItem(CK);
    if(cv&&cv.indexOf('v2:')!==0&&!localStorage.getItem(IK))localStorage.setItem(IK,'pre-v2'); /* saw intro + card before this change */
    card=!cv; intro=home&&!localStorage.getItem(IK);
  }catch(e){return;}
  if(!card&&!intro)return;
  var still=matchMedia('(prefers-reduced-motion: reduce)').matches;
  var ART='<svg class=wl-art viewBox="0 0 320 150" aria-hidden=true focusable=false><g fill="#9fb0c3"><circle cx=30 cy=24 r=1.1 /><circle cx=112 cy=12 r=.9 /><circle cx=200 cy=20 r=1.2 /><circle cx=300 cy=70 r=1 /><circle cx=150 cy=86 r=.8 /><circle cx=86 cy=56 r=1 /><circle cx=238 cy=94 r=.9 /></g>'+
    '<g transform="translate(105 20) scale(.2132) translate(-254 -250)"><ellipse cx=512 cy=508 rx=560 ry=170 transform="rotate(-18 512 508)" fill=none stroke="#5ec8ff" stroke-opacity=".18" stroke-width=6 stroke-dasharray="18 22"/>'+
    '<g fill=none stroke-width=32 stroke-linecap=round><path d="M279 505A233 233 0 0 1 644.3 313.2" stroke="#00cfff"/><path d="M744.9 511.9A233 233 0 0 1 383.7 699.5" stroke="#fff"/></g>'+
    '<circle cx=423 cy=432 r=10 fill="#00cfff"/><path transform="translate(426 517.5) rotate(-15)" fill="#00cfff" fill-rule=evenodd d="M-23.5 -57.5h47a5 5 0 0 1 5 5v105a5 5 0 0 1 -5 5h-47a5 5 0 0 1 -5 -5v-105a5 5 0 0 1 5 -5zM-8.5 -48h17.0a5.5 5.5 0 0 1 5.5 5.5v0.0a5.5 5.5 0 0 1 -5.5 5.5h-17.0a5.5 5.5 0 0 1 -5.5 -5.5v-0.0a5.5 5.5 0 0 1 5.5 -5.5z"/>'+
    '<g fill="#fff"><path d="M583 488h21l33 32-22 22-32-32z"/><path d="M620 492l20-21 15 14-21 22z"/><path d="M567 545l21-21 14 14-20 20z"/><circle cx=635 cy=541 r=8 /></g></g></svg>';
  function show(){
    if(!card)return; card=false; try{localStorage.setItem(CK,'v2:'+Date.now());}catch(e){}
    var d=document.createElement('div'); d.className='welcome'; d.setAttribute('role','dialog'); d.setAttribute('aria-modal','false'); d.setAttribute('aria-labelledby','wl-h');
    d.innerHTML='<button type=button class=wl-x aria-label="Close welcome">×</button>'+ART+
      '<p class=wl-k>Constellation online</p><h2 id=wl-h>Welcome to Full Duplex</h2>'+
      '<p class=wl-p>Satellite-to-phone, explained by a mobile network insider with over 13 years in GSM. Start here:</p>'+
      '<div class=wl-b><a class=btn href="'+root+'check/">Can my phone connect?</a><a class="btn ghost" href="'+root+'satellites/">Meet the satellites</a><a class="btn ghost" href="https://fullduplexhq.beehiiv.com/subscribe?utm_source=fullduplex-site&amp;utm_medium=welcome&amp;utm_campaign=signal">Get Signal free</a></div>'+
      '<button type=button class=wl-skip>Skip</button>';
    function shut(){d.classList.add('out');setTimeout(function(){d.remove();},still?0:250);document.removeEventListener('keydown',key);}
    function key(ev){if(ev.key==='Escape')shut();}
    d.querySelector('.wl-x').addEventListener('click',shut); d.querySelector('.wl-skip').addEventListener('click',shut);
    [].forEach.call(d.querySelectorAll('.wl-b a'),function(x){x.addEventListener('click',function(){d.remove();});});
    document.addEventListener('keydown',key);
    document.body.appendChild(d);
  }
  if(intro){try{localStorage.setItem(IK,'v2:'+Date.now());}catch(e){}}
  if(!intro||still||!window.HTMLCanvasElement)return show();
  var s=document.createElement('script'); s.src=root+'assets/intro.js?v='+(me.src.split('v=')[1]||'0');
  s.onload=function(){if(window.FDIntro)window.FDIntro({onDone:show});else show();}; s.onerror=show; document.head.appendChild(s);
})();
