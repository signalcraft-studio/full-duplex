/* Full Duplex flight view globe: real positions of recently launched broadband and phone-network satellites.
   Orbits: data/gp-recent.json (CelesTrak GP data, cached by scripts/fetch_gp.py, never fetched from CelesTrak by browsers).
   Propagation: satellite.js (SGP4, MIT), loaded only when the globe scrolls into view. Pauses off-screen;
   under prefers-reduced-motion it draws still frames (refreshed every 15 s) with no spinning. */
(function(){
  var sec=document.querySelector('section.flg'), box=document.getElementById('glview'); if(!sec||!box) return;
  var base=sec.getAttribute('data-base')||'', R=Math.PI/180, RE=6371;
  var reduce=window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches;
  var COL={starlink:'#00cfff','amazon-leo':'#f5c26b',ast:'#ff9a3c',globalstar:'#b58cff',lynk:'#6ee79a',oneweb:'#e8eef7',qianfan:'#ff6b8b',guowang:'#ff8f6b'};
  var MON='Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split(' ');
  var started=false, ready=false, visible=false, running=false, cv, ctx, dpr=Math.min(2,window.devicePixelRatio||1), W=0, r=0, cx=0;
  var land=null, G=null, sats=[], sel=null, launch=null, lam=0, phi=0.4, drag=null, last=0, x=1, simBase=Date.now(), perfBase=performance.now(), lastSum=0, aimed=false;
  function $(id){ return document.getElementById(id); }
  function simNow(){ return new Date(simBase+(performance.now()-perfBase)*x); }
  function vec(lat,lon){ var c=Math.cos(lat); return [c*Math.cos(lon),c*Math.sin(lon),Math.sin(lat)]; }
  function proj(v,h){ var a=v[0]*Math.cos(lam)-v[1]*Math.sin(lam), b=v[1]*Math.cos(lam)+v[0]*Math.sin(lam);
    var X=b*h, Y=(Math.cos(phi)*v[2]-Math.sin(phi)*a)*h, Z=(Math.sin(phi)*v[2]+Math.cos(phi)*a)*h; return [cx+r*X, cx-r*Y, Z, X*X+Y*Y]; }
  function resize(){ var b=box.clientWidth; W=Math.round(b*1.28); cv.width=W*dpr; cv.height=W*dpr; cx=W/2; r=b/2-3; }
  function fmtDate(s){ if(!s) return 'date unknown'; var p=s.split('-'); return (+p[2])+' '+MON[+p[1]-1]+' '+p[0]; }
  function pos(s,d,gm){ var p=satellite.propagate(s.rec,d); if(!p||!p.position||isNaN(p.position.x)) return null;
    var e=satellite.eciToEcf(p.position,gm), n=Math.sqrt(e.x*e.x+e.y*e.y+e.z*e.z); return {u:[e.x/n,e.y/n,e.z/n],h:n/RE,eci:p.position,v:p.velocity}; }
  function render(){
    if(!ctx) return; var d=simNow(), gm=satellite.gstime(d);
    ctx.setTransform(dpr,0,0,dpr,0,0); ctx.clearRect(0,0,W,W);
    if(land){ var p=land.p, ds=Math.max(1.2,r/120);
      for(var i=0;i<p.length;i+=3){ var q=proj(vec(p[i]/10*R,p[i+1]/10*R),1); if(q[2]<=0.02) continue;
        ctx.globalAlpha=0.18+0.42*q[2]; ctx.fillStyle=p[i+2]===3?'#2f7d5a':p[i+2]===2?'#6b5a35':'#2d4468'; ctx.fillRect(q[0]-ds/2,q[1]-ds/2,ds,ds); } }
    var hi=[];
    for(var k=0;k<sats.length;k++){ var s=sats[k], P=pos(s,d,gm); s.now=P; if(!P) continue;
      var on=sel&&s.g===sel; if(on){ hi.push(s); continue; }
      var q2=proj(P.u,P.h); if(q2[2]<0&&q2[3]<1) continue;
      ctx.globalAlpha=(q2[2]<0?0.25:0.6)*(sel?0.75:1); ctx.fillStyle=COL[s.net]||'#e8eef7'; ctx.beginPath(); ctx.arc(q2[0],q2[1],1.7,0,7); ctx.fill(); }
    // highlighted launch: short trails (last 8 minutes of flight) then bright dots
    hi.forEach(function(s){ ctx.beginPath(); var pen=false;
      for(var j=16;j>=0;j--){ var P2=j?pos(s,new Date(d.getTime()-j*30000),satellite.gstime(new Date(d.getTime()-j*30000))):s.now; if(!P2) continue;
        var q3=proj(P2.u,P2.h); if(q3[2]<0&&q3[3]<1){ pen=false; continue; } pen?ctx.lineTo(q3[0],q3[1]):ctx.moveTo(q3[0],q3[1]); pen=true; }
      ctx.globalAlpha=0.45; ctx.strokeStyle=COL[s.net]||'#fff'; ctx.lineWidth=1.2; ctx.stroke(); });
    hi.forEach(function(s){ var q4=proj(s.now.u,s.now.h); if(q4[2]<0&&q4[3]<1) return; var c=COL[s.net]||'#fff';
      ctx.globalAlpha=q4[2]<0?0.35:0.3; ctx.fillStyle=c; ctx.beginPath(); ctx.arc(q4[0],q4[1],6,0,7); ctx.fill();
      ctx.globalAlpha=q4[2]<0?0.5:1; ctx.fillStyle='#fff'; ctx.beginPath(); ctx.arc(q4[0],q4[1],2.4,0,7); ctx.fill(); });
    ctx.globalAlpha=1;
    var now=performance.now(); if(now-lastSum>1000){ lastSum=now; summary(d); }
  }
  function summary(d){
    var g=G&&G.groups.filter(function(g){return g.id===sel;})[0], el=$('gl-sum'); if(!g){ el.textContent=''; return; }
    var hs=[], ang=[], n0=null, r0=null;
    sats.forEach(function(s){ if(s.g!==sel||!s.now) return; hs.push((s.now.h-1)*RE);
      var p=s.now.eci, v=s.now.v; if(!n0){ n0=[p.y*v.z-p.z*v.y,p.z*v.x-p.x*v.z,p.x*v.y-p.y*v.x]; var nn=Math.hypot(n0[0],n0[1],n0[2]); n0=n0.map(function(a){return a/nn;}); r0=[p.x,p.y,p.z]; }
      var t1=[n0[1]*r0[2]-n0[2]*r0[1],n0[2]*r0[0]-n0[0]*r0[2],n0[0]*r0[1]-n0[1]*r0[0]];
      var a=Math.atan2(t1[0]*p.x+t1[1]*p.y+t1[2]*p.z, r0[0]*p.x+r0[1]*p.y+r0[2]*p.z)/R; ang.push((a+360)%360); });
    if(!hs.length){ el.textContent=''; return; }
    ang.sort(function(a,b){return a-b;}); var gap=360-ang[ang.length-1]+ang[0]; for(var i=1;i<ang.length;i++) gap=Math.max(gap,ang[i]-ang[i-1]);
    var spread=Math.round(360-gap), days=Math.max(0,Math.round((d-Date.parse(g.launch_date+'T12:00:00Z'))/864e5));
    el.innerHTML=''; var b=document.createElement('strong'); b.textContent=g.label+' · '+g.n+' satellites'; el.appendChild(b);
    el.appendChild(document.createTextNode(' launched '+fmtDate(g.launch_date)+(days?' ('+days+' days ago)':'')+' · international designator '+g.id+'. Now '+Math.round(Math.min.apply(0,hs))+'–'+Math.round(Math.max.apply(0,hs))+' km up, spread over about '+spread+'° of their orbit (a full ring is 360°).'+(g.phone?' These can connect to ordinary phones.':' Broadband satellites: they serve dishes, not phones.')));
    $('gl-time').textContent='Positions for '+d.toLocaleString('en-GB',{day:'numeric',month:'short',hour:'2-digit',minute:'2-digit',second:'2-digit',timeZoneName:'short'})+(x>1?' (sped up ×'+x+')':'');
  }
  function chips(){
    var box2=$('gl-chips'); box2.innerHTML='';
    G.groups.forEach(function(g){ var b=document.createElement('button'); b.type='button'; b.className='chip'; b.setAttribute('aria-pressed',g.id===sel);
      b.innerHTML='<i style="background:'+(COL[g.net]||'#fff')+'"></i>'; b.appendChild(document.createTextNode(g.label.replace(/ \(.*\)$/,'')+' · '+fmtDate(g.launch_date).replace(/ \d{4}$/,'')+' ('+g.n+')'));
      b.addEventListener('click',function(){ pick(g.id,true); }); box2.appendChild(b); });
  }
  function aimAt(){ var s=sats.filter(function(s){return s.g===sel&&s.now;})[0]; if(!s) return; var u=s.now.u;
    lam=-Math.atan2(u[1],u[0])+0.5; phi=Math.max(-0.9,Math.min(0.9,Math.asin(u[2]))); }
  function pick(id,aim){ sel=id; [].forEach.call($('gl-chips').children,function(b,i){ b.setAttribute('aria-pressed',G.groups[i].id===id); });
    lastSum=-1e9; render(); if(aim){ aimAt(); render(); } }
  function match(){
    var el=$('gl-sel'); if(!launch){ el.textContent=''; return null; }
    var day=launch.n.slice(0,10), past=Date.parse(launch.n)<Date.now(), m=null;
    if(G) G.groups.forEach(function(g){ if(!m&&g.net===launch.net&&g.launch_date===day) m=g; });
    if(m){ el.textContent=launch.m+': '+m.n+' satellites from this launch are in the tracking data. They’re highlighted on the globe.'; return m.id; }
    if(!past) el.textContent=launch.m+' hasn’t launched yet (planned '+launch.w+'). '+(launch.net?'Its satellites will appear here once they’re tracked and published, usually within a few days of launch. Until then, here are the newest satellites already up.':'It isn’t carrying broadband or phone satellites, so the globe shows the newest ones that are.');
    else el.textContent=launch.m+' has launched, but its satellites aren’t in the published tracking data yet. They usually appear within a few days.';
    return null;
  }
  function chooseDefault(){ var id=match(); if(id) return id; var g=null;
    if(launch&&launch.net) G.groups.forEach(function(x){ if(!g&&x.net===launch.net) g=x; });
    if(!g) G.groups.forEach(function(x){ if(!g&&x.net==='starlink') g=x; });
    return (g||G.groups[0]).id; }
  function frame(t){ if(!running) return; requestAnimationFrame(frame); if(t-last<40) return; var dt=last?Math.min(100,t-last):40; last=t; if(!drag) lam+=dt*0.00005; render(); }
  function play(){ if(reduce||running||!visible||document.hidden||!ready) return; running=true; last=0; requestAnimationFrame(frame); }
  function pause(){ running=false; }
  function load(src){ return new Promise(function(ok,no){ if(window.satellite) return ok(); var s=document.createElement('script'); s.src=src; s.onload=ok; s.onerror=no; document.head.appendChild(s); }); }
  function start(){
    if(started) return; started=true;
    cv=document.createElement('canvas'); cv.setAttribute('aria-hidden','true'); box.appendChild(cv); ctx=cv.getContext('2d'); resize();
    Promise.all([load(base+'assets/vendor/satellite.min.js'), fetch(base+'data/gp-recent.json').then(function(r){return r.json();}),
                 fetch(base+'assets/globe-dots.json').then(function(r){return r.json();}).catch(function(){return null;})]).then(function(a){
      G=a[1]; land=a[2];
      G.groups.forEach(function(g){ g.objects.forEach(function(o){ try{ sats.push({g:g.id,net:g.net,name:o.OBJECT_NAME,rec:satellite.json2satrec(o)}); }catch(e){} }); });
      ready=true; box.classList.add('ready'); chips(); pick(chooseDefault(),true); play();
      if(reduce) setInterval(function(){ if(visible&&!document.hidden){ lastSum=-1e9; render(); } },15000);
    }).catch(function(){ $('gl-sel').textContent='Sorry, the satellite data didn’t load. Try refreshing the page.'; });
    addEventListener('resize',function(){ resize(); render(); });
    cv.addEventListener('pointerdown',function(e){ drag={x:e.clientX,y:e.clientY,l:lam,p:phi}; cv.setPointerCapture(e.pointerId); });
    cv.addEventListener('pointermove',function(e){ if(!drag) return; lam=drag.l+(e.clientX-drag.x)*0.006; phi=Math.max(-1.1,Math.min(1.1,drag.p+(e.clientY-drag.y)*0.006)); if(!running) render(); });
    cv.addEventListener('pointerup',function(){ drag=null; }); cv.addEventListener('pointercancel',function(){ drag=null; });
  }
  [].forEach.call(sec.querySelectorAll('.gl-speed .chip'),function(b){
    if(reduce){ b.parentNode.hidden=true; return; }
    b.addEventListener('click',function(){ simBase=simNow().getTime(); perfBase=performance.now(); x=+b.getAttribute('data-x');
      [].forEach.call(b.parentNode.children,function(c){ c.setAttribute("aria-pressed",c===b); }); lastSum=-1e9; }); });
  document.addEventListener('fd:flight',function(e){ launch=e.detail; if(ready){ pick(chooseDefault(),true); } else match(); });
  if('IntersectionObserver' in window){
    new IntersectionObserver(function(es){ visible=es[0].isIntersecting; if(visible){ if(!started) (window.requestIdleCallback||setTimeout)(start,{timeout:1200}); else play(); } else pause(); },{rootMargin:'200px',threshold:0}).observe(box);
  } else { visible=true; start(); }
  document.addEventListener('visibilitychange',function(){ document.hidden?pause():play(); });
})();
