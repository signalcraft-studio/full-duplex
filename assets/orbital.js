/* Full Duplex home, variant B "Orbital": a dot globe with every phone-capable satellite on its real shell (heights to scale with the
   Earth, positions illustrative), additive glow, starfield, drag to spin, and "find your phone": pick country, network and phone
   (tracker + phones.json data from the page) and a beam runs from your country to that network's satellites, ending in its status.
   Canvas 2D, no libraries. Mobile and prefers-reduced-motion get a still poster frame; motion only follows a user action. */
(function(){
  var sec=document.querySelector('section.orb'); if(!sec) return;
  var cv=sec.querySelector('.orb-cv'), ctx=cv.getContext&&cv.getContext('2d'); if(!ctx) return;
  var D; try{D=JSON.parse(sec.getAttribute('data-orb'));}catch(e){return;}
  // set up only when the globe is near the screen, so it costs nothing at page load
  var stepQ=/[?&]step\b/.test(location.search);
  if(!stepQ&&'IntersectionObserver' in window){var io=new IntersectionObserver(function(es){if(es[0].isIntersecting){io.disconnect(); main();}},{rootMargin:'700px 0px'}); io.observe(sec);} else main();
  function main(){
  var R=Math.PI/180, RE=6371, clip=/[?&]clip\b/.test(location.search), step=/[?&]step\b/.test(location.search);
  if(clip) document.documentElement.classList.add('orb-clip');
  var RM=matchMedia('(prefers-reduced-motion: reduce)').matches&&!clip, SMALL=matchMedia('(max-width: 699px)').matches&&!clip;
  var POSTER=RM||SMALL; // still frame; animate only briefly after a user action
  var W=0,H=0,DPR=1,cx=0,cy=0,rad=0, lam=-10*R, phi=22*R, tl=lam, tp=phi, zoom=1, tz=1, t=0, last=0, running=false, visible=true, until=0;
  var land=null, sats=[], stars=null, glow={}, beam=null, drag=null;
  // satellites: one per real satellite, spread over planes; speed follows Kepler (period ~ a^1.5), sped up
  D.s.forEach(function(sh){var a=(RE+sh.alt)/RE, per=Math.pow(a,1.5), pl=Math.max(1,sh.pl), per_pl=Math.ceil(sh.n/pl);
    for(var k=0;k<sh.n;k++){var p=k%pl, j=Math.floor(k/pl); sats.push({id:sh.id,c:sh.c,a:a,inc:sh.inc*R,raan:2*Math.PI*p/pl+(sh.alt%7),u0:2*Math.PI*j/per_pl+p*0.37,w:0.00016/per});}});
  function sprite(c){if(glow[c]) return glow[c]; var s=document.createElement('canvas'), n=32; s.width=s.height=n; var g=s.getContext('2d'), gr=g.createRadialGradient(n/2,n/2,0,n/2,n/2,n/2);
    gr.addColorStop(0,'#fff'); gr.addColorStop(.18,c); gr.addColorStop(.45,c+'55'); gr.addColorStop(1,c+'00'); g.fillStyle=gr; g.fillRect(0,0,n,n); return glow[c]=s;}
  function size(){var r=cv.getBoundingClientRect(); W=r.width; H=r.height; if(!W||!H) return; DPR=Math.min(2,window.devicePixelRatio||1);
    cv.width=Math.round(W*DPR); cv.height=Math.round(H*DPR);
    var wide=W>=900||clip; cx=W*(clip?.5:wide?.55:.5); cy=H*(wide?.47:.5); rad=Math.min(W*(wide?(clip?.3:.2):.36),H*(clip?.36:wide?.33:.4));
    stars=document.createElement('canvas'); stars.width=cv.width; stars.height=cv.height; var g=stars.getContext('2d'), seed=7;
    function rnd(){seed=(seed*16807)%2147483647; return seed/2147483647;}
    for(var i=0;i<Math.round(W*H/2600);i++){var x=rnd()*stars.width, y=rnd()*stars.height, b=rnd(); g.fillStyle='rgba(220,232,255,'+(.15+b*.6).toFixed(2)+')'; g.fillRect(x,y,b>.92?2*DPR:1*DPR,b>.92?2*DPR:1*DPR);}}
  // world: y = north; camera turns by lam (longitude) and tilts by phi
  function world(lat,lon,r){var cl=Math.cos(lat); return [r*cl*Math.sin(lon), r*Math.sin(lat), r*cl*Math.cos(lon)];}
  function cam(v){var cl=Math.cos(lam), sl=Math.sin(lam), x=v[0]*cl-v[2]*sl, z=v[0]*sl+v[2]*cl, cp=Math.cos(phi), sp=Math.sin(phi), y=v[1]*cp-z*sp; z=v[1]*sp+z*cp;
    var f=4.2/(4.2-z*.55), s=rad*zoom*f; return {x:cx+x*s, y:cy-y*s, z:z, f:f};}
  function satPos(o,tt){var u=o.u0+tt*o.w, x=Math.cos(u), y0=Math.sin(u), ci=Math.cos(o.inc), si=Math.sin(o.inc), yN=y0*si, yE=y0*ci, cr=Math.cos(o.raan), sr=Math.sin(o.raan);
    return [o.a*(x*cr-yE*sr), o.a*yN, o.a*(x*sr+yE*cr)];}
  function hidden(p){return p.z<0&&Math.hypot(p.x-cx,p.y-cy)<rad*zoom*p.f*.99;}
  function draw(){
    ctx.setTransform(1,0,0,1,0,0); ctx.clearRect(0,0,cv.width,cv.height);
    if(stars){var ox=((lam/R)*0.6*DPR)%stars.width; ctx.globalAlpha=1; ctx.drawImage(stars,-ox,0); ctx.drawImage(stars,stars.width-ox,0);}
    ctx.setTransform(DPR,0,0,DPR,0,0);
    var r=rad*zoom;
    // atmosphere + ocean
    var g=ctx.createRadialGradient(cx,cy,r*.95,cx,cy,r*1.35); g.addColorStop(0,'rgba(94,200,255,.35)'); g.addColorStop(1,'rgba(94,200,255,0)'); ctx.fillStyle=g; ctx.beginPath(); ctx.arc(cx,cy,r*1.35,0,7); ctx.fill();
    g=ctx.createRadialGradient(cx-r*.35,cy-r*.4,r*.1,cx,cy,r*1.05); g.addColorStop(0,'#16345e'); g.addColorStop(1,'#050c1c'); ctx.fillStyle=g; ctx.beginPath(); ctx.arc(cx,cy,r*1.02,0,7); ctx.fill();
    // satellites behind the Earth first (dim), then land, then the front ones
    var pts=sats.map(function(o){return [o,cam(satPos(o,t))];});
    ctx.globalCompositeOperation='lighter';
    pts.forEach(function(q){var p=q[1]; if(p.z>=0||hidden(p)) return; var s=Math.max(2.2,r/60)*p.f; ctx.globalAlpha=.5; ctx.drawImage(sprite(q[0].c),p.x-s,p.y-s,s*2,s*2);});
    ctx.globalCompositeOperation='source-over';
    if(land){var dl=Math.max(1.1,r/170); for(var i=0;i<land.length;i+=3){var p=cam(world(land[i]/10*R,land[i+1]/10*R,1)); if(p.z<=0.02) continue; var st=land[i+2];
      ctx.globalAlpha=Math.min(1,.25+p.z*.9); ctx.fillStyle=st===3?'#6ee79a':st===2?'#f5c26b':st===1?'#8ea3b8':'#3d5f88'; ctx.fillRect(p.x-dl/2,p.y-dl/2,dl,dl);}}
    else{ctx.strokeStyle='rgba(143,219,255,.18)'; ctx.lineWidth=.8; for(var la=-60;la<=60;la+=30){ctx.beginPath(); for(var lo=-180;lo<=180;lo+=6){var p=cam(world(la*R,lo*R,1)); if(p.z<0){ctx.moveTo(p.x,p.y); continue;} ctx.lineTo(p.x,p.y);} ctx.stroke();}}
    ctx.globalAlpha=1; ctx.strokeStyle='rgba(143,219,255,.45)'; ctx.lineWidth=1; ctx.beginPath(); ctx.arc(cx,cy,r*1.02,0,7); ctx.stroke();
    // shell rings (true relative height) as faint halos
    D.s.forEach(function(sh){ctx.globalAlpha=.10; ctx.strokeStyle=sh.c; ctx.beginPath(); ctx.arc(cx,cy,r*(RE+sh.alt)/RE*1.0,0,7); ctx.stroke();});
    ctx.globalCompositeOperation='lighter';
    pts.forEach(function(q){var p=q[1]; if(p.z<0) return; var s=(beam&&beam.id&&q[0].id!==beam.id?.6:1)*Math.max(2.8,r/44)*p.f; ctx.globalAlpha=beam&&beam.id&&q[0].id!==beam.id?.25:.95; ctx.drawImage(sprite(q[0].c),p.x-s,p.y-s,s*2,s*2);});
    // beam: your country -> nearest satellite of your network (or straight up for Skylo's far-away geostationary partners)
    if(beam){var a=cam(world(beam.lat*R,beam.lon*R,1)), b=null, bd=1e9, k=Math.min(1,(t-beam.t0)/900);
      if(beam.id){pts.forEach(function(q){if(q[0].id!==beam.id||q[1].z<0) return; var d=Math.hypot(q[1].x-a.x,q[1].y-a.y); if(d<bd){bd=d;b=q[1];}});}
      if(!b){var up=world(beam.lat*R,beam.lon*R,beam.id?1.3:3.2); b=cam(up);}
      var ex=a.x+(b.x-a.x)*k, ey=a.y+(b.y-a.y)*k, lg=ctx.createLinearGradient(a.x,a.y,b.x,b.y); lg.addColorStop(0,'#ffffff'); lg.addColorStop(1,beam.c);
      ctx.globalAlpha=a.z>0?1:.35; ctx.strokeStyle=lg; ctx.lineWidth=2.2; if(beam.st==='announced'||beam.st==='none') ctx.setLineDash([4,5]);
      ctx.beginPath(); ctx.moveTo(a.x,a.y); ctx.lineTo(ex,ey); ctx.stroke(); ctx.setLineDash([]);
      ctx.globalAlpha=.35; ctx.lineWidth=8; ctx.beginPath(); ctx.moveTo(a.x,a.y); ctx.lineTo(ex,ey); ctx.stroke();
      for(var n=0;n<3;n++){var u=((t/900)+n/3)%1*k; ctx.globalAlpha=.9; ctx.drawImage(sprite(beam.c),a.x+(b.x-a.x)*u-7,a.y+(b.y-a.y)*u-7,14,14);}
      ctx.globalAlpha=1; ctx.drawImage(sprite('#ffffff'),a.x-9,a.y-9,18,18);}
    ctx.globalCompositeOperation='source-over'; ctx.globalAlpha=1;
  }
  function frame(ts){if(!running) return; var dt=last?Math.min(50,ts-last):16; last=ts; tick(dt); draw();
    if(POSTER&&ts>until){running=false; return;} requestAnimationFrame(frame);}
  function tick(dt){t+=dt; if(!drag&&!beam&&!POSTER) tl+=dt*0.00004; lam+=(tl-lam)*.06; phi+=(tp-phi)*.06; zoom+=(tz-zoom)*.06;}
  function play(ms){if(ms) until=performance.now()+ms; if(running) return; running=true; last=0; requestAnimationFrame(frame);}
  function stop(){running=false;}
  size(); draw();
  var rz; addEventListener('resize',function(){clearTimeout(rz); rz=setTimeout(function(){size(); draw();},150);});
  // land dots load after first paint (52 KB); the globe draws a graticule until then
  function loadLand(){fetch(sec.getAttribute('data-dots')).then(function(r){return r.json();}).then(function(j){land=j.p; draw();}).catch(function(){});}
  if('requestIdleCallback' in window) requestIdleCallback(loadLand,{timeout:1500}); else setTimeout(loadLand,300);
  // drag to spin
  cv.addEventListener('pointerdown',function(e){drag={x:e.clientX,y:e.clientY,l:tl,p:tp}; cv.setPointerCapture(e.pointerId);});
  cv.addEventListener('pointermove',function(e){if(!drag) return; tl=drag.l-(e.clientX-drag.x)*.006; tp=Math.max(-1.2,Math.min(1.2,drag.p+(e.clientY-drag.y)*.006)); play(1200);});
  cv.addEventListener('pointerup',function(){drag=null;});
  // find your phone
  var f=document.getElementById('fy'), out=f&&f.querySelector('.fy-out');
  var LBL={live:'Live',trial:'On trial',announced:'Announced',none:'Not yet'};
  function esc(s){return String(s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
  function find(c,o,p){
    var rows=D.r.filter(function(r){return r[0]===c&&(!o||o==='other'||r[1]===o||r[2].indexOf(o)>=0);});
    rows.sort(function(a,b){var k={live:3,trial:2,announced:1}; return k[b[4]]-k[a[4]];});
    var r=rows[0], ll=D.ctry[c]; if(!ll) return null;
    if(!r||(o==='other')) return {lat:ll[0],lon:ll[1],st:'none',c:'#7f93a8'};
    return {lat:ll[0],lon:ll[1],st:r[4],c:D.cols[r[3]]||'#8fdbff',id:D.ids[r[3]]||null,prov:r[3],row:r};
  }
  function result(b,p,c,o){
    var ctry=f.querySelector('[name=c]'), cn=ctry.options[ctry.selectedIndex].text;
    if(b.st==='none') return '<p class="fy-st s-none">Not yet</p><p>We don’t track a satellite-to-phone deal for that network in '+esc(cn)+'.</p><p><a class="btn sm" href="'+esc(D.sub)+'">Tell me when my network gets it</a></p>';
    var r=b.row, h='<p class="fy-st s-'+b.st+'">'+LBL[b.st]+'</p><p><strong>'+esc(r[6])+'</strong> with <strong>'+esc(r[8])+'</strong> in '+esc(r[5])+'. <a href="'+esc(r[7])+'">Source</a></p>';
    if(p){var L=D.lists[r[5]+'|'+r[6]], m=D.models[p]||p;
      if(L) h+='<p>'+esc(m)+': '+(L.y.indexOf(p)>=0?'listed on <a href="'+esc(L.u)+'">'+esc(L.l)+'</a>.':'not on <a href="'+esc(L.u)+'">'+esc(L.l)+'</a>, so check with your network.')+'</p>';
      else h+='<p>'+esc(m)+': no official phone list for this network yet. <a href="check/?c='+esc(c)+'&o='+esc(o||'')+'&p='+esc(p)+'">How to check your phone</a>.</p>';}
    if(b.st!=='live') h+='<p><a class="btn sm" href="'+esc(D.sub)+'">Tell me when it goes live</a></p>';
    if(!b.id) h+='<p class=d-stamp>'+(b.prov==='Skylo'?'Skylo uses partners’ geostationary satellites, far above this view.':'')+'</p>';
    var txt=r[6]+' + '+r[8]+' in '+r[5]+': '+LBL[b.st]+'. Find your phone in the sky on Full Duplex';
    h+='<p class=fy-share><a href="https://x.com/intent/post?text='+encodeURIComponent(txt)+'&url='+encodeURIComponent(D.base+'?utm_source=x&utm_medium=social&utm_campaign=find-your-phone#fy')+'">Share on X</a> · <a href="check/?c='+esc(c)+'&o='+esc(o||'')+'&p='+esc(p||'')+'">Full checker result</a></p>';
    return h;
  }
  function go(c,o,p){var b=find(c,o,p); if(!b) return false; b.t0=t; beam=b; tl=b.lon*R; tp=Math.max(-1,Math.min(1,b.lat*R*.9)); tz=1.12;
    while(tl-lam>Math.PI) tl-=2*Math.PI; while(lam-tl>Math.PI) tl+=2*Math.PI;
    if(out) out.innerHTML=result(b,p,c,o); play(POSTER?2600:0); return true;}
  if(f) f.addEventListener('submit',function(e){var c=f.c.value, o=f.o.value, p=f.p.value; if(!c||c==='other') return; e.preventDefault(); go(c,o,p);});
  // run: animate when on screen (desktop); poster frame otherwise
  if(step){window.__orb={go:go,step:function(dt){tick(dt); draw();},land:function(){return !!land;},spin:function(v){tl+=v;}}; return;}
  if(POSTER) return;
  if('IntersectionObserver' in window) new IntersectionObserver(function(es){visible=es[0].isIntersecting; if(visible&&!document.hidden) play(); else stop();}).observe(sec); else play();
  document.addEventListener('visibilitychange',function(){if(document.hidden) stop(); else if(visible) play();});
  }
})();
