/* Full Duplex site script: hide-on-scroll mobile header, sticky subscribe bar, checker forms, glossary, welcome. No third-party trackers; see privacy.html. */
(function(){
  /* (The lazy beehiiv iframe loader lived here until 14 Nov 2026; every Signal block is now our own button.) */
  // 1. The top header used to hide on scroll below 860px. The new sidebar / tab bar stays put, so that behaviour is off.
  // 2. Mobile sticky subscribe bar: appears after 40% scroll, dismissible, remembered for 30 days.
  var bar=document.querySelector('.stickybar'); if(!bar)return;
  var KEY='fd_bar_dismissed', until=0; try{until=+localStorage.getItem(KEY)||0;}catch(e){}
  if(Date.now()<until)return;
  var shown=false;
  function onScroll(){
    var h=document.documentElement.scrollHeight-innerHeight; var past=h>0&&scrollY/h>0.4;
    if(past&&!shown&&!document.querySelector('.welcome')){bar.hidden=false;shown=true;} else if(!past&&shown&&scrollY/h<0.3){bar.hidden=true;shown=false;}
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

/* Source passthrough: if a visitor lands with utm_* tags in the URL (e.g. from an X post), keep them for this visit only
   (sessionStorage, cleared when the tab closes; no cookies, no third-party calls) and carry them onto beehiiv subscribe links,
   so beehiiv credits the signup to X instead of "fullduplex-site". The link's own placement (header, footer, ...) moves to
   utm_content; an existing utm_content (e.g. the checker's country/network) is never overwritten. Documented in privacy.html. */
(function(){
  try{
    var KEYS=['utm_source','utm_medium','utm_campaign'], SEL='a[href^="https://fullduplexhq.beehiiv.com/subscribe"]';
    var q=new URLSearchParams(location.search), saved=null;
    try{saved=JSON.parse(sessionStorage.getItem('fd_utm')||'null');}catch(e){}
    if(q.get('utm_source')&&q.get('utm_source')!=='fullduplex-site'){
      saved={}; KEYS.forEach(function(k){if(q.get(k))saved[k]=q.get(k);});
      try{sessionStorage.setItem('fd_utm',JSON.stringify(saved));}catch(e){}
    }
    if(!saved||!saved.utm_source)return;
    function tag(a){
      var u=new URL(a.href), placement=u.searchParams.get('utm_medium');
      KEYS.forEach(function(k){if(saved[k])u.searchParams.set(k,saved[k]);});
      if(placement&&!u.searchParams.get('utm_content'))u.searchParams.set('utm_content',placement);
      a.href=u.toString();
    }
    function all(){Array.prototype.forEach.call(document.querySelectorAll(SEL),tag);}
    if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',all);else all();
    /* links added later (welcome card, Check my phone results, game end card) are tagged just before they are used */
    ['click','auxclick','contextmenu'].forEach(function(ev){
      document.addEventListener(ev,function(e){var a=e.target.closest&&e.target.closest(SEL);if(a)tag(a);},true);
    });
  }catch(e){/* never break the page */}
})();

/* Mobile "More" sheet: button opens a dialog, Esc / overlay / close returns focus. */
(function(){
  var btn=document.querySelector('.tab-more'), sheet=document.getElementById('nav-more');
  if(!btn||!sheet) return;
  var panel=sheet.querySelector('.nav-more-panel'), closeBtn=sheet.querySelector('.nav-more-x'), last=null;
  function focusables(){return [].slice.call(panel.querySelectorAll('a,button,input:not([type=hidden])')).filter(function(x){return x.offsetParent!==null;});}
  function open(){
    last=document.activeElement; sheet.hidden=false; btn.setAttribute('aria-expanded','true');
    document.body.classList.add('nav-more-open'); (closeBtn||panel).focus();
  }
  function close(){
    if(sheet.hidden) return;
    sheet.hidden=true; btn.setAttribute('aria-expanded','false');
    document.body.classList.remove('nav-more-open'); if(last&&last.focus) last.focus();
  }
  btn.addEventListener('click',function(){ sheet.hidden?open():close(); });
  if(closeBtn) closeBtn.addEventListener('click',close);
  sheet.addEventListener('click',function(e){ if(e.target===sheet) close(); });
  document.addEventListener('keydown',function(e){
    if(sheet.hidden) return;
    if(e.key==='Escape'){ close(); return; }
    if(e.key!=='Tab') return;
    var f=focusables(); if(!f.length) return;
    var first=f[0], lastE=f[f.length-1];
    if(e.shiftKey&&document.activeElement===first){ e.preventDefault(); lastE.focus(); }
    else if(!e.shiftKey&&document.activeElement===lastE){ e.preventDefault(); first.focus(); }
  });
})();

/* On-site Signal sign-up (Nov 2026). Forms (.su) post to our Cloudflare Worker, which adds the subscriber through beehiiv's API,
   so no beehiiv script or cookie loads here. Cloudflare Turnstile (spam check) loads only when someone focuses an email box.
   Without JavaScript the form is a plain link-style GET to beehiiv's sign-up page. Documented in privacy.html. */
(function(){
  var forms=document.querySelectorAll('form.su'); if(!forms.length) return;
  var RE=/^[^\s@<>()",;:]+@[^\s@<>()",;:]+\.[A-Za-z]{2,}$/, tsState=0, tsQ=[];
  var SUB='https://fullduplexhq.beehiiv.com/subscribe';
  function loadTS(cb){
    if(tsState===2) return cb(); tsQ.push(cb); if(tsState===1) return; tsState=1;
    window.__fdTs=function(){tsState=2; tsQ.splice(0).forEach(function(f){f();});};
    var s=document.createElement('script'); s.src='https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit&onload=__fdTs'; s.async=true;
    s.onerror=function(){tsState=0; tsQ.splice(0).forEach(function(f){f(true);});}; document.head.appendChild(s);
  }
  function arm(f){
    if(f._ts!==undefined) return; f._ts=null; f._tok='';
    loadTS(function(err){
      if(err||!window.turnstile) return;
      try{ f._ts=turnstile.render(f.querySelector('.su-ts'),{sitekey:f.dataset.sk,appearance:'interaction-only',size:'flexible',action:'signup',
        callback:function(t){f._tok=t;}, 'expired-callback':function(){f._tok='';}, 'error-callback':function(){f._tok='';}}); }catch(e){}
    });
  }
  function msg(f,text,kind,html){var m=f.querySelector('.su-msg'); m.className='su-msg'+(kind?' '+kind:''); if(html) m.innerHTML=html; else m.textContent=text;}
  function waitTok(f,ms){return new Promise(function(res){var t0=Date.now();(function p(){if(f._tok) return res(f._tok); if(Date.now()-t0>ms) return res(''); setTimeout(p,150);})();});}
  var fallback=function(f){return 'Or <a href="'+SUB+'?utm_source=site&amp;utm_medium='+encodeURIComponent(f.dataset.su)+'&amp;utm_campaign=onsite-signup">sign up on beehiiv’s page</a> instead.';};
  Array.prototype.forEach.call(forms,function(f){
    f.noValidate=true;
    var inp=f.querySelector('.su-in'), go=f.querySelector('.su-go');
    inp.addEventListener('focus',function(){arm(f);});
    inp.addEventListener('input',function(){if(f.querySelector('.su-msg').classList.contains('err')){inp.removeAttribute('aria-invalid'); msg(f,'');}});
    f.addEventListener('submit',function(e){
      e.preventDefault(); if(f._busy) return;
      var email=(inp.value||'').trim();
      if(!RE.test(email)){inp.setAttribute('aria-invalid','true'); msg(f,'That email address doesn’t look right. Check it and try again.','err'); inp.focus(); return;}
      inp.removeAttribute('aria-invalid'); arm(f); f._busy=true; go.disabled=true; msg(f,'Signing you up…','wait');
      waitTok(f,10000).then(function(tok){
        return fetch(f.dataset.ep,{method:'POST',headers:{'Content-Type':'application/json'},
          body:JSON.stringify({email:email,turnstileToken:tok,placement:f.dataset.su,page:location.pathname})})
          .then(function(r){return r.json().catch(function(){return {ok:false,error:'server'};});});
      }).catch(function(){return {ok:false,error:'server'};}).then(function(d){
        f._busy=false; go.disabled=false;
        if(d&&d.ok){ f.classList.add('done'); msg(f,'You’re in. Signal lands in your inbox on Fridays.','ok'); return; }
        var err=d&&d.error;
        if(err==='invalid_email'){inp.setAttribute('aria-invalid','true'); msg(f,'','err','That email address doesn’t look right. Check it and try again.');}
        else if(err==='captcha'){msg(f,'','err','We couldn’t finish the quick spam check. Please try again. '+fallback(f));}
        else if(err==='rate_limited'){msg(f,'','err','Too many tries just now. Please wait a minute and try again. '+fallback(f));}
        else msg(f,'','err','Something went wrong on our side, sorry. '+fallback(f));
        if(f._ts!==null&&f._ts!==undefined&&window.turnstile){try{f._tok=''; turnstile.reset(f._ts);}catch(e){}}
      });
    });
  });
  /* "Get Signal" in the sidebar and the More sheet opens the small form instead of leaving the site. */
  Array.prototype.forEach.call(document.querySelectorAll('[data-su-toggle]'),function(a){
    var p=document.getElementById(a.getAttribute('data-su-toggle')); if(!p) return;
    a.setAttribute('aria-expanded','false'); a.setAttribute('role','button');
    function set(open){p.hidden=!open; a.setAttribute('aria-expanded',open?'true':'false'); if(open){var i=p.querySelector('.su-in'); if(i) i.focus();}}
    a.addEventListener('click',function(e){e.preventDefault(); set(p.hidden);});
    document.addEventListener('keydown',function(e){if(e.key==='Escape'&&!p.hidden&&p.classList.contains('nav-su-pop')){set(false); a.focus();}});
    document.addEventListener('click',function(e){if(!p.hidden&&p.classList.contains('nav-su-pop')&&!p.contains(e.target)&&!a.contains(e.target)) set(false);});
  });
})();
