/* Full Duplex home globe: a code-drawn dot globe from data in assets/globe-dots.json (built from
   data/tracker.json by scripts/build.py). No images, no libraries.
   Starts after page load when on screen; pauses off-screen and in background tabs; static under
   prefers-reduced-motion; drag to spin. Arcs are illustrative satellite passes, not real orbits. */
(function(){
  var box=document.getElementById('globe'); if(!box) return;
  var COL=['#3a5680','#7f93a8','#f5c26b','#6ee79a'], R=Math.PI/180;
  var reduce=window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches;
  function start(){
    fetch((box.getAttribute('data-base')||'')+'assets/globe-dots.json').then(function(r){return r.json()}).then(draw).catch(function(){box.classList.add('failed');});
  }
  function draw(data){
    var p=data.p, n=p.length/3, lat=new Float32Array(n), lon=new Float32Array(n), st=new Uint8Array(n);
    for(var i=0;i<n;i++){ lat[i]=p[3*i]/10*R; lon[i]=p[3*i+1]/10*R; st[i]=p[3*i+2]; }
    var cosLat=lat.map(Math.cos), sinLat=lat.map(Math.sin);
    var live=(data.live||[]).map(function(c){return [c[0]*R,c[1]*R];});
    var pairs=[[0,3],[1,5],[2,7],[4,9],[6,11]].filter(function(q){return live[q[0]]&&live[q[1]];});
    var cv=document.createElement('canvas'); cv.setAttribute('aria-hidden','true'); box.appendChild(cv);
    var ctx=cv.getContext('2d'), dpr=Math.min(2,window.devicePixelRatio||1), size=0, r=0;
    var lam=-5*R, phi=38*R; // view centre: lon 5E, lat 38N (Europe)
    function resize(){ size=box.clientWidth; cv.width=size*dpr; cv.height=size*dpr; cv.style.width=cv.style.height=size+'px'; r=size/2-4; }
    function proj(la,lo){ // orthographic, centred on (phi, -lam)
      var cl=Math.cos(la), dl=lo+lam, x=cl*Math.sin(dl), y=Math.cos(phi)*Math.sin(la)-Math.sin(phi)*cl*Math.cos(dl), z=Math.sin(phi)*Math.sin(la)+Math.cos(phi)*cl*Math.cos(dl);
      return [size/2+r*x, size/2-r*y, z];
    }
    function slerp(a,b,t){
      var ax=Math.cos(a[0])*Math.cos(a[1]), ay=Math.cos(a[0])*Math.sin(a[1]), az=Math.sin(a[0]), bx=Math.cos(b[0])*Math.cos(b[1]), by=Math.cos(b[0])*Math.sin(b[1]), bz=Math.sin(b[0]);
      var d=Math.acos(Math.max(-1,Math.min(1,ax*bx+ay*by+az*bz))), s=Math.sin(d)||1, k1=Math.sin((1-t)*d)/s, k2=Math.sin(t*d)/s;
      var x=k1*ax+k2*bx, y=k1*ay+k2*by, z=k1*az+k2*bz, h=1+0.06*Math.sin(Math.PI*t); // lift the arc slightly above the surface
      return [Math.atan2(z,Math.hypot(x,y)), Math.atan2(y,x), h];
    }
    function render(t){
      ctx.setTransform(dpr,0,0,dpr,0,0); ctx.clearRect(0,0,size,size);
      var sp=Math.sin(phi), cp=Math.cos(phi), ds=Math.max(1.4,size/230);
      for(var s=0;s<4;s++){
        ctx.fillStyle=COL[s];
        for(var i=0;i<n;i++){ if(st[i]!==s) continue;
          var dl=lon[i]+lam, cdl=Math.cos(dl), z=sp*sinLat[i]+cp*cosLat[i]*cdl; if(z<=0.02) continue;
          var x=cosLat[i]*Math.sin(dl), y=cp*sinLat[i]-sp*cosLat[i]*cdl, w=(s?ds*1.25:ds)*(0.55+0.45*z);
          ctx.globalAlpha=s?0.6+0.4*z:0.3+0.5*z; ctx.fillRect(size/2+r*x-w/2, size/2-r*y-w/2, w, w);
        }
      }
      ctx.globalAlpha=1;
      pairs.forEach(function(q,k){
        var a=live[q[0]], b=live[q[1]]; ctx.beginPath(); var pen=false;
        for(var j=0;j<=40;j++){ var g=slerp(a,b,j/40), pp=proj(g[0],g[1]), X=size/2+(pp[0]-size/2)*g[2], Y=size/2+(pp[1]-size/2)*g[2];
          if(pp[2]>0){ pen?ctx.lineTo(X,Y):ctx.moveTo(X,Y); pen=true; } else pen=false; }
        ctx.strokeStyle='rgba(94,200,255,.38)'; ctx.lineWidth=1.1; ctx.stroke();
        if(!reduce){ var g2=slerp(a,b,((t/7000)+k*0.23)%1), p2=proj(g2[0],g2[1]); if(p2[2]>0){ ctx.beginPath(); ctx.arc(size/2+(p2[0]-size/2)*g2[2], size/2+(p2[1]-size/2)*g2[2], 2.6,0,7); ctx.fillStyle='#5ec8ff'; ctx.fill(); } }
      });
    }
    resize(); render(0); box.classList.add('ready');
    addEventListener('resize',function(){ resize(); render(performance.now()); });
    var running=false, visible=true, last=0, drag=null;
    function frame(t){ if(!running) return; requestAnimationFrame(frame); if(t-last<33) return; var dt=last?Math.min(100,t-last):33; last=t; if(!drag) lam+=dt*0.00009; render(t); }
    function play(){ if(reduce||running||!visible||document.hidden) return; running=true; last=0; requestAnimationFrame(frame); }
    function pause(){ running=false; }
    new IntersectionObserver(function(es){ visible=es[0].isIntersecting; visible?play():pause(); }).observe(box);
    document.addEventListener('visibilitychange',function(){ document.hidden?pause():play(); });
    cv.addEventListener('pointerdown',function(e){ drag={x:e.clientX,y:e.clientY,l:lam,p:phi}; cv.setPointerCapture(e.pointerId); });
    cv.addEventListener('pointermove',function(e){ if(!drag) return; lam=drag.l+(e.clientX-drag.x)*0.006; phi=Math.max(-1.1,Math.min(1.1,drag.p+(e.clientY-drag.y)*0.006)); if(!running) render(performance.now()); });
    cv.addEventListener('pointerup',function(){ drag=null; }); cv.addEventListener('pointercancel',function(){ drag=null; });
    play();
  }
  function go(){ if('IntersectionObserver' in window){ var io=new IntersectionObserver(function(es){ if(es[0].isIntersecting){ io.disconnect(); (window.requestIdleCallback||setTimeout)(start,{timeout:2000}); } }); io.observe(box); } else start(); }
  if(document.readyState==='complete') go(); else addEventListener('load',go);
})();
