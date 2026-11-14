/* Full Duplex flight view (/launches/flight/): a webcast-style infographic for an upcoming launch.
   Ascent profile (SVG), stage events, speed/altitude gauges and a mission clock against T-0 from data/launches.json.
   Event times come from the cited mission page or a clearly labelled generic profile (src/flight-profiles.json).
   Speed and altitude are interpolated estimates, never telemetry. Respects prefers-reduced-motion. */
(function(){
  var el=document.getElementById('fl-data'), svg=document.getElementById('fl-svg'); if(!el||!svg) return;
  var D; try{D=JSON.parse(el.textContent);}catch(e){return;}
  var $=function(id){return document.getElementById(id);};
  var reduce=window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches;
  var NS='http://www.w3.org/2000/svg', L=null, P=null, TEND=0, MAXA=1, K=20, mode='live', rT0=0, rStart=0, raf=0, tick=0, lastIdx=-2;
  var X0=70, X1=975, Y0=290, Y1=40, VW=1000, SHORT={maxq:'MAX-Q',meco:'MECO',sep:'STAGE SEP',ses:'ENGINE START',fairing:'FAIRING',landing:'LANDING',seco:'ENGINE CUTOFF',deploy:'DEPLOY',liftoff:'LIFTOFF',other:''};
  var PRECISE={Second:1,Minute:1,Hour:1};
  function u(t){ return t<=0?0:Math.min(1,Math.log(1+t/K)/Math.log(1+TEND/K)); }
  function tOf(v){ return K*(Math.exp(v*Math.log(1+TEND/K))-1); }
  function state(t){ var k=P.keypoints; if(t<=0) return [0,0]; if(t>=k[k.length-1][0]) return [k[k.length-1][1],k[k.length-1][2]];
    for(var i=1;i<k.length;i++) if(t<=k[i][0]){ var a=k[i-1], b=k[i], f=(t-a[0])/(b[0]-a[0]); return [a[1]+(b[1]-a[1])*f, a[2]+(b[2]-a[2])*f]; } }
  function xy(t){ var s=state(t); return [X0+(X1-X0)*u(t), Y0-(Y0-Y1)*Math.sqrt(s[0]/MAXA)]; }
  function mk(tag,attrs,parent,text){ var n=document.createElementNS(NS,tag); for(var a in attrs) n.setAttribute(a,attrs[a]); if(text!=null) n.textContent=text; (parent||svg).appendChild(n); return n; }
  function pad2(n){ return (n<10?'0':'')+n; }
  function hms(s){ s=Math.floor(Math.abs(s)); return Math.floor(s/3600)+':'+pad2(Math.floor(s%3600/60))+':'+pad2(s%60); }
  function clock(t){ var s=Math.floor(Math.abs(t)), d=Math.floor(s/86400); s%=86400;
    return (t<0?'T− ':'T+ ')+(d?d+'d ':'')+pad2(Math.floor(s/3600))+':'+pad2(Math.floor(s%3600/60))+':'+pad2(s%60); }
  var path, flown, dot, glow, nowLine, marks=[];
  function draw(){
    while(svg.firstChild) svg.removeChild(svg.firstChild); marks=[];
    var narrow=(svg.parentNode.clientWidth||1000)<640; VW=narrow?600:1000; X0=narrow?84:70; X1=VW-22; Y0=narrow?350:290; Y1=narrow?50:40;
    svg.setAttribute('viewBox','0 0 '+VW+' '+(Y0+50)); svg.classList.toggle('narrow',narrow);
    var defs=mk('defs',{}), g=mk('radialGradient',{id:'flglow'},defs); mk('stop',{offset:'0','stop-color':'#fff'},g); mk('stop',{offset:'.35','stop-color':'#ffb06a','stop-opacity':'.85'},g); mk('stop',{offset:'1','stop-color':'#ff9a3c','stop-opacity':'0'},g);
    // altitude grid (sqrt scale so the early climb is visible)
    var step=MAXA>300?100:50;
    for(var a=step;a<MAXA;a+=step){ var y=Y0-(Y0-Y1)*Math.sqrt(a/MAXA); mk('line',{x1:X0,x2:X1,y1:y,y2:y,class:'fl-grid'}); mk('text',{x:X0-8,y:y+4,class:'fl-ax','text-anchor':'end'},null,a+' km'); }
    mk('line',{x1:X0,x2:X1,y1:Y0,y2:Y0,class:'fl-ground'});
    [60,600,3600].forEach(function(t){ if(t<TEND*0.9){ var x=X0+(X1-X0)*u(t); mk('text',{x:x,y:Y0+40,class:'fl-ax','text-anchor':'middle'},null,'T+'+(t<3600?(t/60)+' min':'1 hr')); mk('line',{x1:x,x2:x,y1:Y0,y2:Y0+6,class:'fl-ground'}); } });
    mk('text',{x:X0,y:Y0+40,class:'fl-ax','text-anchor':'start'},null,'time →');
    var d='', N=220; for(var i=0;i<=N;i++){ var p=xy(tOf(i/N)); d+=(i?'L':'M')+p[0].toFixed(1)+' '+p[1].toFixed(1); }
    path=mk('path',{d:d,class:'fl-plan'}); flown=mk('path',{d:'',class:'fl-flown'});
    // booster return arc for recovered boosters
    var sep=null, land=null; P.events.forEach(function(e){ if(e[1]==='sep'&&sep==null) sep=e[0]; if(e[1]==='landing') land=e[0]; });
    if(P.booster==='landing'&&sep!=null&&land!=null){ var s0=xy(sep), lx=X0+(X1-X0)*u(land);
      mk('path',{d:'M'+s0[0]+' '+s0[1]+' Q'+((s0[0]+lx)/2)+' '+(s0[1]-30)+' '+lx+' '+Y0,class:'fl-boost'}); }
    // event markers, labels staggered to avoid overlaps
    var lastX=[-99,-99,-99], seen={};
    P.events.forEach(function(e,i){ var t=e[0], k=e[1], p=(k==='landing')?[X0+(X1-X0)*u(t),Y0]:xy(t);
      var c=mk('circle',{cx:p[0],cy:p[1],r:k==='deploy'?7:5.5,class:'fl-ev k-'+k}); var tl=mk('title',{},c,e[2]+' · T+'+hms(t));
      var lab=seen[k]?'':SHORT[k]; seen[k]=1; var row=-1; if(lab){ for(var r=0;r<3;r++) if(p[0]-lastX[r]>(narrow?96:78)){ row=r; break; } }
      var txt=null; if(row>=0){ lastX[row]=p[0]; var ly=k==='landing'?Y0-14-row*16:p[1]-16-row*16; if(ly<14) ly=p[1]+26+row*16;
        txt=mk('text',{x:p[0],y:ly,class:'fl-lab','text-anchor':'middle'},null,lab); }
      marks.push({t:t,c:c,txt:txt}); });
    nowLine=mk('line',{x1:X0,x2:X0,y1:Y1-20,y2:Y0,class:'fl-now'});
    glow=mk('circle',{cx:X0,cy:Y0,r:18,fill:'url(#flglow)'}); dot=mk('circle',{cx:X0,cy:Y0,r:4.5,class:'fl-dot'});
  }
  function events(){
    var ol=$('fl-events'); ol.innerHTML='';
    P.events.forEach(function(e){ var li=document.createElement('li'); li.className='fe fe-'+e[1]; li.setAttribute('data-t',e[0]);
      li.innerHTML='<span class=fe-t>T+'+hms(e[0])+'</span><span class=fe-b><b></b> </span>'; li.querySelector('b').textContent=e[2]; li.querySelector('.fe-b').appendChild(document.createTextNode(e[3])); ol.appendChild(li); });
  }
  function esc(s){ var d=document.createElement('div'); d.textContent=s; return d.innerHTML; }
  function setLaunch(key,push){
    var l=null; for(var i=0;i<D.l.length;i++) if(D.l[i].s===key||D.l[i].id===key) l=D.l[i]; L=l||D.l[0]; P=D.p[L.p]||D.p.generic;
    TEND=Math.max(P.events[P.events.length-1][0],P.keypoints[P.keypoints.length-1][0])*1.04; MAXA=0; P.keypoints.forEach(function(k){MAXA=Math.max(MAXA,k[1]);}); MAXA*=1.12;
    $('fl-mission').textContent=L.m; $('fl-veh').textContent=L.r+' · '+L.loc+(L.st?' · '+L.st:'');
    $('fl-why').textContent=L.why; $('fl-pay').textContent=P.pay||''; $('fl-pay').hidden=!P.pay;
    var src=P.src?'Event times: <a href="'+esc(P.src.url)+'">'+esc(P.src.label)+'</a>, checked '+esc(P.src.checked)+'. ':'';
    $('fl-src').innerHTML=src+esc(P.basis||'')+' Speed and altitude between events are Full Duplex estimates.';
    var sel=$('fl-sel'); if(sel.value!==L.s) sel.value=L.s;
    [].forEach.call(document.querySelectorAll('.fl-quick .chip'),function(a){ a.getAttribute('data-l')===L.s?a.setAttribute('aria-current','true'):a.removeAttribute('aria-current'); });
    if(push&&history.replaceState) history.replaceState(null,'','?l='+encodeURIComponent(L.s));
    draw(); events(); lastIdx=-2; setMode('live');
    document.dispatchEvent(new CustomEvent('fd:flight',{detail:L}));
  }
  function liveT(){ return (Date.now()-Date.parse(L.n))/1000; }
  function render(t){
    var p=xy(Math.max(0,t)), s=state(Math.max(0,t));
    glow.setAttribute('cx',p[0]); glow.setAttribute('cy',p[1]); dot.setAttribute('cx',p[0]); dot.setAttribute('cy',p[1]);
    nowLine.setAttribute('x1',p[0]); nowLine.setAttribute('x2',p[0]);
    var d='', N=Math.max(2,Math.round(220*u(Math.max(0,t)))); if(t>0) for(var i=0;i<=N;i++){ var q=xy(tOf(u(t)*i/N)); d+=(i?'L':'M')+q[0].toFixed(1)+' '+q[1].toFixed(1); }
    flown.setAttribute('d',d);
    $('fl-spd').textContent=Math.round(s[1]).toLocaleString('en-GB'); $('fl-alt').textContent=(s[0]<10?s[0].toFixed(1):Math.round(s[0])).toLocaleString('en-GB');
    $('fl-spd-arc').style.strokeDasharray=(Math.min(1,s[1]/30000)*100)+' 100'; $('fl-alt-arc').style.strokeDasharray=(Math.min(1,s[0]/MAXA)*100)+' 100';
    var imprecise=mode==='live'&&!PRECISE[L.pr];
    $('fl-clock').textContent=imprecise?'T− '+L.w.split(' · ')[0]:clock(t);
    var idx=-1; for(var i2=0;i2<P.events.length;i2++) if(t>=P.events[i2][0]) idx=i2;
    if(idx!==lastIdx){ var lis=$('fl-events').children;
      for(var j=0;j<lis.length;j++){ lis[j].classList.toggle('done',j<=idx); lis[j].classList.toggle('next',j===idx+1); }
      marks.forEach(function(m,j){ m.c.classList.toggle('done',j<=idx); });
      if(lastIdx!==-2&&idx>lastIdx&&idx>=0&&mode!=='scrub') $('fl-status').textContent=P.events[idx][2]+' (T+'+hms(P.events[idx][0])+', planned).';
      lastIdx=idx; }
    var nx=P.events[idx+1], nt=$('fl-next');
    if(imprecise) nt.textContent='Launch time not set yet. Try “Replay the flight”.';
    else if(t<0) nt.textContent='Planned liftoff '+L.w+(mode==='live'?'':' · replay');
    else if(nx) nt.textContent='Next: '+nx[2]+' in '+hms(nx[0]-t);
    else nt.textContent=mode==='live'?'Planned profile complete. See where satellites are now, below.':'Profile complete.';
    if(mode!=='scrub') $('fl-range').value=Math.round(u(Math.max(0,t))*1000);
  }
  function stop(){ cancelAnimationFrame(raf); clearInterval(tick); raf=0; tick=0; }
  function setMode(m){
    stop(); mode=m;
    $('fl-live').setAttribute('aria-pressed',m==='live'); $('fl-replay').setAttribute('aria-pressed',m==='replay');
    $('fl-live').className='btn sm'+(m==='live'?'':' ghost'); $('fl-replay').className='btn sm'+(m==='replay'?'':' ghost');
    if(m==='live'){ render(liveT()); tick=setInterval(function(){ if(!document.hidden) render(liveT()); },250); }
    if(m==='replay'){ rStart=performance.now(); $('fl-status').textContent='Replaying the planned flight, sped up.'; lastIdx=-1;
      var DUR=18000, PRE=2000;
      (function f(now){ var e=now-rStart, t; if(e<PRE) t=-10+10*e/PRE; else t=tOf(Math.min(1,(e-PRE)/DUR));
        render(t); if(e<PRE+DUR) raf=requestAnimationFrame(f); else { raf=0; $('fl-replay').textContent='Replay again'; } })(rStart); }
  }
  $('fl-live').addEventListener('click',function(){ setMode('live'); $('fl-status').textContent='Live clock: counting to the planned launch time.'; });
  if(reduce){ $('fl-replay').hidden=true; }
  $('fl-replay').addEventListener('click',function(){ this.textContent='Replay the flight'; setMode('replay'); });
  $('fl-range').addEventListener('input',function(){ if(mode!=='scrub') setMode('scrub'); render(tOf(this.value/1000)); this.setAttribute('aria-valuetext','T+'+hms(tOf(this.value/1000))); });
  $('fl-sel').addEventListener('change',function(){ setLaunch(this.value,true); });
  [].forEach.call(document.querySelectorAll('.fl-quick .chip'),function(a){ a.addEventListener('click',function(e){ e.preventDefault(); setLaunch(a.getAttribute('data-l'),true); }); });
  document.addEventListener('visibilitychange',function(){ if(!document.hidden&&mode==='live') render(liveT()); });
  var rw=0; addEventListener('resize',function(){ var w=svg.parentNode.clientWidth; if((w<640)!==(rw<640)){ rw=w; var v=$('fl-range').value; draw(); lastIdx=-2; render(mode==='live'?liveT():tOf(v/1000)); } rw=w; });
  var q=(location.search.match(/[?&]l=([^&#]+)/)||[])[1];
  setLaunch(q?decodeURIComponent(q):D.l[0].s,false);
  if(/[?&]replay/.test(location.search)&&!reduce) setMode('replay');
})();
