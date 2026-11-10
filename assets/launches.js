/* Full Duplex launch tracker: countdowns, local times, launch filters. No libraries, no trackers. */
(function(){
  var fmt;
  try{fmt=new Intl.DateTimeFormat('en-GB',{weekday:'short',day:'numeric',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit',timeZoneName:'short'});}catch(e){}
  function local(el){
    if(!fmt)return; var d=new Date(el.getAttribute('datetime')); if(isNaN(d))return;
    el.title=el.textContent; el.textContent=fmt.format(d);
  }
  [].forEach.call(document.querySelectorAll('time[data-local]'),local);
  function pad(n){return (n<10?'0':'')+n;}
  function left(ms){
    var s=Math.floor(ms/1000),d=Math.floor(s/86400),h=Math.floor(s%86400/3600),m=Math.floor(s%3600/60);
    return 'T− '+(d?d+'d ':'')+pad(h)+'h '+pad(m)+'m '+pad(s%60)+'s';
  }
  var card=document.querySelector('.nextlaunch'), queue=[];
  if(card){try{queue=JSON.parse(card.getAttribute('data-queue'))||[];}catch(e){}}
  // If the first launch in the card has passed (the page is rebuilt a few times a day), roll on to the next one.
  function roll(){
    var now=Date.now();
    while(queue.length>1&&new Date(queue[0].n).getTime()<now-3*3600e3)queue.shift();
    if(!card||!queue.length)return;
    var q=queue[0], t=card.querySelector('.nl-title');
    if(t.textContent!==q.m){
      t.textContent=q.m; card.querySelector('.nl-rocket').textContent=q.r||''; card.querySelector('.nl-pad').textContent=q.p||'';
      card.querySelector('.nl-window').textContent=q.w||'';
      var tm=card.querySelector('.nl-when time'); tm.setAttribute('datetime',q.n); tm.textContent=q.n; local(tm);
      card.querySelector('.nl-cd').setAttribute('data-countdown',q.n);
      var tg=card.querySelector('.nl-tag .ltag'); if(tg){tg.textContent=q.t; tg.className='ltag l-'+q.c;}
      var cal=card.querySelector('.nl-links a[download]'); if(cal)cal.remove();
    }
  }
  var cds=[].slice.call(document.querySelectorAll('[data-countdown]'));
  function tick(){
    roll(); var now=Date.now();
    cds.forEach(function(el){
      var ms=new Date(el.getAttribute('data-countdown')).getTime()-now;
      el.textContent= ms>0 ? left(ms) : (ms>-3*3600e3 ? 'Launch window open: check the status' : 'Launched or moved: data refreshes several times a day');
    });
  }
  if(cds.length){tick(); setInterval(tick,1000);}
  // Filters on /launches/
  var list=document.getElementById('launch-list'); if(!list)return;
  var chips=[].slice.call(document.querySelectorAll('.chip[data-who]')), items=[].slice.call(list.querySelectorAll('li.launch')), more=document.getElementById('launch-more');
  var count=document.getElementById('l-count'), empty=document.getElementById('l-empty');
  function apply(k){
    var n=0;
    items.forEach(function(li){var on=k==='all'||(' '+li.getAttribute('data-who')+' ').indexOf(' '+k+' ')>-1; li.hidden=!on; if(on)n++;});
    chips.forEach(function(c){c.setAttribute('aria-pressed',String(c.getAttribute('data-who')===k));});
    count.textContent=n+(n===1?' launch':' launches');
    if(more){var hid=more.querySelectorAll('li.launch:not([hidden])').length; if(k!=='all'&&hid)more.open=true; more.hidden=!hid; more.querySelector('summary').textContent='Show '+hid+' more launch'+(hid===1?'':'es');}
    empty.hidden=n>0; if(!n)empty.textContent=empty.getAttribute('data-empty-'+k)||empty.getAttribute('data-empty');
    try{history.replaceState(null,'',k==='all'?location.pathname:'#'+k);}catch(e){}
  }
  chips.forEach(function(c){c.addEventListener('click',function(){apply(c.getAttribute('data-who'));});});
  var h=location.hash.slice(1); if(h&&chips.some(function(c){return c.getAttribute('data-who')===h;}))apply(h);
})();
