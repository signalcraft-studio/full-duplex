/* Full Duplex home, "the mix": C's scroll story with sticky canvas graphics, in two parts around B's globe (assets/orbital.js).
   Part 1: hero -> your phone -> out of range -> a satellite catches it. Part 2: A's race (one dot per phone-capable satellite, clusters per
   network, date counter, then the partner phones from the tracker) driven by scroll and the rewind bar over sourced milestones ->
   leaderboard -> today's totals. Every number comes from #story-data (race.json, milestones.json, constellations.json, tracker). No libraries.
   Phones (<700px) and prefers-reduced-motion get still frames that change with scroll only; desktop animates only while on screen. */
(function(){
  var el=document.getElementById('story-data'); if(!el) return;
  var D; try{D=JSON.parse(el.textContent);}catch(e){return;}
  var RM=matchMedia('(prefers-reduced-motion: reduce)').matches, step=/[?&]step\b/.test(location.search);
  var STILL=RM||(matchMedia('(max-width: 699px)').matches&&!step);
  var MON=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  var ms=function(s){return Date.parse(s+'T00:00:00Z');};
  var F=D.f.map(function(f){return {t:ms(f[0]),v:f[1]};}), MS=D.ms.map(function(m){return {t:ms(m[0]),d:m[0],x:m[1],u:m[2],l:m[3]};});
  var F0=F[0].t, T1=F[F.length-1].t, T0=Date.UTC(new Date(Math.min(MS.length?MS[0].t:F0,F0)).getUTCFullYear(),0,1);
  // time axis for scroll and the rewind bar: the first quarter covers the early milestones (before monthly counts start), the rest the counts
  var Q=F0>T0?.25:0;
  function timeOf(u){return u<=Q?T0+(F0-T0)*(Q?u/Q:1):F0+(T1-F0)*(u-Q)/(1-Q);}
  function uOf(tt){return tt<=F0?(Q?Q*(tt-T0)/(F0-T0):0):Q+(1-Q)*(tt-F0)/(T1-F0);}
  var ease=function(x){x=Math.max(0,Math.min(1,x)); return RM?(x>0?1:0):x<.5?2*x*x:1-Math.pow(-2*x+2,2)/2;};
  var cl=function(x){return Math.max(0,Math.min(1,x));};
  function fmt(d,day){var x=new Date(d); return (day?x.getUTCDate()+' ':'')+MON[x.getUTCMonth()]+' '+x.getUTCFullYear();}
  function escH(s){return String(s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
  var insts=[];
  [].forEach.call(document.querySelectorAll('section.story .st-wrap'),function(wrap){insts.push(make(wrap));});
  function make(wrap){
    var sec=wrap.parentNode, fig=wrap.querySelector('.st-fig'), cv=fig.querySelector('canvas'), ctx=cv.getContext&&cv.getContext('2d'); if(!ctx) return null;
    sec.classList.add('js');
    var steps=[].slice.call(wrap.querySelectorAll('.st-step')), rw=fig.querySelector('.st-rw'), range=fig.querySelector('input[type=range]'), msEl=fig.querySelector('.st-ms');
    var first=steps[0].getAttribute('data-s');
    var W=0,H=0,DPR=1,t=0,last=0,running=false,cur={k:first,p:0},prev=null,fadeT=-1e9,override=null,lastP=-1;
    var narrow=function(){return W<700;};
    // ---- race layout (A's "race to your phone"), inside a box of the canvas
    var R={s:D.race.s,p:D.race.p,col:{}}, parts=[], emitAt={}, prevN={};
    R.s.forEach(function(s){R.col[s.id]=s.c;});
    function raceLayout(){
      var nw=narrow(), bx=0, by=H*(nw?.02:.05), bw=W, bh=H*(nw?.64:.8), m=Math.min(bw,bh), wide=bw/bh>1.5;
      R.K=wide?1.3:1; R.cx=bx+bw*.5; R.cy=by+bh*.5; R.re=m*(wide?.14:.11);
      var rx1=bw*(wide?.24:.3), ry1=bh*(wide?.3:.29), rx2=bw*(wide?.4:.44), ry2=bh*(wide?.43:.43);
      var ORDER=['starlink-dtc','ast','globalstar','lynk','skylo'], HANG={'starlink-dtc':180,'ast':-40,'globalstar':2,'lynk':34,'skylo':64};
      var wgt={}, tot=0; ORDER.forEach(function(id){var n=(R.p[id]||[]).length; wgt[id]=n?Math.max(n,3):0; tot+=wgt[id];});
      var a=180-(tot?wgt['starlink-dtc']/tot*360:0)/2; R.phones=[];
      ['starlink-dtc','skylo','lynk','globalstar','ast'].forEach(function(id){var ps=R.p[id]||[], span=tot?wgt[id]/tot*360:0;
        ps.forEach(function(p,i){var th=-(a+span*(i+.5)/ps.length)*Math.PI/180; R.phones.push({id:id,l:p[0],st:p[1],x:R.cx+rx2*Math.cos(th),y:R.cy+ry2*Math.sin(th),i:R.phones.length});}); a+=span;});
      R.hubs={}; R.s.forEach(function(s){var th=HANG[s.id]*Math.PI/180; R.hubs[s.id]={x:R.cx+rx1*Math.cos(th)*(s.id==='starlink-dtc'?.92:1),y:R.cy+ry1*Math.sin(th)};});
      R.c=m*.0047*R.K; R.dots={};
      R.s.forEach(function(s){var n=Math.max(s.n||0,s.max||0), arr=[]; for(var i=0;i<n;i++) arr.push({r:R.c*Math.sqrt(i+.5)*1.18,a:i*2.39996,b:-1}); R.dots[s.id]=arr;});
    }
    function countsAt(tt){var o={};
      if(tt<=F0||tt>=T1){var f=tt<=F0?F[0]:F[F.length-1]; R.s.forEach(function(s){o[s.id]=f.v[s.id]||0;}); return o;}
      for(var k=0;k<F.length-1;k++) if(tt<F[k+1].t){var u=(tt-F[k].t)/(F[k+1].t-F[k].t); R.s.forEach(function(s){var a=F[k].v[s.id]||0,b=F[k+1].v[s.id]||0; o[s.id]=a+(b-a)*u;}); return o;}
      return o;}
    function bez(p,q,u,bend){var mx=(p.x+q.x)/2,my=(p.y+q.y)/2,dx=q.x-p.x,dy=q.y-p.y,ox=mx-dy*bend,oy=my+dx*bend,v=1-u; return {x:v*v*p.x+2*v*u*ox+u*u*q.x,y:v*v*p.y+2*v*u*oy+u*u*q.y,ox:ox,oy:oy};}
    function emit(a,b,c,dur,bend){if(parts.length<200) parts.push({a:a,b:b,c:c,t0:t,d:dur,bend:bend});}
    function miniPhone(x,y,s,c,a){ctx.globalAlpha=a; ctx.strokeStyle=c; ctx.lineWidth=1.3; var w=s*.62,h=s; ctx.beginPath(); if(ctx.roundRect) ctx.roundRect(x-w/2,y-h/2,w,h,s*.14); else ctx.rect(x-w/2,y-h/2,w,h); ctx.stroke(); ctx.fillStyle=c; ctx.globalAlpha=a*.25; ctx.fill();}
    // ---- part 1 drawing helpers (C)
    function ground(){return H*(narrow()?.56:.8);}
    function phonePos(){return {x:W*(narrow()?.3:.32), y:ground()};}
    function drawGround(a){ctx.globalAlpha=a; var g=ctx.createLinearGradient(0,ground(),0,H); g.addColorStop(0,'rgba(47,224,200,.10)'); g.addColorStop(1,'rgba(47,224,200,0)'); ctx.fillStyle=g; ctx.fillRect(0,ground(),W,H-ground());
      ctx.strokeStyle='rgba(143,219,255,.35)'; ctx.lineWidth=1; ctx.beginPath(); ctx.moveTo(0,ground()); ctx.lineTo(W,ground()); ctx.stroke();}
    function phone(x,y,s,a,lit){var w=s*.5,h=s; ctx.globalAlpha=a; ctx.fillStyle='#0d1730'; ctx.strokeStyle='#cfe3ff'; ctx.lineWidth=2;
      ctx.beginPath(); if(ctx.roundRect) ctx.roundRect(x-w/2,y-h,w,h,s*.08); else ctx.rect(x-w/2,y-h,w,h); ctx.fill(); ctx.stroke();
      var g=ctx.createLinearGradient(x,y-h,x,y); g.addColorStop(0,lit||'#5ec8ff'); g.addColorStop(1,'#9b7bff'); ctx.fillStyle=g; ctx.globalAlpha=a*.85; ctx.fillRect(x-w/2+4,y-h+10,w-8,h-20);}
    function ripples(x,y,dir,col,a){if(STILL){ctx.globalAlpha=a*.5; ctx.strokeStyle=col; ctx.lineWidth=2; ctx.beginPath(); ctx.arc(x,y,30,dir-0.7,dir+0.7); ctx.stroke(); ctx.globalAlpha=a*.25; ctx.beginPath(); ctx.arc(x,y,60,dir-0.7,dir+0.7); ctx.stroke(); return;}
      for(var i=0;i<3;i++){var r=((t/1400+i/3)%1); ctx.globalAlpha=a*(1-r); ctx.strokeStyle=col; ctx.lineWidth=2; ctx.beginPath(); ctx.arc(x,y,10+r*90,dir-0.7,dir+0.7); ctx.stroke();}}
    function tower(x,y,s,a){ctx.globalAlpha=a; ctx.strokeStyle='#8fa6c2'; ctx.lineWidth=2; ctx.beginPath(); ctx.moveTo(x-s*.18,y); ctx.lineTo(x,y-s); ctx.lineTo(x+s*.18,y);
      for(var i=1;i<5;i++){var yy=y-s*i/5, ww=s*.18*(1-i/5); ctx.moveTo(x-ww,yy); ctx.lineTo(x+ww,yy);} ctx.stroke(); ctx.fillStyle='#f5c26b'; ctx.beginPath(); ctx.arc(x,y-s,4,0,7); ctx.fill();}
    function sat(x,y,s,a){ctx.globalAlpha=a; ctx.fillStyle='#e8eef7'; ctx.fillRect(x-s*.12,y-s*.12,s*.24,s*.24); ctx.fillStyle='#2b5aa8'; ctx.strokeStyle='#8fdbff'; ctx.lineWidth=1;
      ctx.fillRect(x-s*.7,y-s*.09,s*.5,s*.18); ctx.strokeRect(x-s*.7,y-s*.09,s*.5,s*.18); ctx.fillRect(x+s*.2,y-s*.09,s*.5,s*.18); ctx.strokeRect(x+s*.2,y-s*.09,s*.5,s*.18);
      var g=ctx.createRadialGradient(x,y,0,x,y,s); g.addColorStop(0,'rgba(94,200,255,.35)'); g.addColorStop(1,'rgba(94,200,255,0)'); ctx.fillStyle=g; ctx.beginPath(); ctx.arc(x,y,s,0,7); ctx.fill();}
    function dash(x1,y1,x2,y2,col,a,k){ctx.globalAlpha=a; ctx.strokeStyle=col; ctx.lineWidth=2; ctx.setLineDash([6,6]); ctx.lineDashOffset=STILL?0:-t/30; ctx.beginPath(); ctx.moveTo(x1,y1); ctx.lineTo(x1+(x2-x1)*k,y1+(y2-y1)*k); ctx.stroke(); ctx.setLineDash([]);}
    var stars=null;
    function starfield(a){if(!stars){stars=[]; var seed=11; var rnd=function(){seed=(seed*16807)%2147483647; return seed/2147483647;}; for(var i=0;i<140;i++) stars.push([rnd(),rnd()*.75,rnd()]);}
      ctx.fillStyle='#dce8ff'; stars.forEach(function(s){ctx.globalAlpha=a*(.15+s[2]*.5); ctx.fillRect(s[0]*W,s[1]*H,s[2]>.9?2:1,s[2]>.9?2:1);});}
    var sz=function(){return H*(narrow()?.14:.2);};
    var S={
      intro:function(p,a){starfield(a); drawGround(a); var P=phonePos(), s=sz(), rise=STILL?1:ease(t/1400); phone(P.x,P.y+(1-rise)*s*1.2,s,a); if(rise>.95) ripples(P.x,P.y-s*.9,-Math.PI/2+.5,'#5ec8ff',a);},
      phone:function(p,a){starfield(a); drawGround(a); var P=phonePos(), s=sz(); phone(P.x,P.y,s,a); var tx=W*(narrow()?.78:.72); tower(tx,ground(),H*(narrow()?.22:.32),a); dash(P.x+s*.25,P.y-s*.8,tx,ground()-H*(narrow()?.22:.32),'#f5c26b',a,1); ripples(P.x,P.y-s*.9,-Math.PI/2+.5,'#5ec8ff',a);},
      tower:function(p,a){starfield(a); drawGround(a); var P=phonePos(), s=sz(); phone(P.x,P.y,s,a,'#7f93a8'); var tx=W*(narrow()?.78:.72)+ease(cl(p*1.4-.1))*W*.5, k=1-ease(cl(p*1.4-.1));
        tower(tx,ground(),H*(narrow()?.22:.32),a); dash(P.x+s*.25,P.y-s*.8,tx,ground()-H*(narrow()?.22:.32),'#f5c26b',a*k,1);
        if(k<.4){ctx.globalAlpha=a*(1-k/.4); ctx.fillStyle='#ff9a8a'; ctx.font='600 '+Math.round(H*.03)+'px "Inter Tight",system-ui'; ctx.textAlign='center'; ctx.fillText('No service',P.x,P.y-s-18);}},
      sat:function(p,a){starfield(a); drawGround(a); var P=phonePos(), s=sz(); phone(P.x,P.y,s,a,'#6ee79a'); var sx=W*(narrow()?.7:.68), sy=H*(narrow()?.12:.2)-(1-ease(p*2))*H*.4, k=ease(cl(p*2-.5));
        ctx.globalAlpha=a*.25; ctx.strokeStyle='#5ec8ff'; ctx.lineWidth=1; ctx.beginPath(); ctx.ellipse(W*.5,H*1.6,W*.9,H*1.4,0,Math.PI*1.1,Math.PI*1.9); ctx.stroke();
        sat(sx,sy,H*.09,a); dash(P.x,P.y-s,sx,sy,'#6ee79a',a,k); if(k>=1&&!STILL){for(var i=0;i<3;i++){var u=(t/1100+i/3)%1, up=i%2===0; var x=up?P.x+(sx-P.x)*u:sx+(P.x-sx)*u, y=up?(P.y-s)+(sy-P.y+s)*u:sy+(P.y-s-sy)*u; ctx.globalAlpha=a; ctx.fillStyle='#fff'; ctx.beginPath(); ctx.arc(x,y,3.5,0,7); ctx.fill();}}},
      race:function(p,a){
        var curT=override!=null?override:timeOf(cl(p*1.15)), st=countsAt(curT), early=curT<F0, ph=cl((curT-(T1-70*864e5))/(70*864e5)), H_=R.hubs, nw=narrow();
        // Earth -> hub links
        R.s.forEach(function(s){var h=H_[s.id], n=st[s.id], on=(n>0||!s.n)?1:.25, q=bez({x:R.cx,y:R.cy},h,.5,.12);
          ctx.globalAlpha=.22*a*on; ctx.strokeStyle=s.c; ctx.lineWidth=1; if(!s.n) ctx.setLineDash([3,4]); ctx.beginPath(); ctx.moveTo(R.cx,R.cy); ctx.quadraticCurveTo(q.ox,q.oy,h.x,h.y); ctx.stroke(); ctx.setLineDash([]);});
        if(ph>0) R.phones.forEach(function(q){var h=H_[q.id]; if(!h) return; var b=bez(h,q,.5,.08), k=cl(ph*1.6-q.i/R.phones.length*.6); q.a=k;
          ctx.globalAlpha=(q.st==='announced'?.12:.2)*k*a; ctx.strokeStyle=R.col[q.id]; ctx.lineWidth=1; if(q.st==='announced') ctx.setLineDash([2,4]); ctx.beginPath(); ctx.moveTo(h.x,h.y); ctx.quadraticCurveTo(b.ox,b.oy,q.x,q.y); ctx.stroke(); ctx.setLineDash([]);});
        // Earth
        var re=R.re, g=ctx.createRadialGradient(R.cx-re*.35,R.cy-re*.4,re*.1,R.cx,R.cy,re); g.addColorStop(0,'#2a5c9a'); g.addColorStop(.6,'#123158'); g.addColorStop(1,'#081a33');
        var halo=ctx.createRadialGradient(R.cx,R.cy,re*.9,R.cx,R.cy,re*1.7); halo.addColorStop(0,'rgba(94,200,255,.28)'); halo.addColorStop(1,'rgba(94,200,255,0)');
        ctx.globalAlpha=a; ctx.fillStyle=halo; ctx.beginPath(); ctx.arc(R.cx,R.cy,re*1.7,0,7); ctx.fill(); ctx.fillStyle=g; ctx.beginPath(); ctx.arc(R.cx,R.cy,re,0,7); ctx.fill();
        ctx.save(); ctx.beginPath(); ctx.arc(R.cx,R.cy,re,0,7); ctx.clip(); ctx.strokeStyle='rgba(143,219,255,.22)'; ctx.lineWidth=.8;
        for(var i=-2;i<=2;i++){ctx.beginPath(); ctx.ellipse(R.cx,R.cy+i*re*.36,re*Math.sqrt(1-Math.pow(i*.36,2)),re*.08,0,0,7); ctx.stroke();}
        var rot=STILL?.1:(t/9000)%1; for(i=0;i<4;i++){var p2=((rot+i/4)%1)*Math.PI; ctx.beginPath(); ctx.ellipse(R.cx,R.cy,Math.abs(Math.cos(p2))*re,re,0,0,7); ctx.stroke();}
        ctx.restore(); ctx.globalAlpha=a; ctx.strokeStyle='rgba(143,219,255,.6)'; ctx.lineWidth=1.2; ctx.beginPath(); ctx.arc(R.cx,R.cy,re,0,7); ctx.stroke();
        // clusters: 1 dot = 1 satellite
        var spin=STILL?0:t/60000;
        R.s.forEach(function(s){var h=H_[s.id], n=st[s.id], arr=R.dots[s.id]||[], dim=early?.35:1;
          if(!s.n){ctx.globalAlpha=.85*a; ctx.strokeStyle=s.c; ctx.lineWidth=1.4; ctx.beginPath(); ctx.arc(h.x,h.y,R.c*3.2,0,7); ctx.stroke(); ctx.globalAlpha=.35*a; ctx.beginPath(); ctx.arc(h.x,h.y,R.c*5.2,0,7); ctx.stroke();}
          ctx.fillStyle=s.c;
          for(var i=0;i<arr.length;i++){var d=arr[i], vis=cl(n-i); if(vis<=0){d.b=-1; continue;} if(d.b<0) d.b=t; var glow=STILL?0:Math.max(0,1-(t-d.b)/700), an=d.a+spin*(1+12/(d.r+4));
            ctx.globalAlpha=Math.min(1,vis*(.82+glow*.18))*a*dim; ctx.beginPath(); ctx.arc(h.x+Math.cos(an)*d.r,h.y+Math.sin(an)*d.r,R.c*(.34+glow*.9),0,7); ctx.fill();}
          var whole=Math.floor(n); if(!STILL&&prevN[s.id]!==undefined&&whole>prevN[s.id]){var k=Math.min(3,whole-prevN[s.id]); while(k--) emit({x:R.cx,y:R.cy},h,s.c,900+Math.random()*500,.12);} prevN[s.id]=whole;
          if(!STILL&&(n>0||!s.n)&&t>(emitAt[s.id]||0)){emit({x:R.cx,y:R.cy},h,s.c,1300,.12); if(ph>0) emit(h,{x:R.cx,y:R.cy},s.c,1300,-.12); emitAt[s.id]=t+2000/(1+Math.log(1+(s.n||3))/3);}
          var fs=Math.max(10.5,Math.min(13.5,W/52))*R.K; ctx.globalAlpha=a; ctx.font='600 '+fs+'px "Inter Tight",system-ui,sans-serif'; ctx.textAlign='center';
          var ly=h.y+(arr.length?arr[arr.length-1].r+fs*(s.id==='starlink-dtc'?1.5:1.35):R.c*5.2+fs*1.3);
          var lbl=nw?s.l.replace(/ \(.*\)/,'').replace(' Direct to Cell',''):s.l;
          ctx.fillStyle='#e8eef7'; ctx.fillText(lbl,h.x,ly); ctx.fillStyle=s.c; ctx.font='500 '+(fs*.92)+'px "JetBrains Mono",ui-monospace,monospace';
          ctx.fillText(s.n?Math.round(n).toLocaleString('en-GB'):(s.note||''),h.x,ly+fs*1.2);});
        if(ph>0){var ps=Math.max(9,Math.min(15,W/48))*R.K; R.phones.forEach(function(q){var c=q.st==='live'?'#6ee79a':q.st==='trial'?'#f5c26b':q.st==='announced'?'#7f93a8':R.col[q.id]; miniPhone(q.x,q.y,ps,c,(q.a||0)*a);
          if(!STILL&&q.a>.9&&q.st!=='announced'&&Math.random()<(q.st==='live'?.01:.004)){var h=H_[q.id]; if(Math.random()<.5) emit(h,q,R.col[q.id],1100,.08); else emit(q,h,'#6ee79a',1100,-.08);}});}
        parts=parts.filter(function(q){var u=(t-q.t0)/q.d; if(u>=1) return false; var b=bez(q.a,q.b,u,q.bend); ctx.globalAlpha=Math.sin(u*Math.PI)*a; ctx.fillStyle=q.c; ctx.beginPath(); ctx.arc(b.x,b.y,R.c*.7,0,7); ctx.fill();
          ctx.globalAlpha*=.25; ctx.beginPath(); ctx.arc(b.x,b.y,R.c*2,0,7); ctx.fill(); return true;});
        // date counter + total
        var tot=0; R.s.forEach(function(s){tot+=Math.round(st[s.id]||0);});
        var dfs=Math.round(Math.min(nw?30:40,H*.055)), dx=nw?W*.05:W*.04, dy=nw?H*.05:H*.09;
        ctx.globalAlpha=a; ctx.textAlign='left'; ctx.fillStyle='#fff'; ctx.font='500 '+dfs+'px "JetBrains Mono",monospace'; ctx.fillText(fmt(Math.min(curT,T1),curT>=T1),dx,dy);
        ctx.fillStyle='#cfdbe8'; ctx.font='500 '+Math.round(dfs*.42)+'px "JetBrains Mono",monospace';
        ctx.fillText(early?'Monthly satellite counts start '+fmt(F0):tot.toLocaleString('en-GB')+' phone-capable satellites in orbit',dx,dy+dfs*.8);
        // milestone text under the rewind bar
        var mi=-1; MS.forEach(function(m,i){if(m.t<=curT) mi=i;});
        if(msEl&&mi!==msEl._i){msEl._i=mi; msEl.innerHTML=mi<0?'':'<time>'+fmt(MS[mi].t,1)+'</time> '+escH(MS[mi].x)+' <a href="'+escH(MS[mi].u)+'">'+escH(MS[mi].l)+'</a>';}
        if(range&&override==null) range.value=Math.round(100*uOf(Math.min(curT,T1)));},
      board:function(p,a){var n=D.b.length, L=W*(narrow()?.06:.08), Rr=W*.92, Tp=H*(narrow()?.06:.16), rowH=Math.min(70,(H*(narrow()?.46:.62))/n), mx=0;
        D.b.forEach(function(b){mx=Math.max(mx,b.n.live+b.n.trial+b.n.announced);});
        D.b.forEach(function(b,i){var y=Tp+i*rowH, k=ease(cl(p*1.6-i*.12)), x=L, bw=(Rr-L)*.62, fs=Math.round(Math.min(18,rowH*.3));
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
    function size(){var r=cv.getBoundingClientRect(); W=r.width; H=r.height; DPR=Math.min(2,devicePixelRatio||1); cv.width=Math.round(W*DPR); cv.height=Math.round(H*DPR); stars=null; raceLayout();}
    function measure(){var vh=innerHeight, k=null, p=0;
      steps.forEach(function(s){var r=s.getBoundingClientRect(); if(r.top<vh*.65){k=s.getAttribute('data-s'); p=cl((vh*.65-r.top)/r.height);}});
      if(!k){k=first; p=0;}
      if(k!==cur.k){prev={k:cur.k,p:cur.k==='race'?1:cur.p}; fadeT=t; override=null; if(rw) rw.hidden=(k!=='race');
        steps.forEach(function(s){s.classList.toggle('on',s.getAttribute('data-s')===k);});}
      if(override!=null&&Math.abs(p-lastP)>.04) override=null; lastP=p; cur={k:k,p:p};
      var ft=fig.getBoundingClientRect().top, stick=parseFloat(getComputedStyle(fig).top)||0;
      wrap.classList.toggle('is-stuck', ft<=stick+1);}
    function draw(){ctx.setTransform(DPR,0,0,DPR,0,0); ctx.clearRect(0,0,W,H); var fa=STILL?1:cl((t-fadeT)/350);
      if(prev&&fa<1&&prev.k!=='race') S[prev.k](prev.p,1-fa); S[cur.k](cur.p,fa); ctx.globalAlpha=1;}
    function frame(ts){if(!running) return; var dt=last?Math.min(50,ts-last):16; last=ts; t+=dt; measure(); draw(); requestAnimationFrame(frame);}
    function play(){if(running) return; running=true; last=0; requestAnimationFrame(frame);}
    size(); measure(); steps.forEach(function(s){s.classList.toggle('on',s.getAttribute('data-s')===cur.k);}); if(rw) rw.hidden=(cur.k!=='race'); draw();
    var rz; addEventListener('resize',function(){clearTimeout(rz); rz=setTimeout(function(){size(); draw();},120);});
    if(range) range.addEventListener('input',function(){override=timeOf(range.value/100); if(!running) draw();});
    var api={render:function(dt){t+=dt; measure(); draw();}};
    if(step) return api;
    if(STILL){var pend=false; addEventListener('scroll',function(){if(pend) return; pend=true; requestAnimationFrame(function(){pend=false; var r=wrap.getBoundingClientRect(); if(r.bottom<0||r.top>innerHeight) return; measure(); draw();});},{passive:true}); return api;}
    var vis=true; if('IntersectionObserver' in window) new IntersectionObserver(function(es){vis=es[0].isIntersecting; if(vis&&!document.hidden) play(); else running=false;}).observe(wrap); else play();
    document.addEventListener('visibilitychange',function(){if(document.hidden) running=false; else if(vis) play();});
    return api;
  }
  if(step) window.__story={render:function(dt){insts.forEach(function(i){if(i) i.render(dt);});}};
})();
