/* Full Duplex home hero: "the race to your phone". Canvas only, no libraries, no trackers.
   Every number comes from the page's data-race attribute, built by scripts/build.py from data/race.json (monthly satellites in orbit
   and dated milestones), data/constellations.json (today's counts) and data/tracker.json (partner networks and their status).
   1 dot = 1 phone-capable satellite. Respects prefers-reduced-motion (static final frame). */
(function(){
  var fig=document.getElementById('hr-stage'); if(!fig) return;
  var cv=fig.querySelector('canvas'), ctx=cv.getContext&&cv.getContext('2d'); if(!ctx) return;
  var D; try{D=JSON.parse(fig.getAttribute('data-race'));}catch(e){return;}
  var root=document.documentElement, clip=/[?&]clip\b/.test(location.search), step=clip&&/[?&]step\b/.test(location.search); // step: frame-by-frame capture for the X clip
  if(clip) root.classList.add('hr-clip');
  var RM=window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches&&!clip;
  var elDate=fig.querySelector('.hr-date'), elTot=fig.querySelector('.hr-tot b'), pops=fig.querySelector('.hr-pops'), endc=fig.querySelector('.hr-end'), rp=document.getElementById('hr-replay');
  var MON=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  var ms=function(s){return Date.parse(s+'T00:00:00Z');};
  var S=D.s, F=D.f.map(function(f){return {t:ms(f[0]),v:f[1]};}), E=D.e.map(function(e){return {t:ms(e[0]),d:e[0],s:e[1],x:e[2]};});
  var col={}; S.forEach(function(s){col[s.id]=s.c;});
  // timeline: every month gets BASE ms, plus EV ms for each milestone inside it, so pop-ups have time to be read
  var INTRO=900, BASE=clip?270:260, EV=clip?1050:1000, seg=[], T=INTRO;
  for(var k=0;k<F.length-1;k++){var n=E.filter(function(e){return e.t>F[k].t&&e.t<=F[k+1].t;}).length, d=BASE+EV*n; seg.push({a:T,b:T+d}); T+=d;}
  var TEND=T, TPH=TEND+1400, TCARD=TEND+2200;
  // geometry
  var K=1,W=0,H=0,DPR=1,cx=0,cy=0,re=0,hubs={},phones=[],dots={};
  var ORDER=['starlink-dtc','ast','globalstar','lynk','skylo'];
  var HANG={'starlink-dtc':180,'ast':-40,'globalstar':2,'lynk':34,'skylo':64};
  function layout(){
    var r=cv.getBoundingClientRect(); W=r.width; H=r.height; if(!W||!H) return;
    DPR=Math.min(window.devicePixelRatio||1,2); cv.width=Math.round(W*DPR); cv.height=Math.round(H*DPR);
    var m=Math.min(W,H), wide=W/H>1.5; K=wide?1.3:1; cx=W*.5; cy=H*.5; re=m*(wide?.14:.11);
    var rx1=W*(wide?.24:.3), ry1=H*(wide?.3:.29), rx2=W*(wide?.4:.45), ry2=H*(wide?.43:.43);
    // phone ring: one arc per operator, Starlink on the left, the rest on the right; small groups get a minimum width
    var wgt={}, tot=0; ORDER.forEach(function(id){var n=(D.p[id]||[]).length; wgt[id]=n?Math.max(n,3):0; tot+=wgt[id];});
    var sl=wgt['starlink-dtc']/tot*360, a=180-sl/2; phones=[];
    var seq=['starlink-dtc','skylo','lynk','globalstar','ast']; // clockwise from bottom-left, ending top-right
    seq.forEach(function(id){var ps=D.p[id]||[], span=wgt[id]/tot*360;
      ps.forEach(function(p,i){var th=(a+span*(i+.5)/ps.length)*Math.PI/180*-1; // negative: run anticlockwise on screen
        phones.push({id:id,l:p[0],st:p[1],x:cx+rx2*Math.cos(th),y:cy-ry2*Math.sin(th)*-1,i:phones.length});});
      a+=span;});
    S.forEach(function(s){var th=HANG[s.id]*Math.PI/180; hubs[s.id]={x:cx+rx1*Math.cos(th)*(s.id==='starlink-dtc'?.92:1),y:cy+ry1*Math.sin(th)};});
    var c=m*.0047*K; // phyllotaxis pitch: 1 dot = 1 satellite
    S.forEach(function(s){var n=Math.max(s.n||0,s.max||0), arr=[]; for(var i=0;i<n;i++){var rr=c*Math.sqrt(i+.5)*1.18, an=i*2.39996; arr.push({r:rr,a:an,b:-1});} dots[s.id]=arr;});
    hubs.c=c;
  }
  // state
  var t=0,last=0,raf=0,running=false,done=false,visible=false,parts=[],shown={},prevN={},emitAt={},popEl=null,popT=0;
  function counts(tt){
    var out={}; if(tt<=INTRO){S.forEach(function(s){out[s.id]=F[0].v[s.id]||0;}); return {v:out,date:F[0].t,k:-1};}
    if(tt>=TEND){S.forEach(function(s){out[s.id]=F[F.length-1].v[s.id]||0;}); return {v:out,date:F[F.length-1].t,k:F.length};}
    for(var k=0;k<seg.length;k++) if(tt<seg[k].b){var p=(tt-seg[k].a)/(seg[k].b-seg[k].a);
      S.forEach(function(s){var a=F[k].v[s.id]||0,b=F[k+1].v[s.id]||0; out[s.id]=a+(b-a)*p;});
      return {v:out,date:F[k].t+(F[k+1].t-F[k].t)*p,k:k};}
  }
  function fmt(d,full){var x=new Date(d); return (full?x.getUTCDate()+' ':'')+MON[x.getUTCMonth()]+' '+x.getUTCFullYear();}
  function bez(p,q,u,bend){var mx=(p.x+q.x)/2,my=(p.y+q.y)/2,dx=q.x-p.x,dy=q.y-p.y,ox=mx-dy*bend,oy=my+dx*bend,v=1-u;
    return {x:v*v*p.x+2*v*u*ox+u*u*q.x,y:v*v*p.y+2*v*u*oy+u*u*q.y,ox:ox,oy:oy};}
  function emit(a,b,c,dur,bend){if(parts.length<260) parts.push({a:a,b:b,c:c,t0:t,d:dur,bend:bend});}
  function pop(e){
    if(!pops) return; var el=document.createElement('p'); el.className='hr-pop'; el.style.setProperty('--c',col[e.s]||'#fff');
    var x=new Date(e.t); el.innerHTML='<time>'+x.getUTCDate()+' '+MON[x.getUTCMonth()]+' '+x.getUTCFullYear()+'</time>';
    el.appendChild(document.createTextNode(e.x)); pops.appendChild(el); popEl=el; popT=t;
    while(pops.children.length>1) pops.removeChild(pops.firstChild); // one slot: each milestone stays until the next one
  }
  function phone(x,y,s,c,a){ctx.globalAlpha=a; ctx.strokeStyle=c; ctx.lineWidth=1.3; var w=s*.62,h=s;
    ctx.beginPath(); if(ctx.roundRect) ctx.roundRect(x-w/2,y-h/2,w,h,s*.14); else ctx.rect(x-w/2,y-h/2,w,h); ctx.stroke();
    ctx.fillStyle=c; ctx.globalAlpha=a*.25; ctx.fill(); ctx.globalAlpha=a; ctx.fillRect(x-w*.18,y+h*.3,w*.36,1.2);}
  function draw(){
    var st=counts(t), now=t; ctx.setTransform(DPR,0,0,DPR,0,0); ctx.clearRect(0,0,W,H);
    var intro=Math.min(1,t/INTRO), ph=Math.max(0,Math.min(1,(t-TEND)/(TPH-TEND)));
    // links Earth -> hub
    S.forEach(function(s){var h=hubs[s.id], n=st.v[s.id]; var on=(n>0||!s.n)?1:.25; var q=bez({x:cx,y:cy},h,.5,.12);
      ctx.globalAlpha=.22*intro*on; ctx.strokeStyle=s.c; ctx.lineWidth=1; if(!s.n) ctx.setLineDash([3,4]);
      ctx.beginPath(); ctx.moveTo(cx,cy); ctx.quadraticCurveTo(q.ox,q.oy,h.x,h.y); ctx.stroke(); ctx.setLineDash([]);});
    // links hub -> partner phones (today, from the tracker)
    if(ph>0) phones.forEach(function(p){var h=hubs[p.id]; if(!h) return; var q=bez(h,p,.5,.08), a=Math.max(0,Math.min(1,ph*1.6-p.i/phones.length*.6));
      ctx.globalAlpha=(p.st==='announced'?.12:.2)*a; ctx.strokeStyle=col[p.id]; ctx.lineWidth=1; if(p.st==='announced') ctx.setLineDash([2,4]);
      ctx.beginPath(); ctx.moveTo(h.x,h.y); ctx.quadraticCurveTo(q.ox,q.oy,p.x,p.y); ctx.stroke(); ctx.setLineDash([]); p.a=a;});
    // Earth
    ctx.globalAlpha=intro; var g=ctx.createRadialGradient(cx-re*.35,cy-re*.4,re*.1,cx,cy,re); g.addColorStop(0,'#2a5c9a'); g.addColorStop(.6,'#123158'); g.addColorStop(1,'#081a33');
    var halo=ctx.createRadialGradient(cx,cy,re*.9,cx,cy,re*1.7); halo.addColorStop(0,'rgba(94,200,255,.28)'); halo.addColorStop(1,'rgba(94,200,255,0)');
    ctx.fillStyle=halo; ctx.beginPath(); ctx.arc(cx,cy,re*1.7,0,7); ctx.fill();
    ctx.fillStyle=g; ctx.beginPath(); ctx.arc(cx,cy,re,0,7); ctx.fill();
    ctx.save(); ctx.beginPath(); ctx.arc(cx,cy,re,0,7); ctx.clip(); ctx.strokeStyle='rgba(143,219,255,.22)'; ctx.lineWidth=.8;
    for(var i=-2;i<=2;i++){ctx.beginPath(); ctx.ellipse(cx,cy+i*re*.36,re*Math.sqrt(1-Math.pow(i*.36,2)),re*.08,0,0,7); ctx.stroke();}
    var rot=(t/9000)%1; for(i=0;i<4;i++){var ph2=((rot+i/4)%1)*Math.PI; ctx.beginPath(); ctx.ellipse(cx,cy,Math.abs(Math.cos(ph2))*re,re,0,0,7); ctx.stroke();}
    ctx.restore(); ctx.strokeStyle='rgba(143,219,255,.6)'; ctx.lineWidth=1.2; ctx.beginPath(); ctx.arc(cx,cy,re,0,7); ctx.stroke();
    // satellite clusters
    var spin=t/60000;
    S.forEach(function(s){var h=hubs[s.id], n=st.v[s.id], arr=dots[s.id]||[];
      if(!s.n){ // no satellites of its own (Skylo): a hollow node
        ctx.globalAlpha=.85*intro; ctx.strokeStyle=s.c; ctx.lineWidth=1.4; ctx.beginPath(); ctx.arc(h.x,h.y,hubs.c*3.2,0,7); ctx.stroke();
        ctx.globalAlpha=.35*intro; ctx.beginPath(); ctx.arc(h.x,h.y,hubs.c*5.2,0,7); ctx.stroke();}
      ctx.fillStyle=s.c;
      for(var i=0;i<arr.length;i++){var d=arr[i], vis=Math.max(0,Math.min(1,n-i)); if(vis<=0){d.b=-1; continue;}
        if(d.b<0) d.b=now; var age=now-d.b, glow=RM?0:Math.max(0,1-age/700), an=d.a+spin*(1+12/(d.r+4));
        var x=h.x+Math.cos(an)*d.r, y=h.y+Math.sin(an)*d.r, rr=hubs.c*(.34+glow*.9);
        ctx.globalAlpha=Math.min(1,vis*(.82+glow*.18))*intro; ctx.beginPath(); ctx.arc(x,y,rr,0,7); ctx.fill();}
      // launches: particles up from Earth when a cluster grows
      var whole=Math.floor(n); if(!RM&&prevN[s.id]!==undefined&&whole>prevN[s.id]&&t<TEND){var k=Math.min(3,whole-prevN[s.id]); while(k--) emit({x:cx,y:cy},h,s.c,900+Math.random()*500,.12);}
      prevN[s.id]=whole;
      if(!RM&&(n>0||!s.n)&&t>INTRO&&t>(emitAt[s.id]||0)){emit({x:cx,y:cy},h,s.c,1300,.12); if(t>TEND) emit(h,{x:cx,y:cy},s.c,1300,-.12); emitAt[s.id]=t+(t>TEND?1400:2200)/(1+Math.log(1+(s.n||3))/3);}
      // label: name and the true count at this point in time
      ctx.globalAlpha=intro; var fs=Math.max(10.5,Math.min(13.5,W/52))*K; ctx.font='600 '+fs+'px "Inter Tight",system-ui,sans-serif'; ctx.textAlign='center';
      var ly=h.y+(arr.length?Math.max(arr.length?arr[arr.length-1].r:0,0)+fs*1.35:hubs.c*5.2+fs*1.3);
      if(s.id==='starlink-dtc'){ly=h.y+(arr.length?arr[arr.length-1].r:0)+fs*1.5;}
      ctx.fillStyle='#e8eef7'; ctx.fillText(s.l,h.x,ly); ctx.fillStyle=s.c; ctx.font='500 '+(fs*.92)+'px "JetBrains Mono",ui-monospace,monospace';
      ctx.fillText(s.n?Math.round(n).toLocaleString('en-GB'):(s.note||''),h.x,ly+fs*1.2);});
    // phones and both-way traffic (full duplex)
    if(ph>0){var ps=Math.max(9,Math.min(15,W/48))*K; phones.forEach(function(p){var c=p.st==='live'?'#6ee79a':p.st==='trial'?'#f5c26b':p.st==='announced'?'#7f93a8':col[p.id]; phone(p.x,p.y,ps,c,p.a||0);
      if(!RM&&p.a>.9&&p.st!=='announced'&&Math.random()<(p.st==='live'?.012:.005)){var h=hubs[p.id]; if(Math.random()<.5) emit(h,p,col[p.id],1100,.08); else emit(p,h,'#6ee79a',1100,-.08);}});}
    // particles
    ctx.globalAlpha=1; parts=parts.filter(function(q){var u=(t-q.t0)/q.d; if(u>=1) return false; var b=bez(q.a,q.b,u,q.bend);
      ctx.globalAlpha=Math.sin(u*Math.PI); ctx.fillStyle=q.c; ctx.beginPath(); ctx.arc(b.x,b.y,hubs.c*.7,0,7); ctx.fill();
      ctx.globalAlpha*=.25; ctx.beginPath(); ctx.arc(b.x,b.y,hubs.c*2,0,7); ctx.fill(); return true;});
    ctx.globalAlpha=1;
    // counter and milestones
    if(elDate){var tx=t>=TEND?fmt(st.date,true):fmt(st.date); if(elDate.textContent!==tx) elDate.textContent=tx;}
    if(elTot){var tot=0; S.forEach(function(s){tot+=Math.round(st.v[s.id]||0);}); var tt=tot.toLocaleString('en-GB'); if(elTot.textContent!==tt) elTot.textContent=tt;}
    E.forEach(function(e,i){if(!shown[i]&&st.date>=e.t&&t>INTRO){shown[i]=1; if(!RM) pop(e);}});
    // fades are driven by the animation clock (not CSS), so a frame-by-frame capture matches what people see
    if(popEl){var pa=Math.min(1,(t-popT)/350); popEl.style.opacity=pa; popEl.style.transform='translateY('+((1-pa)*8).toFixed(1)+'px)';}
    var ea=Math.max(0,Math.min(1,(t-TCARD)/600)); if(endc){endc.style.opacity=ea; endc.style.transform=ea<1?'translateY('+((1-ea)*8).toFixed(1)+'px)':'';} if(pops) pops.style.opacity=1-ea;
    if(t>=TCARD&&!done){done=true; fig.classList.add('is-end');}
  }
  function frame(ts){
    if(!running) return; var dt=last?Math.min(50,ts-last):16; last=ts; t+=dt; draw();
    if(t>TCARD+40000&&!clip){running=false; return;} // settle after a while to save battery
    raf=requestAnimationFrame(frame);
  }
  function play(){if(running||RM) return; running=true; last=0; raf=requestAnimationFrame(frame);}
  function pause(){running=false; cancelAnimationFrame(raf);}
  function finalFrame(){t=TCARD+700; S.forEach(function(s){(dots[s.id]||[]).forEach(function(d){d.b=-1e9;});}); E.forEach(function(e,i){shown[i]=1;}); draw(); fig.classList.add('is-end'); done=true;}
  function replay(){pause(); RM=false; t=0; done=false; parts=[]; shown={}; prevN={}; emitAt={}; fig.classList.remove('is-end'); if(pops) pops.innerHTML=''; popEl=null;
    S.forEach(function(s){(dots[s.id]||[]).forEach(function(d){d.b=-1;});}); play();}
  layout();
  if(RM) finalFrame(); else draw();
  var rz; window.addEventListener('resize',function(){clearTimeout(rz); rz=setTimeout(function(){layout(); draw();},120);});
  if(rp) rp.addEventListener('click',replay); // a user-started replay plays even with reduced motion
  if(RM) return;
  if(step){window.__hr={TEND:TEND,TCARD:TCARD,step:function(dt){t+=dt; draw();}}; return;}
  if(clip) play(); else if('IntersectionObserver' in window){new IntersectionObserver(function(es){visible=es[0].isIntersecting; if(visible&&!document.hidden) play(); else pause();},{threshold:.25}).observe(fig);}
  else play();
  document.addEventListener('visibilitychange',function(){if(document.hidden) pause(); else if(visible) play();});
  window.__hr={TEND:TEND,TCARD:TCARD,replay:replay};
})();
