/* Full Duplex intro concepts D1-D3 (review: ?intro=d1|d2|d3). Canvas 2D only: no WebGL, no libraries, no audio.
   Every frame is drawn from the clock (render(t)), so it can be skipped or seeked at any point.
   Particles land on pixels sampled from the real logo A artwork, then the crisp SVG logo takes over. */
(function(){
  var INNER='<g fill="none" stroke-width="32" stroke-linecap="round"><path d="M279 505A233 233 0 0 1 644.3 313.2" stroke="#00cfff"/><path d="M744.9 511.9A233 233 0 0 1 383.7 699.5" stroke="#fff"/></g><circle cx="423" cy="432" r="10" fill="#00cfff"/><path transform="translate(426 517.5) rotate(-15)" fill="#00cfff" fill-rule="evenodd" d="M-23.5 -57.5h47a5 5 0 0 1 5 5v105a5 5 0 0 1 -5 5h-47a5 5 0 0 1 -5 -5v-105a5 5 0 0 1 5 -5zM-8.5 -48h17.0a5.5 5.5 0 0 1 5.5 5.5v0.0a5.5 5.5 0 0 1 -5.5 5.5h-17.0a5.5 5.5 0 0 1 -5.5 -5.5v-0.0a5.5 5.5 0 0 1 5.5 -5.5z"/><g fill="#fff"><path d="M583 488h21l33 32-22 22-32-32z"/><path d="M620 492l20-21 15 14-21 22z"/><path d="M567 545l21-21 14 14-20 20z"/><circle cx="635" cy="541" r="8"/></g>';
  var MARK='<svg xmlns="http://www.w3.org/2000/svg" viewBox="254 250 516 516">'+INNER+'</svg>';
  var CY='#00cfff', WH='#e8eef7', GR='#6ee79a';
  function rng(a){return function(){a=a+0x6D2B79F5|0;var t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296;};}
  function cl(x){return x<0?0:x>1?1:x;} function ph(t,a,d){return cl((t-a)/d);}
  function eio(x){return x<.5?4*x*x*x:1-Math.pow(-2*x+2,3)/2;} function eo(x){return 1-Math.pow(1-x,3);} function ei(x){return x*x*x;}
  function eback(x){var c=1.6;return 1+(c+1)*Math.pow(x-1,3)+c*Math.pow(x-1,2);}
  function lerp(a,b,u){return a+(b-a)*u;}
  var css='.fdi{position:fixed;inset:0;z-index:9999;overflow:hidden;color:#e8eef7;font-family:var(--f-head);-webkit-user-select:none;user-select:none}'+
    '.fdi-bg{position:absolute;inset:0;background:radial-gradient(120% 90% at 50% 30%,#0c1830 0,#05080f 62%)}'+
    '.fdi-s{position:absolute;inset:0;will-change:transform}.fdi canvas{position:absolute;inset:0;width:100%;height:100%}'+
    '.fdi-mark{position:absolute;opacity:0}.fdi-mark svg{display:block;width:100%;height:100%}'+
    '.fdi-word{position:absolute;left:0;right:0;text-align:center;font-weight:600;letter-spacing:-.02em;line-height:1.1;white-space:nowrap}.fdi-word i{display:inline-block;font-style:normal;opacity:0}.fdi-word i.c{color:#00cfff}'+
    '.fdi-kick{position:absolute;left:0;right:0;text-align:center;font:500 .78rem var(--f-mono);letter-spacing:.22em;text-transform:uppercase;color:#9fb0c3;opacity:0}'+
    '.fdi-type{position:absolute;left:4%;right:4%;text-align:center;font-weight:650;letter-spacing:-.035em;line-height:1.02;margin:0}.fdi-type>span{display:block;overflow:hidden;padding-bottom:.06em}.fdi-type>span>span{display:inline-block;transform:translateY(110%)}.fdi-type em{font-style:normal;color:#00cfff}'+
    '.fdi-hint{position:absolute;left:0;right:0;bottom:15%;text-align:center;font:500 .8rem var(--f-mono);letter-spacing:.16em;text-transform:uppercase;color:#9fb0c3;opacity:0}'+
    '.fdi-skip{position:absolute;right:18px;bottom:18px;z-index:2;font:500 .75rem var(--f-mono);letter-spacing:.1em;text-transform:uppercase;background:rgba(232,238,247,.07);color:#e8eef7;border:1px solid rgba(232,238,247,.28);border-radius:999px;padding:.6rem 1rem;cursor:pointer}.fdi-skip:hover,.fdi-skip:focus-visible{border-color:#00cfff;color:#00cfff}'+
    '.fdi-rev{position:absolute;left:18px;bottom:26px;z-index:2;margin:0;font:.7rem var(--f-mono);color:#9fb0c3}.fdi-rev a,.fdi-rev b{margin-left:.45rem;color:#00cfff}.fdi-rev b{color:#e8eef7}'+
    '.fdi-p{position:absolute;left:0;right:0;height:50.5%;background:#05080f}.fdi-p.t{top:0;background:linear-gradient(#05080f,#081226)}.fdi-p.b{bottom:0;background:linear-gradient(#081226,#05080f)}'+
    '.fdi-seam{position:absolute;left:0;right:0;top:50%;height:2px;margin-top:-1px;background:linear-gradient(90deg,transparent,#00cfff,transparent);opacity:0}'+
    '.fdi-c{position:absolute;inset:0}.fdi-cn{position:absolute;width:26px;height:26px;border:0 solid #00cfff;opacity:.85}'+
    '.fdi-cn.a{top:16px;left:16px;border-width:2px 0 0 2px}.fdi-cn.b{top:16px;right:16px;border-width:2px 2px 0 0}.fdi-cn.c{bottom:16px;left:16px;border-width:0 0 2px 2px}.fdi-cn.d{bottom:16px;right:16px;border-width:0 2px 2px 0}'+
    '.fdi-ht{position:absolute;font:500 .7rem var(--f-mono);letter-spacing:.16em;text-transform:uppercase;color:#9fb0c3}.fdi-ht.l{top:24px;left:52px}.fdi-ht.r{top:24px;right:52px;display:flex;gap:3px;align-items:flex-end}'+
    '.fdi-ht.r i{display:block;width:4px;background:#33415a;border-radius:1px}.fdi-ht.r i.on{background:#6ee79a}'+
    '.fdi-ct{position:absolute;left:0;right:0;bottom:17%;text-align:center;font:500 .9rem var(--f-mono);letter-spacing:.16em;white-space:nowrap}.fdi-ct b{font-weight:600;color:#00cfff}.fdi-ct.ok,.fdi-ct.ok b{color:#6ee79a}'+
    '.fdi-sub{position:absolute;left:0;right:0;bottom:calc(17% - 1.6rem);text-align:center;font:.7rem var(--f-mono);letter-spacing:.16em;color:#9fb0c3;text-transform:uppercase}'+
    '@media (max-width:700px){.fdi-ht.l{left:46px;top:22px;font-size:.6rem}.fdi-ht.r{right:46px;top:22px}.fdi-rev{bottom:24px}.fdi-kick{font-size:.66rem}.fdi-ct{font-size:.78rem}.fdi-sub{font-size:.6rem}}';

  window.FDIntro=function(v,o){
    o=o||{}; var END={d1:3.7,d2:3.9,d3:3.6}[v]; if(!END)return o.onDone&&o.onDone();
    if(!document.getElementById('fdi-css')){var st=document.createElement('style');st.id='fdi-css';st.textContent=css;document.head.appendChild(st);}
    var el=document.createElement('div'); el.className='fdi fdi-'+v; el.setAttribute('role','presentation');
    var rev=o.review?'<p class=fdi-rev>Review:'+['d1','d2','d3'].map(function(x){return x===v?'<b>'+x.toUpperCase()+'</b>':'<a href="?intro='+x+'">'+x.toUpperCase()+'</a>';}).join('')+'<a href="?intro='+v+'">↻ replay</a></p>':'';
    var mark='<div class=fdi-mark>'+MARK+'</div>';
    var word='<div class=fdi-word aria-hidden=true>'+'Full'.split('').map(function(c){return '<i>'+c+'</i>';}).join('')+'Duplex'.split('').map(function(c){return '<i class=c>'+c+'</i>';}).join('')+'</div>';
    var h='';
    if(v==='d1')h='<div class=fdi-bg></div><div class=fdi-s><canvas aria-hidden=true></canvas>'+mark+word+'<p class=fdi-kick>Satellite-to-phone, explained</p></div>';
    if(v==='d2')h='<div class=fdi-bg></div><div class=fdi-s><canvas aria-hidden=true></canvas>'+mark+'<p class=fdi-type><span><span>Your phone is</span></span><span><span>about to talk</span></span><span><span>to <em>space.</em></span></span></p><p class=fdi-hint>'+(matchMedia('(hover:hover)').matches?'Move your cursor · steer the signal':'Touch the sky · steer the signal')+'</p></div>';
    if(v==='d3')h='<div class="fdi-p t"></div><div class="fdi-p b"></div><div class=fdi-seam></div><div class=fdi-c><canvas aria-hidden=true></canvas>'+mark+
      '<span class="fdi-cn a"></span><span class="fdi-cn b"></span><span class="fdi-cn c"></span><span class="fdi-cn d"></span><span class="fdi-ht l">Full Duplex · D2D link</span><span class="fdi-ht r"><i style="height:4px"></i><i style="height:7px"></i><i style="height:10px"></i><i style="height:13px"></i></span>'+
      '<p class=fdi-ct></p><p class=fdi-sub>Low Earth orbit · direct to cell</p></div>';
    el.innerHTML=h+'<button type=button class=fdi-skip>Skip intro</button>'+rev;
    document.body.appendChild(el);
    var cv=el.querySelector('canvas'), ctx=cv.getContext&&cv.getContext('2d'), M=el.querySelector('.fdi-mark'), stage=el.querySelector('.fdi-s')||el.querySelector('.fdi-c');
    var main=document.querySelector('main')||document.getElementById('main'), done=false, raf=0, t0=0, seeking=false;
    function finish(fast){
      if(done)return; done=true; cancelAnimationFrame(raf); document.removeEventListener('keydown',key);
      if(main){main.style.transform='';main.style.opacity='';main.style.transformOrigin='';}
      if(fast){el.style.transition='opacity .22s';el.style.opacity='0';setTimeout(function(){el.remove();},240);} else el.remove();
      if(o.onDone)o.onDone();
    }
    function key(ev){if(ev.key==='Escape')finish(true);}
    document.addEventListener('keydown',key);
    el.addEventListener('click',function(ev){if(!(ev.target.closest&&ev.target.closest('.fdi-rev')))finish(true);});
    if(!ctx||document.hidden)return finish();
    var W=innerWidth,H=innerHeight,mob=W<700,dpr=Math.min(devicePixelRatio||1,mob?1.5:2);
    cv.width=Math.round(W*dpr);cv.height=Math.round(H*dpr);ctx.setTransform(dpr,0,0,dpr,0,0);
    var S=Math.round(Math.min(W*(mob?.52:.4),H*.34,320)), cx=W/2, cy=H*(v==='d2'?.46:.42), lx=cx-S/2, ly=cy-S/2;
    M.style.cssText='left:'+lx+'px;top:'+ly+'px;width:'+S+'px;height:'+S+'px';
    var wd=el.querySelector('.fdi-word'), kk=el.querySelector('.fdi-kick'), ty=el.querySelector('.fdi-type'), hint=el.querySelector('.fdi-hint');
    if(wd){wd.style.top=(ly+S*1.02)+'px';wd.style.fontSize=Math.round(S*.2)+'px';kk.style.top=(ly+S*1.02+S*.27)+'px';}
    if(ty){ty.style.fontSize=(mob?Math.min(44,W*.11):Math.min(76,W*.055))+'px';ty.style.top=(H*.5)+'px';}
    var R=rng(20261113), P=[], A=[], ptr={x:-1,y:-1,on:false,sx:0,sy:0};
    for(var i=0;i<(mob?70:150);i++)A.push({x:R()*W,y:R()*H,s:R()*1.3+.4,p:R()*6.3});
    el.addEventListener('pointermove',function(e){ptr.x=e.clientX;ptr.y=e.clientY;if(!ptr.on){ptr.on=true;ptr.sx=ptr.x;ptr.sy=ptr.y;}});
    el.addEventListener('touchmove',function(e){var q=e.touches[0];if(q){ptr.x=q.clientX;ptr.y=q.clientY;ptr.on=true;}},{passive:true});

    /* sample the logo artwork into particle targets */
    var img=new Image();
    img.onload=function(){
      var oc=document.createElement('canvas'); oc.width=oc.height=S; var ox=oc.getContext('2d'); ox.drawImage(img,0,0,S,S);
      var d=ox.getImageData(0,0,S,S).data, g=Math.max(3,Math.round(S/(mob?50:64)));
      for(var y=0;y<S;y+=g)for(var x=0;x<S;x+=g){var k=(y*S+x)*4;if(d[k+3]>140){
        var jx=x+(R()-.5)*g*.6, jy=y+(R()-.5)*g*.6, ring=Math.floor(R()*4);
        P.push({tx:lx+jx,ty:ly+jy,c:d[k]<120?0:1,a:R(),b:R(),q:R()*6.283,ring:ring,rr:.92+R()*.16,sx:R()*W,sy:R()*H,rank:R()});}}
      prep(); el.classList.add('go'); t0=performance.now(); if(!seeking)loop();
    };
    img.onerror=function(){finish();};
    img.src='data:image/svg+xml;charset=utf-8,'+encodeURIComponent(MARK);

    var RINGS=[{R:1.0,a:.36,r:-.42,w:.62},{R:1.32,a:.5,r:.28,w:.48},{R:1.68,a:.3,r:-.12,w:.38},{R:2.1,a:.58,r:.55,w:.3}], LT=[];
    /* D3: the progress curve (stutters like a real lock), when each dot lights, and a few constellation links */
    var KF=[[0,0],[.25,.1],[.5,.16],[.85,.44],[1.1,.5],[1.5,.79],[1.8,.86],[2.1,.96],[2.35,1]];
    function prog(t){t-=.1;if(t<=0)return 0;for(var i=1;i<KF.length;i++)if(t<=KF[i][0]){var a=KF[i-1],b=KF[i],u=(t-a[0])/(b[0]-a[0]);return lerp(a[1],b[1],u*u*(3-2*u));}return 1;}
    function prep(){
      P.sort(function(a,b){return a.rank-b.rank;});
      if(v==='d3'){var j=0;for(var t=0;t<=2.6;t+=.01){while(j<P.length&&P[j].rank*.985<=prog(t)){P[j].lt=t;j++;}}for(;j<P.length;j++)P[j].lt=2.45;
        for(var i=6;i<P.length;i+=5){var best=-1,bd=1e9;for(var k=Math.max(0,i-60);k<i;k++){var dx=P[k].tx-P[i].tx,dy=P[k].ty-P[i].ty,dd=dx*dx+dy*dy;if(dd<bd&&dd>(S*.03)*(S*.03)){bd=dd;best=k;}}if(best>=0&&bd<(S*.2)*(S*.2))LT.push([best,i]);}}
      if(v==='d1')P.forEach(function(p){p.st=1.1+.55*((Math.atan2(p.ty-cy,p.tx-cx)+Math.PI)/6.283);});
      if(v==='d2')P.forEach(function(p){var dx=p.sx-p.tx,dy=p.sy-p.ty;p.st=1.5+.3*cl(Math.sqrt(dx*dx+dy*dy)/W)+p.a*.1;});
    }
    function stars(t,al){ctx.fillStyle=WH;for(var i=0;i<A.length;i++){var s=A[i];ctx.globalAlpha=al*(.25+.3*(1+Math.sin(t*2.2+s.p)));ctx.fillRect(s.x,s.y,s.s,s.s);}}
    function dots(list){for(var c=0;c<2;c++){ctx.fillStyle=c?WH:CY;for(var i=0;i<list.length;i++){var q=list[i];if(q[3]!==c||q[4]<=.01)continue;ctx.globalAlpha=q[4];ctx.fillRect(q[0]-q[2]/2,q[1]-q[2]/2,q[2],q[2]);}}ctx.globalAlpha=1;}
    function orbit(p,t){
      var g=RINGS[p.ring], th=p.q+g.w*t*1.25, rad=g.R*p.rr*S*.62, x=Math.cos(th)*rad, z=Math.sin(th)*rad, y=-z*Math.sin(g.a), zz=z*Math.cos(g.a);
      var x2=x*Math.cos(g.r)-y*Math.sin(g.r), y2=x*Math.sin(g.r)+y*Math.cos(g.r), pp=900/(900+zz);
      return [cx+x2*pp, cy+y2*pp, pp];
    }
    function sat(x,y,al,sc){ctx.save();ctx.globalAlpha=al;ctx.translate(x,y);ctx.rotate(-.2);ctx.scale(sc,sc);ctx.fillStyle='#1d3a66';ctx.strokeStyle='#5ec8ff';ctx.lineWidth=1;
      ctx.fillRect(-26,-5,17,10);ctx.strokeRect(-26,-5,17,10);ctx.fillRect(9,-5,17,10);ctx.strokeRect(9,-5,17,10);ctx.fillStyle=WH;ctx.fillRect(-7,-7,14,14);ctx.fillStyle=CY;ctx.beginPath();ctx.arc(0,0,2.6,0,6.283);ctx.fill();ctx.restore();}
    function ghost(t){return [W*(.5+.3*Math.sin(t*1.25-1.2)), H*(.68+.1*Math.sin(t*2.1+.4))];}

    function render(t){
      ctx.clearRect(0,0,W,H); var L=[], i, p, u, e;
      if(v==='d1'){
        var zf=ph(t,2.95,.7), z=ei(zf), fade=1-ph(t,3.25,.42);
        stars(t,1-zf);
        var Re=Math.max(W,H)*.95, ex=W/2, ey=H+Re*.8;
        ctx.globalAlpha=(1-zf)*ph(t,0,.5); var gr=ctx.createRadialGradient(ex,ey-Re*.2,Re*.5,ex,ey,Re);gr.addColorStop(0,'#0b1a36');gr.addColorStop(1,'#050a16');
        ctx.fillStyle=gr;ctx.beginPath();ctx.arc(ex,ey,Re,0,6.283);ctx.fill();
        ctx.strokeStyle=CY;ctx.lineWidth=2;ctx.shadowColor=CY;ctx.shadowBlur=24;ctx.globalAlpha=(1-zf)*.65*ph(t,.1,.6);ctx.beginPath();ctx.arc(ex,ey,Re,Math.PI*1.12,Math.PI*1.88);ctx.stroke();ctx.shadowBlur=0;
        var la=1-ph(t,2.55,.3), oa=(1-ph(t,1.4,.8))*ph(t,.1,.6)*.22;
        if(oa>0){ctx.strokeStyle=CY;ctx.lineWidth=1;for(i=0;i<RINGS.length;i++){var gg=RINGS[i];ctx.globalAlpha=oa;ctx.beginPath();ctx.ellipse(cx,cy,gg.R*S*.62,gg.R*S*.62*Math.sin(gg.a),gg.r,0,6.283);ctx.stroke();}}
        for(i=0;i<P.length;i++){p=P[i];var ob=orbit(p,t);u=eio(ph(t,p.st,.95));
          var sz=lerp(Math.max(1,1.2+(ob[2]-.75)*5),Math.max(1.6,S/120),u), al=lerp(.3+.7*cl((ob[2]-.7)*1.6),.95,u)*la*ph(t,p.a*.4,.4);
          L.push([lerp(ob[0],p.tx,u),lerp(ob[1],p.ty,u),sz,u>.5?p.c:(p.ring%2?1:0),al]);}
        ctx.globalCompositeOperation='lighter';dots(L);ctx.globalCompositeOperation='source-over';
        M.style.opacity=ph(t,2.4,.3);
        var ls=wd.children;for(i=0;i<ls.length;i++){e=eo(ph(t,2.4+i*.04,.4));ls[i].style.opacity=e;ls[i].style.transform='translateY('+((1-e)*40)+'%)';}
        kk.style.opacity=ph(t,2.75,.3);
        stage.style.transformOrigin=cx+'px '+(cy+S*.02)+'px'; stage.style.transform='scale('+(1+z*11)+')'; el.style.opacity=fade;
        el.querySelector('.fdi-bg').style.opacity=1-ph(t,3.1,.45);
        if(main){main.style.transformOrigin='50% '+(cy+scrollY)+'px';main.style.transform=zf>0?'scale('+(1.14-.14*eo(ph(t,3.0,.7)))+')':'';main.style.opacity=zf>0?.25+.75*ph(t,3.05,.6):'';}
      }
      if(v==='d2'){
        var pt; if(ptr.on&&!seeking){ptr.sx+=(ptr.x-ptr.sx)*.18;ptr.sy+=(ptr.y-ptr.sy)*.18;pt=[ptr.sx,ptr.sy];} else pt=ghost(t);
        var sn=ph(t,1.5,.8), satA=(1-ph(t,1.9,.4))*ph(t,.05,.3);
        stars(t,1-ph(t,2.4,.5));
        var sx=W*(.12+.76*cl(t/2.6)), sy=H*.17+Math.sin(t*1.4)*12;
        if(satA>0){
          var dx=sx-pt[0],dy=sy-pt[1],dist=Math.sqrt(dx*dx+dy*dy), bars=Math.max(1,Math.min(4,4-Math.floor(dist/(Math.max(W,H)*.22))));
          ctx.globalAlpha=satA*.75;ctx.strokeStyle=CY;ctx.lineWidth=1.4;ctx.setLineDash([5,7]);ctx.lineDashOffset=-t*70;ctx.beginPath();ctx.moveTo(pt[0],pt[1]);ctx.lineTo(sx,sy);ctx.stroke();ctx.setLineDash([]);
          for(i=0;i<3;i++){var f=(t*.9+i/3)%1;ctx.globalAlpha=satA*(1-Math.abs(f-.5)*1.4);ctx.fillStyle=i%2?GR:CY;ctx.beginPath();ctx.arc(lerp(pt[0],sx,i%2?1-f:f),lerp(pt[1],sy,i%2?1-f:f),2.6,0,6.283);ctx.fill();}
          sat(sx,sy,satA,mob?1:1.45);
          ctx.globalAlpha=satA;ctx.strokeStyle=CY;ctx.lineWidth=1.5;ctx.beginPath();ctx.arc(pt[0],pt[1],15,0,6.283);ctx.stroke();ctx.fillStyle=CY;ctx.beginPath();ctx.arc(pt[0],pt[1],2.5,0,6.283);ctx.fill();
          for(i=0;i<4;i++){ctx.fillStyle=i<bars?GR:'#33415a';ctx.fillRect(pt[0]+22+i*5,pt[1]+6-(i*3+3),3.4,i*3+3);}
        }
        var la2=1-ph(t,2.2,.3);
        for(i=0;i<P.length;i++){p=P[i];
          var fx=p.sx+Math.sin(t*.8+p.q)*14, fy=p.sy+Math.cos(t*.7+p.q*1.3)*11, ddx=fx-pt[0], ddy=fy-pt[1], dd=Math.sqrt(ddx*ddx+ddy*ddy)+.01, rep=(1-sn)*70*Math.exp(-dd*dd/(2*90*90));
          fx+=ddx/dd*rep; fy+=ddy/dd*rep; u=ph(t,p.st,.6); e=eback(u);
          L.push([lerp(fx,p.tx,e),lerp(fy,p.ty,e),lerp(1.4+p.b*2,Math.max(1.6,S/120),u),u>.3?p.c:(p.a<.2?0:1),lerp(.45+.5*p.b,.95,u)*la2*ph(t,p.a*.3,.3)]);}
        dots(L);
        var mv=eio(ph(t,2.25,.45)); M.style.opacity=ph(t,2.05,.25);
        M.style.transform='translateY('+(-mv*(H*.46-S*.55-(mob?50:30)))+'px) scale('+(1-.45*mv)+')';
        var ls2=ty.children;for(i=0;i<ls2.length;i++){e=eo(ph(t,2.4+i*.13,.5));ls2[i].firstChild.style.transform='translateY('+((1-e)*110)+'%)';}
        ty.style.opacity=ph(t,2.38,.05);
        hint.style.opacity=ph(t,.25,.3)*(1-ph(t,1.35,.3));
        var cu=eio(ph(t,3.3,.6)); el.style.transform=cu?'translateY('+(-cu*100)+'%)':'';
        if(main){main.style.transform=cu?'translateY('+((1-cu)*6)+'vh)':'';main.style.opacity=cu?.4+.6*cu:'';}
      }
      if(v==='d3'){
        var pr=prog(t), lk=ph(t,2.45,.25), wp=eio(ph(t,2.95,.6)), cf=1-ph(t,2.95,.15);
        ctx.globalAlpha=.5*(1-lk);ctx.strokeStyle=CY;ctx.lineWidth=1;ctx.setLineDash([3,9]);ctx.beginPath();ctx.arc(cx,cy,S*.68,0,6.283);ctx.stroke();ctx.setLineDash([]);
        var sw=t*2.6; ctx.globalAlpha=.55*(1-lk);ctx.lineWidth=2;ctx.beginPath();ctx.arc(cx,cy,S*.68,sw,sw+.7);ctx.stroke();
        stars(t,.8);
        ctx.strokeStyle=CY;ctx.lineWidth=1;
        for(i=0;i<LT.length;i++){var a=P[LT[i][0]],b=P[LT[i][1]];if(t<b.lt)continue;ctx.globalAlpha=.32*ph(t,b.lt,.2)*(1-ph(t,2.5,.3));ctx.beginPath();ctx.moveTo(a.tx,a.ty);ctx.lineTo(b.tx,b.ty);ctx.stroke();}
        var la3=1-ph(t,2.6,.25), base=Math.max(1.6,S/120);
        for(i=0;i<P.length;i++){p=P[i];if(t<p.lt)continue;var ag=t-p.lt, pop=ag<.25?1+2.2*Math.sin(ag/.25*Math.PI):1;
          L.push([p.tx,p.ty,base*pop,ag<.12?1:p.c,(ag<.25?1:.92)*la3]);}
        dots(L);
        if(lk>0&&lk<1||t>2.45&&t<2.9){var gk=ph(t,2.45,.45);ctx.globalAlpha=(1-gk)*.8;ctx.strokeStyle=GR;ctx.lineWidth=2;ctx.beginPath();ctx.arc(cx,cy,S*(.5+gk*.5),0,6.283);ctx.stroke();}
        ctx.globalAlpha=1; M.style.opacity=lk;
        var ct=el.querySelector('.fdi-ct'), n=Math.round(pr*100), txt=n<100?'[ ACQUIRING SIGNAL <b>'+('00'+n).slice(-3)+'%</b> ]':'[ SIGNAL LOCKED <b>100%</b> · WELCOME TO FULL DUPLEX ]';
        if(mob&&n>=100)txt='[ LOCKED <b>100%</b> · WELCOME ]';
        if(ct.innerHTML!==txt){ct.innerHTML=txt;ct.className='fdi-ct'+(n>=100?' ok':'');}
        var bs=el.querySelectorAll('.fdi-ht.r i');for(i=0;i<4;i++)bs[i].className=pr>=(i+1)*.25-.001?'on':'';
        stage.style.opacity=cf;
        el.querySelector('.fdi-p.t').style.transform='translateY('+(-wp*100)+'%)'; el.querySelector('.fdi-p.b').style.transform='translateY('+(wp*100)+'%)';
        el.querySelector('.fdi-seam').style.opacity=ph(t,2.9,.1)*(1-ph(t,3.15,.3));
        if(main){main.style.transform=wp?'scale('+(1.05-.05*wp)+')':'';main.style.transformOrigin='50% '+(H/2+scrollY)+'px';}
      }
    }
    function loop(){raf=requestAnimationFrame(function(){if(done||seeking)return;var t=(performance.now()-t0)/1000;if(t>=END){render(END);return finish();}render(t);loop();});}
    window.FDI={end:END,seek:function(t){seeking=true;cancelAnimationFrame(raf);if(P.length)render(t);return P.length;},count:function(){return P.length;}};
  };
})();
