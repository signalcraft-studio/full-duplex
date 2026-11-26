/* Full Duplex home, variant C "Signal story": a scroll-driven narrative with one sticky canvas graphic.
   Scenes: phone -> mast -> satellite -> race chart (with a rewind scrubber over sourced milestones) -> leaderboard -> today's totals.
   Every number comes from the page's data-story attribute (race.json, milestones.json, constellations.json, tracker). No libraries.
   Scroll drives the scenes; with prefers-reduced-motion the small ambient pulses stop and scenes switch without easing. */
(function(){
  var sec=document.querySelector('section.story'); if(!sec) return;
  var fig=sec.querySelector('.st-fig'), cv=fig.querySelector('canvas'), ctx=cv.getContext&&cv.getContext('2d'); if(!ctx) return;
  var D; try{D=JSON.parse(sec.getAttribute('data-story'));}catch(e){return;}
  var RM=matchMedia('(prefers-reduced-motion: reduce)').matches, step=/[?&]step\b/.test(location.search);
  sec.classList.add('js');
  var steps=[].slice.call(sec.querySelectorAll('.st-step')), rw=fig.querySelector('.st-rw'), range=document.getElementById('st-range'), msEl=document.getElementById('st-ms');
  var W=0,H=0,DPR=1,t=0,last=0,running=false,cur={k:'phone',p:0},prev=null,fadeT=0,override=null,lastP=-1;
  var MON=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  var ms=function(s){return Date.parse(s+'T00:00:00Z');};
  var F=D.f.map(function(f){return {t:ms(f[0]),v:f[1]};}), MS=D.ms.map(function(m){return {t:ms(m[0]),d:m[0],x:m[1],u:m[2],l:m[3]};});
  var T0=Math.min(MS.length?MS[0].t:F[0].t, F[0].t), T0y=new Date(T0).getUTCFullYear(); T0=Date.UTC(T0y,0,1); var T1=F[F.length-1].t;
  var ease=function(x){x=Math.max(0,Math.min(1,x)); return RM?(x>0?1:0):x<.5?2*x*x:1-Math.pow(-2*x+2,2)/2;};
  var cl=function(x){return Math.max(0,Math.min(1,x));};
  function size(){var r=cv.getBoundingClientRect(); W=r.width; H=r.height; DPR=Math.min(2,devicePixelRatio||1); cv.width=Math.round(W*DPR); cv.height=Math.round(H*DPR);}
  function fmt(d,day){var x=new Date(d); return (day?x.getUTCDate()+' ':'')+MON[x.getUTCMonth()]+' '+x.getUTCFullYear();}
  var narrow=function(){return W<700;};
  function ground(){return H*(narrow()?.56:.8);}
  function phonePos(){return {x:W*(narrow()?.3:.32), y:ground()};}
  function drawGround(a){ctx.globalAlpha=a; var g=ctx.createLinearGradient(0,ground(),0,H); g.addColorStop(0,'rgba(47,224,200,.10)'); g.addColorStop(1,'rgba(47,224,200,0)'); ctx.fillStyle=g; ctx.fillRect(0,ground(),W,H-ground());
    ctx.strokeStyle='rgba(143,219,255,.35)'; ctx.lineWidth=1; ctx.beginPath(); ctx.moveTo(0,ground()); ctx.lineTo(W,ground()); ctx.stroke();}
  function phone(x,y,s,a,lit){var w=s*.5,h=s; ctx.globalAlpha=a; ctx.fillStyle='#0d1730'; ctx.strokeStyle='#cfe3ff'; ctx.lineWidth=2;
    ctx.beginPath(); if(ctx.roundRect) ctx.roundRect(x-w/2,y-h,w,h,s*.08); else ctx.rect(x-w/2,y-h,w,h); ctx.fill(); ctx.stroke();
    var g=ctx.createLinearGradient(x,y-h,x,y); g.addColorStop(0,lit||'#5ec8ff'); g.addColorStop(1,'#9b7bff'); ctx.fillStyle=g; ctx.globalAlpha=a*.85; ctx.fillRect(x-w/2+4,y-h+10,w-8,h-20);}
  function ripples(x,y,dir,col,a){if(RM){ctx.globalAlpha=a*.5; ctx.strokeStyle=col; ctx.beginPath(); ctx.arc(x,y,30,dir-0.7,dir+0.7); ctx.stroke(); return;}
    for(var i=0;i<3;i++){var r=((t/1400+i/3)%1); ctx.globalAlpha=a*(1-r); ctx.strokeStyle=col; ctx.lineWidth=2; ctx.beginPath(); ctx.arc(x,y,10+r*90,dir-0.7,dir+0.7); ctx.stroke();}}
  function tower(x,y,s,a){ctx.globalAlpha=a; ctx.strokeStyle='#8fa6c2'; ctx.lineWidth=2; ctx.beginPath(); ctx.moveTo(x-s*.18,y); ctx.lineTo(x,y-s); ctx.lineTo(x+s*.18,y);
    for(var i=1;i<5;i++){var yy=y-s*i/5, ww=s*.18*(1-i/5); ctx.moveTo(x-ww,yy); ctx.lineTo(x+ww,yy);} ctx.stroke(); ctx.fillStyle='#f5c26b'; ctx.beginPath(); ctx.arc(x,y-s,4,0,7); ctx.fill();}
  function sat(x,y,s,a){ctx.globalAlpha=a; ctx.fillStyle='#e8eef7'; ctx.fillRect(x-s*.12,y-s*.12,s*.24,s*.24); ctx.fillStyle='#2b5aa8'; ctx.strokeStyle='#8fdbff'; ctx.lineWidth=1;
    ctx.fillRect(x-s*.7,y-s*.09,s*.5,s*.18); ctx.strokeRect(x-s*.7,y-s*.09,s*.5,s*.18); ctx.fillRect(x+s*.2,y-s*.09,s*.5,s*.18); ctx.strokeRect(x+s*.2,y-s*.09,s*.5,s*.18);
    var g=ctx.createRadialGradient(x,y,0,x,y,s); g.addColorStop(0,'rgba(94,200,255,.35)'); g.addColorStop(1,'rgba(94,200,255,0)'); ctx.fillStyle=g; ctx.beginPath(); ctx.arc(x,y,s,0,7); ctx.fill();}
  function dash(x1,y1,x2,y2,col,a,k){ctx.globalAlpha=a; ctx.strokeStyle=col; ctx.lineWidth=2; ctx.setLineDash([6,6]); ctx.lineDashOffset=RM?0:-t/30; ctx.beginPath(); ctx.moveTo(x1,y1); ctx.lineTo(x1+(x2-x1)*k,y1+(y2-y1)*k); ctx.stroke(); ctx.setLineDash([]);}
  var S={
    phone:function(p,a){drawGround(a); var P=phonePos(), s=H*(narrow()?.14:.2), rise=ease(p*1.6); phone(P.x,P.y+(1-rise)*s*1.2,s,a); if(rise>.95) ripples(P.x,P.y-s*.9,-Math.PI/2+.5,'#5ec8ff',a);},
    tower:function(p,a){drawGround(a); var P=phonePos(), s=H*(narrow()?.14:.2); phone(P.x,P.y,s,a); var tx=W*(narrow()?.78:.72)+ease(cl(p*1.4-.3))*W*.5, k=1-ease(cl(p*1.4-.3));
      tower(tx,ground(),H*(narrow()?.22:.32),a); dash(P.x+s*.25,P.y-s*.8,tx,ground()-H*(narrow()?.22:.32),'#f5c26b',a*k,1);
      if(k<.4){ctx.globalAlpha=a*(1-k/.4); ctx.fillStyle='#ff9a8a'; ctx.font='600 '+Math.round(H*.03)+'px "Inter Tight",system-ui'; ctx.textAlign='center'; ctx.fillText('No service',P.x,P.y-s-18);}},
    sat:function(p,a){drawGround(a); var P=phonePos(), s=H*(narrow()?.14:.2); phone(P.x,P.y,s,a,'#6ee79a'); var sx=W*(narrow()?.7:.68), sy=H*(narrow()?.12:.2)-(1-ease(p*2))*H*.4, k=ease(cl(p*2-.5));
      ctx.globalAlpha=a*.25; ctx.strokeStyle='#5ec8ff'; ctx.beginPath(); ctx.ellipse(W*.5,H*1.6,W*.9,H*1.4,0,Math.PI*1.1,Math.PI*1.9); ctx.stroke();
      sat(sx,sy,H*.09,a); dash(P.x,P.y-s,sx,sy,'#6ee79a',a,k); if(k>=1&&!RM){for(var i=0;i<3;i++){var u=(t/1100+i/3)%1, up=i%2===0; var x=up?P.x+(sx-P.x)*u:sx+(P.x-sx)*u, y=up?(P.y-s)+(sy-P.y+s)*u:sy+(P.y-s-sy)*u; ctx.globalAlpha=a; ctx.fillStyle='#fff'; ctx.beginPath(); ctx.arc(x,y,3.5,0,7); ctx.fill();}}},
    race:function(p,a){var L=W*(narrow()?.1:.08), R=W*(narrow()?.78:.8), Tp=H*(narrow()?.14:.12), B=H*(narrow()?.5:.74), cur=override!=null?override:T0+(T1-T0)*cl(p*1.15);
      var x=function(tt){return L+(R-L)*(tt-T0)/(T1-T0);}, mx=0; F.forEach(function(f){D.ser.forEach(function(s){mx=Math.max(mx,f.v[s.id]||0);});}); mx=Math.ceil(mx/100)*100;
      var y=function(v){return B-(B-Tp)*v/mx;};
      ctx.globalAlpha=a; ctx.strokeStyle='rgba(255,255,255,.08)'; ctx.fillStyle='#7f93a8'; ctx.font='500 11px "JetBrains Mono",monospace'; ctx.textAlign='right'; ctx.lineWidth=1;
      for(var v=0;v<=mx;v+=mx/4){ctx.beginPath(); ctx.moveTo(L,y(v)); ctx.lineTo(R,y(v)); ctx.stroke(); ctx.fillText(Math.round(v),L-6,y(v)+4);}
      ctx.textAlign='center'; for(var yr=T0y;yr<=new Date(T1).getUTCFullYear();yr++){var xx=x(Date.UTC(yr,0,1)); ctx.fillText(yr,xx,B+18);}
      ctx.globalAlpha=a*.5; ctx.textAlign='left'; ctx.fillText('Satellite counts start '+fmt(F[0].t),L+4,Tp-8);
      var labs=[]; D.ser.forEach(function(s){ctx.globalAlpha=a; ctx.strokeStyle=s.c; ctx.lineWidth=2.4; ctx.beginPath(); var lastPt=null;
        F.forEach(function(f,i){if(f.t>cur&&i>0){var g=F[i-1], k=(cur-g.t)/(f.t-g.t); if(k>0){var vv=(g.v[s.id]||0)+((f.v[s.id]||0)-(g.v[s.id]||0))*k; ctx.lineTo(x(cur),y(vv)); lastPt=[x(cur),y(vv),vv];} return;}
          if(f.t>cur) return; var X=x(f.t),Y=y(f.v[s.id]||0); if(!lastPt) ctx.moveTo(X,Y); else ctx.lineTo(X,Y); lastPt=[X,Y,f.v[s.id]||0];}); ctx.stroke();
        if(lastPt){ctx.fillStyle=s.c; ctx.beginPath(); ctx.arc(lastPt[0],lastPt[1],4,0,7); ctx.fill(); labs.push({x:lastPt[0]+8,y:lastPt[1]+4,c:s.c,t:(narrow()?s.l.replace(/ \(.*\)| BlueBirds|Direct to Cell/g,''):s.l.replace(' BlueBirds',''))+' '+Math.round(lastPt[2])});}});
      labs.sort(function(p,q){return q.y-p.y;}); for(var li=1;li<labs.length;li++) if(labs[li].y>labs[li-1].y-14) labs[li].y=labs[li-1].y-14; // dodge, bottom up
      ctx.font='600 12px "Inter Tight",system-ui'; ctx.textAlign='left'; labs.forEach(function(l){ctx.globalAlpha=a; ctx.fillStyle=l.c; ctx.fillText(l.t,l.x,l.y);});
      // milestones along the axis
      var mi=-1; MS.forEach(function(m,i){var X=x(m.t), on=m.t<=cur; if(on) mi=i; ctx.globalAlpha=a*(on?1:.3); ctx.fillStyle=on?'#2fe0c8':'#7f93a8'; ctx.beginPath(); ctx.arc(X,B+32,on?4:3,0,7); ctx.fill();});
      ctx.globalAlpha=a; ctx.fillStyle='#fff'; ctx.font='500 '+Math.round(Math.min(34,H*.05))+'px "JetBrains Mono",monospace'; ctx.textAlign='right'; ctx.fillText(fmt(Math.min(cur,T1)),R,narrow()?Tp-Math.min(34,H*.05)*1.1:Tp+Math.min(34,H*.05)*.4);
      if(msEl&&mi!==msEl._i){msEl._i=mi; msEl.innerHTML=mi<0?'':'<time>'+fmt(MS[mi].t,1)+'</time> '+MS[mi].x.replace(/[&<]/g,function(c){return c==='&'?'&amp;':'&lt;';})+' <a href="'+MS[mi].u+'">'+MS[mi].l+'</a>';}
      if(range&&override==null) range.value=Math.round(100*(Math.min(cur,T1)-T0)/(T1-T0));},
    board:function(p,a){var n=D.b.length, L=W*(narrow()?.06:.08), R=W*.92, Tp=H*(narrow()?.06:.16), rowH=Math.min(70,(H*(narrow()?.46:.62))/n), mx=0;
      D.b.forEach(function(b){mx=Math.max(mx,b.n.live+b.n.trial+b.n.announced);});
      D.b.forEach(function(b,i){var y=Tp+i*rowH, k=ease(cl(p*1.6-i*.12)), x=L, bw=(R-L)*.62, fs=Math.round(Math.min(18,rowH*.3));
        ctx.globalAlpha=a; ctx.fillStyle='#7f93a8'; ctx.font='500 '+fs+'px "JetBrains Mono",monospace'; ctx.textAlign='left'; ctx.fillText(i+1,x,y+fs);
        ctx.fillStyle='#fff'; ctx.font='600 '+fs+'px "Inter Tight",system-ui'; ctx.fillText(b.l,x+fs*1.5,y+fs);
        var bx=x+fs*1.5, by=y+fs*1.5, bh=Math.max(8,rowH*.22); [['live','#6ee79a'],['trial','#f5c26b'],['announced','#7f93a8']].forEach(function(z){var w=bw*(b.n[z[0]]/Math.max(1,mx))*k; if(w>0){ctx.fillStyle=z[1]; ctx.fillRect(bx,by,w,bh); bx+=w+2;}});
        ctx.fillStyle='#cfdbe8'; ctx.font='500 '+Math.round(fs*.75)+'px "JetBrains Mono",monospace'; ctx.globalAlpha=a*k;
        var txt=(b.n.live?b.n.live+' live ':'')+(b.n.trial?b.n.trial+' trial ':'')+(b.n.announced?b.n.announced+' announced ':'')+(b.n.live+b.n.trial+b.n.announced?'':'iPhone features ')+'· '+(b.sat!=null?b.sat+' sats':'partners’ sats');
        if(narrow()) ctx.fillText(txt,x+fs*1.5,by+bh+fs*1.05); else ctx.fillText(txt,bx+8,by+bh);});},
    today:function(p,a){var vals=[[D.tot.live,'live services','#6ee79a'],[D.tot.cty,'countries live','#5ec8ff'],[D.tot.sats,'satellites','#9b7bff']], k=ease(p*2);
      vals.forEach(function(v,i){var nw=narrow(), x=nw?W*.5:W*(.2+i*.3), y=nw?H*(.12+i*.15):H*.42, fs=Math.round(nw?H*.08:Math.min(W*.09,H*.16));
        ctx.globalAlpha=a; ctx.textAlign='center'; ctx.fillStyle=v[2]; ctx.font='600 '+fs+'px "Inter Tight",system-ui'; ctx.fillText(Math.round(v[0]*k).toLocaleString('en-GB'),x,y);
        ctx.fillStyle='#cfdbe8'; ctx.font='500 '+Math.round(fs*.22)+'px "JetBrains Mono",monospace'; ctx.fillText(v[1].toUpperCase(),x,y+fs*.4);});}
  };
  function measure(){var vh=innerHeight, k=null, p=0;
    steps.forEach(function(s){var r=s.getBoundingClientRect(); if(r.top<vh*.65){k=s.getAttribute('data-s'); p=cl((vh*.65-r.top)/r.height);}});
    if(!k){k='phone'; p=0;}
    if(k!==cur.k){prev={k:cur.k,p:cur.k==='race'?1:cur.p}; fadeT=t; override=null; if(rw) rw.hidden=(k!=='race');
      steps.forEach(function(s){s.classList.toggle('on',s.getAttribute('data-s')===k);});}
    if(override!=null&&Math.abs(p-lastP)>.04) override=null; lastP=p; cur={k:k,p:p};}
  function draw(){ctx.setTransform(DPR,0,0,DPR,0,0); ctx.clearRect(0,0,W,H); var fa=RM?1:cl((t-fadeT)/350);
    if(prev&&fa<1){S[prev.k](prev.p,1-fa);} S[cur.k](cur.p,fa); ctx.globalAlpha=1;}
  function frame(ts){if(!running) return; var dt=last?Math.min(50,ts-last):16; last=ts; t+=dt; measure(); draw(); requestAnimationFrame(frame);}
  function play(){if(running) return; running=true; last=0; requestAnimationFrame(frame);}
  size(); measure(); draw();
  addEventListener('resize',function(){size(); draw();});
  if(range) range.addEventListener('input',function(){override=T0+(T1-T0)*range.value/100; if(!running){draw();}});
  if(step){window.__story={render:function(dt){t+=dt; measure(); draw();}}; return;}
  if(RM){addEventListener('scroll',function(){measure(); draw();},{passive:true}); return;}
  if('IntersectionObserver' in window) new IntersectionObserver(function(es){if(es[0].isIntersecting) play(); else running=false;}).observe(sec.querySelector('.st-wrap')); else play();
})();
