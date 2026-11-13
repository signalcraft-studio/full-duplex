/* First-visit intro (concept D1, "zoom-through"): satellite dots orbit above the Earth's edge, converge into logo A,
   then the view flies through the logo into the page. Canvas 2D only: no WebGL, no libraries, no audio.
   Loaded by assets/site.js once per browser; skip with the button, Esc or a click. Every frame is drawn from the clock. */
(function(){
  var INNER='<g fill="none" stroke-width="32" stroke-linecap="round"><path d="M279 505A233 233 0 0 1 644.3 313.2" stroke="#00cfff"/><path d="M744.9 511.9A233 233 0 0 1 383.7 699.5" stroke="#fff"/></g><circle cx="423" cy="432" r="10" fill="#00cfff"/><path transform="translate(426 517.5) rotate(-15)" fill="#00cfff" fill-rule="evenodd" d="M-23.5 -57.5h47a5 5 0 0 1 5 5v105a5 5 0 0 1 -5 5h-47a5 5 0 0 1 -5 -5v-105a5 5 0 0 1 5 -5zM-8.5 -48h17.0a5.5 5.5 0 0 1 5.5 5.5v0.0a5.5 5.5 0 0 1 -5.5 5.5h-17.0a5.5 5.5 0 0 1 -5.5 -5.5v-0.0a5.5 5.5 0 0 1 5.5 -5.5z"/><g fill="#fff"><path d="M583 488h21l33 32-22 22-32-32z"/><path d="M620 492l20-21 15 14-21 22z"/><path d="M567 545l21-21 14 14-20 20z"/><circle cx="635" cy="541" r="8"/></g>';
  var MARK='<svg xmlns="http://www.w3.org/2000/svg" viewBox="254 250 516 516">'+INNER+'</svg>', CY='#00cfff', WH='#e8eef7', END=3.7;
  function rng(a){return function(){a=a+0x6D2B79F5|0;var t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296;};}
  function cl(x){return x<0?0:x>1?1:x;} function ph(t,a,d){return cl((t-a)/d);}
  function eio(x){return x<.5?4*x*x*x:1-Math.pow(-2*x+2,3)/2;} function eo(x){return 1-Math.pow(1-x,3);} function ei(x){return x*x*x;}
  function lerp(a,b,u){return a+(b-a)*u;}
  var css='.fdi{position:fixed;inset:0;z-index:9999;overflow:hidden;color:#e8eef7;font-family:var(--f-head);-webkit-user-select:none;user-select:none}'+
    '.fdi-bg{position:absolute;inset:0;background:radial-gradient(120% 90% at 50% 30%,#0c1830 0,#05080f 62%)}'+
    '.fdi-s{position:absolute;inset:0;will-change:transform}.fdi canvas{position:absolute;inset:0;width:100%;height:100%}'+
    '.fdi-mark{position:absolute;opacity:0}.fdi-mark svg{display:block;width:100%;height:100%}'+
    '.fdi-word{position:absolute;left:0;right:0;text-align:center;font-weight:600;letter-spacing:-.02em;line-height:1.1;white-space:nowrap}.fdi-word i{display:inline-block;font-style:normal;opacity:0}.fdi-word i.c{color:#00cfff}'+
    '.fdi-kick{position:absolute;left:0;right:0;text-align:center;font:500 .78rem var(--f-mono);letter-spacing:.22em;text-transform:uppercase;color:#9fb0c3;opacity:0}'+
    '.fdi-skip{position:absolute;right:18px;bottom:18px;z-index:2;font:500 .75rem var(--f-mono);letter-spacing:.1em;text-transform:uppercase;background:rgba(232,238,247,.07);color:#e8eef7;border:1px solid rgba(232,238,247,.28);border-radius:999px;padding:.6rem 1rem;cursor:pointer}.fdi-skip:hover,.fdi-skip:focus-visible{border-color:#00cfff;color:#00cfff}'+
    '@media (max-width:700px){.fdi-kick{font-size:.66rem}}';

  window.FDIntro=function(o){
    o=o||{};
    var st=document.createElement('style');st.textContent=css;document.head.appendChild(st);
    var el=document.createElement('div'); el.className='fdi'; el.setAttribute('role','presentation');
    el.innerHTML='<div class=fdi-bg></div><div class=fdi-s><canvas aria-hidden=true></canvas><div class=fdi-mark>'+MARK+'</div><div class=fdi-word aria-hidden=true>'+
      'Full'.split('').map(function(c){return '<i>'+c+'</i>';}).join('')+'Duplex'.split('').map(function(c){return '<i class=c>'+c+'</i>';}).join('')+
      '</div><p class=fdi-kick>Satellite-to-phone, explained</p></div><button type=button class=fdi-skip>Skip intro</button>';
    document.body.appendChild(el);
    var cv=el.querySelector('canvas'), ctx=cv.getContext&&cv.getContext('2d'), M=el.querySelector('.fdi-mark'), stage=el.querySelector('.fdi-s'), bg=el.querySelector('.fdi-bg');
    var main=document.querySelector('main')||document.getElementById('main'), done=false, raf=0, t0=0, seeking=false;
    function finish(fast){
      if(done)return; done=true; cancelAnimationFrame(raf); document.removeEventListener('keydown',key);
      if(main){main.style.transform='';main.style.opacity='';main.style.transformOrigin='';}
      if(fast){el.style.transition='opacity .22s';el.style.opacity='0';setTimeout(function(){el.remove();},240);} else el.remove();
      if(o.onDone)o.onDone();
    }
    function key(ev){if(ev.key==='Escape')finish(true);}
    document.addEventListener('keydown',key);
    el.addEventListener('click',function(){finish(true);});
    if(!ctx||document.hidden)return finish();
    var W=innerWidth,H=innerHeight,mob=W<700,dpr=Math.min(devicePixelRatio||1,mob?1.5:2);
    cv.width=Math.round(W*dpr);cv.height=Math.round(H*dpr);ctx.setTransform(dpr,0,0,dpr,0,0);
    var S=Math.round(Math.min(W*(mob?.52:.4),H*.34,320)), cx=W/2, cy=H*.42, lx=cx-S/2, ly=cy-S/2;
    M.style.cssText='left:'+lx+'px;top:'+ly+'px;width:'+S+'px;height:'+S+'px';
    var wd=el.querySelector('.fdi-word'), kk=el.querySelector('.fdi-kick');
    wd.style.top=(ly+S*1.02)+'px';wd.style.fontSize=Math.round(S*.2)+'px';kk.style.top=(ly+S*1.02+S*.27)+'px';
    var R=rng(20261113), P=[], A=[], i;
    for(i=0;i<(mob?70:150);i++)A.push({x:R()*W,y:R()*H,s:R()*1.3+.4,p:R()*6.3});
    var RINGS=[{R:1.0,a:.36,r:-.42,w:.62},{R:1.32,a:.5,r:.28,w:.48},{R:1.68,a:.3,r:-.12,w:.38},{R:2.1,a:.58,r:.55,w:.3}];
    /* sample the real logo artwork into particle targets */
    var img=new Image();
    img.onload=function(){
      var oc=document.createElement('canvas'); oc.width=oc.height=S; var ox=oc.getContext('2d'); ox.drawImage(img,0,0,S,S);
      var d=ox.getImageData(0,0,S,S).data, g=Math.max(3,Math.round(S/(mob?50:64)));
      for(var y=0;y<S;y+=g)for(var x=0;x<S;x+=g){var k=(y*S+x)*4;if(d[k+3]>140){
        var jx=x+(R()-.5)*g*.6, jy=y+(R()-.5)*g*.6, tx=lx+jx, ty=ly+jy;
        P.push({tx:tx,ty:ty,c:d[k]<120?0:1,a:R(),q:R()*6.283,ring:Math.floor(R()*4),rr:.92+R()*.16,st:1.1+.55*((Math.atan2(ty-cy,tx-cx)+Math.PI)/6.283)});}}
      t0=performance.now(); if(!seeking)loop();
    };
    img.onerror=function(){finish();};
    img.src='data:image/svg+xml;charset=utf-8,'+encodeURIComponent(MARK);
    function orbit(p,t){
      var g=RINGS[p.ring], th=p.q+g.w*t*1.25, rad=g.R*p.rr*S*.62, x=Math.cos(th)*rad, z=Math.sin(th)*rad, y=-z*Math.sin(g.a), zz=z*Math.cos(g.a);
      var x2=x*Math.cos(g.r)-y*Math.sin(g.r), y2=x*Math.sin(g.r)+y*Math.cos(g.r), pp=900/(900+zz);
      return [cx+x2*pp, cy+y2*pp, pp];
    }
    function render(t){
      ctx.clearRect(0,0,W,H); var p,u,e,c,q;
      var zf=ph(t,2.95,.7), z=ei(zf), fade=1-ph(t,3.25,.42);
      ctx.fillStyle=WH;for(i=0;i<A.length;i++){q=A[i];ctx.globalAlpha=(1-zf)*(.25+.3*(1+Math.sin(t*2.2+q.p)));ctx.fillRect(q.x,q.y,q.s,q.s);}
      var Re=Math.max(W,H)*.95, ex=W/2, ey=H+Re*.8;
      ctx.globalAlpha=(1-zf)*ph(t,0,.5); var gr=ctx.createRadialGradient(ex,ey-Re*.2,Re*.5,ex,ey,Re);gr.addColorStop(0,'#0b1a36');gr.addColorStop(1,'#050a16');
      ctx.fillStyle=gr;ctx.beginPath();ctx.arc(ex,ey,Re,0,6.283);ctx.fill();
      ctx.strokeStyle=CY;ctx.lineWidth=2;ctx.shadowColor=CY;ctx.shadowBlur=24;ctx.globalAlpha=(1-zf)*.65*ph(t,.1,.6);ctx.beginPath();ctx.arc(ex,ey,Re,Math.PI*1.12,Math.PI*1.88);ctx.stroke();ctx.shadowBlur=0;
      var la=1-ph(t,2.55,.3), oa=(1-ph(t,1.4,.8))*ph(t,.1,.6)*.22;
      if(oa>0){ctx.lineWidth=1;for(i=0;i<RINGS.length;i++){var gg=RINGS[i];ctx.globalAlpha=oa;ctx.beginPath();ctx.ellipse(cx,cy,gg.R*S*.62,gg.R*S*.62*Math.sin(gg.a),gg.r,0,6.283);ctx.stroke();}}
      ctx.globalCompositeOperation='lighter';
      for(c=0;c<2;c++){ctx.fillStyle=c?WH:CY;for(i=0;i<P.length;i++){p=P[i];var ob=orbit(p,t);u=eio(ph(t,p.st,.95));
        if((u>.5?p.c:p.ring%2)!==c)continue;
        var sz=lerp(Math.max(1,1.2+(ob[2]-.75)*5),Math.max(1.6,S/120),u), al=lerp(.3+.7*cl((ob[2]-.7)*1.6),.95,u)*la*ph(t,p.a*.4,.4);
        if(al<=.01)continue; ctx.globalAlpha=al; ctx.fillRect(lerp(ob[0],p.tx,u)-sz/2,lerp(ob[1],p.ty,u)-sz/2,sz,sz);}}
      ctx.globalCompositeOperation='source-over';ctx.globalAlpha=1;
      M.style.opacity=ph(t,2.4,.3);
      var ls=wd.children;for(i=0;i<ls.length;i++){e=eo(ph(t,2.4+i*.04,.4));ls[i].style.opacity=e;ls[i].style.transform='translateY('+((1-e)*40)+'%)';}
      kk.style.opacity=ph(t,2.75,.3);
      stage.style.transformOrigin=cx+'px '+(cy+S*.02)+'px'; stage.style.transform='scale('+(1+z*11)+')'; el.style.opacity=fade; bg.style.opacity=1-ph(t,3.1,.45);
      if(main){main.style.transformOrigin='50% '+(cy+scrollY)+'px';main.style.transform=zf>0?'scale('+(1.14-.14*eo(ph(t,3.0,.7)))+')':'';main.style.opacity=zf>0?.25+.75*ph(t,3.05,.6):'';}
    }
    function loop(){raf=requestAnimationFrame(function(){if(done||seeking)return;var t=(performance.now()-t0)/1000;if(t>=END){render(END);return finish();}render(t);loop();});}
    window.FDI={end:END,seek:function(t){seeking=true;cancelAnimationFrame(raf);if(P.length)render(t);return P.length;},count:function(){return P.length;}};
  };
})();
