/* Full Duplex orbit view (/launches/): one dot per phone-capable satellite on a code-drawn dot globe, plus the
   "launch moment" (a rocket climbs from the pad and drops its satellites into orbit). Canvas + vanilla JS, no images.
   Counts come from data/constellations.json via the page; orbits are illustrative. Starts only when on screen,
   pauses off-screen and in background tabs, and draws one still frame under prefers-reduced-motion. */
(function(){
  var sec=document.querySelector('section.orbit'), box=document.getElementById('orbitview'); if(!sec||!box) return;
  var R=Math.PI/180, RE=6371, reduce=window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches;
  function J(a){try{return JSON.parse(sec.getAttribute(a)||'null');}catch(e){return null;}}
  var cfg=J('data-orbits')||[], demo=J('data-demo'), queue=J('data-queue')||[];
  var COLS={}; cfg.forEach(function(c){COLS[c.id]=c.c;}); COLS.other='#e8eef7';
  var btn=document.getElementById('ov-launch'), status=document.getElementById('ov-status');
  var legend={}; [].forEach.call(sec.querySelectorAll('.ov-legend b[data-count]'),function(b){legend[b.parentNode.className.replace('o-','')]=b;});
  var started=false, ready=false, pending=null;
  var cv, ctx, dpr=Math.min(2,window.devicePixelRatio||1), W=0, r=0, cx=0, land=null, sats=[], t0=0;
  var lam=78*R, phi=24*R, drag=null, running=false, visible=false, last=0, L=null, aim=null;
  function vec(lat,lon){var cl=Math.cos(lat);return [cl*Math.cos(lon),cl*Math.sin(lon),Math.sin(lat)];}
  function build(){
    var w0=2*Math.PI/38000; // one lap of a 360 km orbit = 38 s on screen
    cfg.forEach(function(c){
      var done=0;
      c.s.forEach(function(sh,si){
        var n=si===c.s.length-1?c.n-done:Math.round(c.n*sh[0]); done+=n;
        var inc=sh[1]*R, a=1+sh[2]/RE, P=Math.max(1,Math.min(sh[3],n)), per=Math.ceil(n/P), w=w0*Math.pow((1+360/RE)/a,1.5);
        for(var k=0;k<n;k++){ var p=k%P, j=Math.floor(k/P);
          sats.push({c:c.id,a:a,inc:inc,raan:p*2*Math.PI/P+si*0.37,u:j*2*Math.PI/per+p*0.61,w:w,rank:k/n}); }
      });
    });
  }
  function eci(s,u){ // unit vector of a circular orbit at argument of latitude u
    var cu=Math.cos(u), su=Math.sin(u), co=Math.cos(s.raan), so=Math.sin(s.raan), ci=Math.cos(s.inc), si=Math.sin(s.inc);
    return [co*cu-so*su*ci, so*cu+co*su*ci, su*si];
  }
  function proj(v,h){ // orthographic projection, view rotated by lam (spin) and phi (tilt)
    var a=v[0]*Math.cos(lam)-v[1]*Math.sin(lam), b=v[1]*Math.cos(lam)+v[0]*Math.sin(lam);
    var x=b*h, y=(Math.cos(phi)*v[2]-Math.sin(phi)*a)*h, z=(Math.sin(phi)*v[2]+Math.cos(phi)*a)*h;
    return [cx+r*x, cx-r*y, z, x*x+y*y];
  }
  function resize(){ var b=box.clientWidth; W=Math.round(b*1.28); cv.width=W*dpr; cv.height=W*dpr; cx=W/2; r=b/2-3; }
  function ease(x){return x<0?0:x>1?1:1-Math.pow(1-x,3);}
  function render(t){
    ctx.setTransform(dpr,0,0,dpr,0,0); ctx.clearRect(0,0,W,W);
    // land dots from the home globe data
    if(land){ var p=land.p, ds=Math.max(1.2,r/120);
      for(var i=0;i<p.length;i+=3){ var la=p[i]/10*R, lo=p[i+1]/10*R, q=proj(vec(la,lo),1); if(q[2]<=0.02) continue;
        ctx.globalAlpha=0.18+0.42*q[2]; ctx.fillStyle=p[i+2]===3?'#2f7d5a':p[i+2]===2?'#6b5a35':'#2d4468'; ctx.fillRect(q[0]-ds/2,q[1]-ds/2,ds,ds); } }
    // satellites: count up when the panel first appears
    var prog=reduce?1:ease((t-t0)/2200), shown={};
    for(var k=0;k<sats.length;k++){ var s=sats[k]; if(s.rank>prog) continue;
      var q2=proj(eci(s,s.u+(reduce?0:t*s.w)),s.a); if(q2[2]<0&&q2[3]<1) continue; // hidden behind the Earth
      ctx.globalAlpha=q2[2]<0?0.35:0.95; ctx.fillStyle=COLS[s.c];
      ctx.beginPath(); ctx.arc(q2[0],q2[1],s.c==='starlink-dtc'?1.5:2.4,0,7); ctx.fill(); }
    ctx.globalAlpha=1;
    if(!reduce&&prog<1){ cfg.forEach(function(c){ if(legend[c.id]) legend[c.id].textContent=Math.round(c.n*prog).toLocaleString('en-GB'); }); }
    else if(!render.done){ render.done=1; cfg.forEach(function(c){ if(legend[c.id]) legend[c.id].textContent=c.n.toLocaleString('en-GB'); }); }
    if(L) drawLaunch(t);
  }
  // ---- launch moment
  function frame3(lat,lon,az){ var P=vec(lat,lon), E=[-Math.sin(lon),Math.cos(lon),0], N=[-Math.sin(lat)*Math.cos(lon),-Math.sin(lat)*Math.sin(lon),Math.cos(lat)];
    var D=[Math.cos(az)*N[0]+Math.sin(az)*E[0],Math.cos(az)*N[1]+Math.sin(az)*E[1],Math.cos(az)*N[2]+Math.sin(az)*E[2]]; return [P,D]; }
  function along(f,s){ return [f[0][0]*Math.cos(s)+f[1][0]*Math.sin(s), f[0][1]*Math.cos(s)+f[1][1]*Math.sin(s), f[0][2]*Math.cos(s)+f[1][2]*Math.sin(s)]; }
  var S=0.7, ALT=0.12, TUP=4200, TDEP=1600, THOLD=7000;
  function drawLaunch(t){
    var e=reduce?TUP+TDEP+500:t-L.t; if(e<0){ pad(t); return; }
    var f=L.f, k=Math.min(1,e/TUP), sMax=S*ease(k*1.02)*(k<1?1:1), hOf=function(s){return 1+ALT*Math.pow(Math.min(1,s/S),0.6);};
    // trail
    ctx.beginPath(); var pen=false;
    for(var i=0;i<=40;i++){ var s=sMax*i/40, q=proj(along(f,s),hOf(s)); if(q[2]<0&&q[3]<1){pen=false;continue;} pen?ctx.lineTo(q[0],q[1]):ctx.moveTo(q[0],q[1]); pen=true; }
    var fade=e>TUP+TDEP+THOLD-1500?Math.max(0,1-(e-(TUP+TDEP+THOLD-1500))/1500):1;
    ctx.strokeStyle='rgba(255,190,120,'+(0.85*fade)+')'; ctx.lineWidth=2; ctx.stroke();
    pad(t,fade);
    if(k<1){ // rocket head with a flame glow
      var hq=proj(along(f,sMax),hOf(sMax)); var g=ctx.createRadialGradient(hq[0],hq[1],0,hq[0],hq[1],14); g.addColorStop(0,'rgba(255,240,210,1)'); g.addColorStop(.35,'rgba(255,154,60,.8)'); g.addColorStop(1,'rgba(255,154,60,0)');
      ctx.fillStyle=g; ctx.beginPath(); ctx.arc(hq[0],hq[1],14,0,7); ctx.fill(); ctx.fillStyle='#fff'; ctx.beginPath(); ctx.arc(hq[0],hq[1],2.6,0,7); ctx.fill();
    } else { // satellites released one by one, then they fly on along the orbit
      var n=Math.max(1,L.n), col=COLS[L.c]||'#e8eef7', w=2*Math.PI/38000;
      for(var j=0;j<n;j++){ var rel=TUP+TDEP*j/n; if(e<rel) continue;
        var s2=S+(e-rel)*w*0.9+0*j, q3=proj(along(f,s2),1+ALT); if(q3[2]<0&&q3[3]<1) continue;
        ctx.globalAlpha=fade*Math.min(1,(e-rel)/300); ctx.fillStyle=col; ctx.beginPath(); ctx.arc(q3[0],q3[1],2.8,0,7); ctx.fill();
        ctx.globalAlpha=fade*0.35; ctx.beginPath(); ctx.arc(q3[0],q3[1],6,0,7); ctx.fill(); ctx.globalAlpha=1; }
    }
    if(!reduce&&e>TUP+TDEP+THOLD){ L=null; box.classList.remove('liftoff'); btn&&(btn.disabled=false); }
  }
  function pad(t,fade){ var q=proj(L.f[0],1); if(q[2]<=0) return; var ph=reduce?0.5:((t/900)%1);
    ctx.strokeStyle='rgba(255,154,60,'+((1-ph)*(fade==null?1:fade))+')'; ctx.lineWidth=1.5; ctx.beginPath(); ctx.arc(q[0],q[1],3+ph*12,0,7); ctx.stroke();
    ctx.fillStyle='#ff9a3c'; ctx.beginPath(); ctx.arc(q[0],q[1],2.5,0,7); ctx.fill();
    if(L.label){ ctx.globalAlpha=fade==null?1:fade; ctx.font='500 12px "JetBrains Mono",ui-monospace,monospace'; ctx.textAlign='right'; ctx.fillStyle='#ffc08a'; ctx.fillText(L.label,q[0]-10,q[1]+18); ctx.globalAlpha=1; } }
  function where(p){ return (p||'').split(',')[0]; }
  function liftoff(d){
    if(!d) return; if(!ready){ pending=d; start(); return; }
    var now=performance.now(); L={t:now+(reduce?0:1300),f:frame3(d.lat*R,d.lon*R,d.az*R),n:d.n,c:d.c,label:where(d.p)};
    aim={t:now,l0:lam,p0:phi,l1:-(d.lon*R)-35*R,p1:Math.max(-0.9,Math.min(0.9,d.lat*R+12*R))};
    // shortest way round
    while(aim.l1-aim.l0>Math.PI) aim.l1-=2*Math.PI; while(aim.l1-aim.l0<-Math.PI) aim.l1+=2*Math.PI;
    if(reduce){ lam=aim.l1; phi=aim.p1; aim=null; }
    box.classList.add('liftoff'); if(btn&&!reduce) btn.disabled=true;
    var who={'starlink-dtc':'Starlink Direct to Cell','ast':'BlueBird','globalstar':'Globalstar','lynk':'Lynk'}[d.c]||'';
    status.textContent='Launch moment (illustrative): '+(d.r||'A rocket')+' lifts off from '+where(d.p)+' for '+d.m+' and '+(d.n?'releases '+d.n+' '+who+' satellites into orbit.':'releases its payload into orbit.');
    if(reduce) render(performance.now()); else play();
  }
  function frame(t){ if(!running) return; requestAnimationFrame(frame); if(t-last<33) return; var dt=last?Math.min(100,t-last):33; last=t;
    if(aim){ var k=ease((t-aim.t)/1200); lam=aim.l0+(aim.l1-aim.l0)*k; phi=aim.p0+(aim.p1-aim.p0)*k; if(k>=1) aim=null; }
    else if(!drag&&!L) lam+=dt*0.00007;
    render(t); }
  function play(){ if(reduce||running||!visible||document.hidden) return; running=true; last=0; requestAnimationFrame(frame); }
  function pause(){ running=false; }
  function start(){
    if(started) return; started=true;
    cv=document.createElement('canvas'); cv.setAttribute('aria-hidden','true'); box.appendChild(cv); ctx=cv.getContext('2d'); resize(); build();
    fetch((sec.getAttribute('data-base')||'')+'assets/globe-dots.json').then(function(r){return r.json();}).then(function(d){land=d;}).catch(function(){}).then(function(){
      ready=true; box.classList.add('ready'); t0=performance.now(); render(t0); play();
      if(pending){ var d=pending; pending=null; liftoff(d); }
      else if(/[?#&]liftoff/.test(location.search+location.hash)&&demo) liftoff(demo);
    });
    addEventListener('resize',function(){ resize(); render(performance.now()); });
    cv.addEventListener('pointerdown',function(e){ drag={x:e.clientX,y:e.clientY,l:lam,p:phi}; cv.setPointerCapture(e.pointerId); });
    cv.addEventListener('pointermove',function(e){ if(!drag) return; lam=drag.l+(e.clientX-drag.x)*0.006; phi=Math.max(-1.1,Math.min(1.1,drag.p+(e.clientY-drag.y)*0.006)); if(!running) render(performance.now()); });
    cv.addEventListener('pointerup',function(){ drag=null; }); cv.addEventListener('pointercancel',function(){ drag=null; });
  }
  if(btn){ if(!demo) btn.hidden=true; btn.addEventListener('click',function(){ liftoff(demo); }); }
  document.addEventListener('fd:liftoff',function(e){ var net=e.detail&&e.detail.net, d=null;
    for(var i=0;i<queue.length;i++) if(queue[i].net===net){ d=queue[i]; break; } liftoff(d||queue[0]); });
  if('IntersectionObserver' in window){
    new IntersectionObserver(function(es){ visible=es[0].isIntersecting; if(visible){ if(!started) (window.requestIdleCallback||setTimeout)(start,{timeout:1200}); else play(); } else pause(); },{threshold:0.2}).observe(box);
  } else { visible=true; start(); }
  document.addEventListener('visibilitychange',function(){ document.hidden?pause():play(); });
})();
