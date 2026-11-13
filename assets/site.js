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
/* First-visit welcome: a small card (not a modal; the page stays usable). Shown once per browser (localStorage), skippable, Esc closes,
   static when reduced motion is on. Links are built relative to this script so they work at any depth.
   Review: ?welcome=a|b|c|d forces a concept (B-D live in assets/welcome-alt.js, loaded only for review). */
(function(){
  var KEY='fd_welcomed', me=document.currentScript||document.querySelector('script[src*="assets/site.js"]');
  var Q=(location.search.match(/[?&]welcome=([a-d])\b/)||[])[1];
  if(!me)return;
  if(!Q){
    try{if(localStorage.getItem(KEY)||/[?&]nowelcome\b/.test(location.search))return;}catch(e){return;}
    if(document.body.classList.contains('is-game')||document.body.classList.contains('is-check'))return;
    try{localStorage.setItem(KEY,String(Date.now()));}catch(e){}
  }
  var root=new URL('../',me.src).href, still=matchMedia('(prefers-reduced-motion: reduce)').matches;
  var A={cls:'v-a',k:'Signal received',art:'<svg class=wl-art viewBox="0 0 320 150" aria-hidden=true focusable=false><defs><linearGradient id=wl-g x1=0 y1=1 x2=1 y2=0><stop offset=0 stop-color="#5ec8ff" stop-opacity=".1"/><stop offset=1 stop-color="#5ec8ff" stop-opacity=".9"/></linearGradient></defs>'+
    '<g class=wl-stars fill="#9fb0c3"><circle cx=40 cy=22 r=1.2 /><circle cx=120 cy=14 r=1 /><circle cx=210 cy=30 r=1.3 /><circle cx=290 cy=60 r=1 /><circle cx=170 cy=70 r=.9 /><circle cx=70 cy=64 r=1 /></g>'+
    '<path d="M0 140C80 118 240 118 320 140V150H0z" fill="#16243d"/>'+
    '<g class=wl-phone transform="translate(52 96)"><rect x=-9 y=-17 width=18 height=32 rx=4 fill="#0f1626" stroke="#e8eef7" stroke-width=1.6 /><rect x=-6 y=-13 width=12 height=21 rx=1.5 fill="#5ec8ff" opacity=".35"/></g>'+
    '<path class=wl-up d="M58 80Q140 30 236 34" fill=none stroke="url(#wl-g)" stroke-width=2.4 stroke-linecap=round stroke-dasharray="4 7"/>'+
    '<circle class=wl-dot r=4 fill="#5ec8ff"><animateMotion dur="1.3s" begin="0.25s" fill="freeze" path="M58 80Q140 30 236 34"/></circle>'+
    '<g transform="translate(250 32) rotate(-12)"><g class=wl-sat><rect x=-28 y=-5 width=18 height=10 fill="#1d3a66" stroke="#5ec8ff" stroke-width=1 /><rect x=10 y=-5 width=18 height=10 fill="#1d3a66" stroke="#5ec8ff" stroke-width=1 /><rect x=-8 y=-8 width=16 height=16 rx=2 fill="#e8eef7"/><circle cx=0 cy=0 r=3 fill="#00cfff"/></g></g>'+
    '<path class=wl-down d="M244 46L66 88" fill=none stroke="#6ee79a" stroke-width=2.4 stroke-linecap=round />'+
    '<g class=wl-ring fill=none stroke="#6ee79a" stroke-width=1.6><circle cx=52 cy=96 r=16 /><circle cx=52 cy=96 r=26 /></g></svg>'};
  function show(V){
    var d=document.createElement('div'); d.className='welcome '+V.cls+(still?' still':''); d.setAttribute('role','dialog'); d.setAttribute('aria-modal','false'); d.setAttribute('aria-labelledby','wl-h');
    if(V.wt)d.style.setProperty('--wt',V.wt);
    var rev=Q?'<p class=wl-rev>Review: '+['a','b','c','d'].map(function(x){return x===Q?'<b>'+x.toUpperCase()+'</b>':'<a href="?welcome='+x+'">'+x.toUpperCase()+'</a>';}).join(' ')+'</p>':'';
    d.innerHTML='<button type=button class=wl-x aria-label="Close welcome">×</button>'+V.art+
      '<p class=wl-k>'+V.k+'</p><h2 id=wl-h>Welcome to Full Duplex</h2>'+
      '<p class=wl-p>Satellite-to-phone, explained by a mobile network insider with over 13 years in GSM. Start here:</p>'+
      '<div class=wl-b><a class=btn href="'+root+'check/">Can my phone connect?</a><a class="btn ghost" href="'+root+'satellites/">Meet the satellites</a><a class="btn ghost" href="https://fullduplexhq.beehiiv.com/subscribe?utm_source=fullduplex-site&amp;utm_medium=welcome&amp;utm_campaign=signal">Get Signal free</a></div>'+
      '<button type=button class=wl-skip>Skip</button>'+rev;
    if(still){var mo=d.querySelector('animateMotion');if(mo)mo.remove();var dt=d.querySelector('.wl-dot');if(dt){dt.setAttribute('cx','236');dt.setAttribute('cy','34');}}
    if(V.init)V.init(d,still);
    function shut(){d.classList.add('out');setTimeout(function(){d.remove();},still?0:250);document.removeEventListener('keydown',key);}
    function key(ev){if(ev.key==='Escape')shut();}
    d.querySelector('.wl-x').addEventListener('click',shut); d.querySelector('.wl-skip').addEventListener('click',shut);
    [].forEach.call(d.querySelectorAll('.wl-b a'),function(x){x.addEventListener('click',function(){d.remove();});});
    document.addEventListener('keydown',key);
    setTimeout(function(){document.body.appendChild(d);},still?0:400);
  }
  if(Q&&Q!=='a'){var s=document.createElement('script');s.src=root+'assets/welcome-alt.js?v='+(me.src.split('v=')[1]||'0');s.onload=function(){if(window.FDW&&window.FDW[Q])show(window.FDW[Q]);};document.head.appendChild(s);}
  else show(A);
})();
