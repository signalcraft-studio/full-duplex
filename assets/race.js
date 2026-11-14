/* Full Duplex race chart (/launches/): phone-capable satellites in orbit, month by month, from data/race.json
   (every month-end value sourced; bars only tween between them). HTML bars, no libraries. Plays once when it
   scrolls into view; Replay, Zoom and a month slider for control. Under prefers-reduced-motion it stays on today
   unless you press Replay, which then steps month by month without motion effects. */
(function(){
  var sec=document.querySelector('section.race'); if(!sec) return;
  var D; try{D=JSON.parse(sec.getAttribute('data-race'));}catch(e){return;}
  var reduce=window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches;
  var F=D.f, K=D.k, N=F.length, rows={}, plot=sec.querySelector('.race-plot'), dateEl=sec.querySelector('.race-date'), evEl=sec.querySelector('.race-event');
  var tgt=sec.querySelector('.rtarget'), playB=document.getElementById('race-play'), zoomB=document.getElementById('race-zoom'), range=document.getElementById('race-range');
  K.forEach(function(k){ var el=plot.querySelector('[data-id="'+k+'"]'); rows[k]={el:el,bar:el.querySelector('.rbar i'),val:el.querySelector('.rval')}; });
  var MON='Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split(' '), zoom=false, pos=N-1, raf=0, played=false;
  function label(i){ var d=F[i][0].split('-'); return i===N-1?(+d[2])+' '+MON[d[1]-1]+' '+d[0]+' · today':MON[d[1]-1]+' '+d[0]; }
  function render(p){
    p=Math.max(0,Math.min(N-1,+p||0)); pos=p; var i=Math.min(N-1,Math.floor(p)), fr=p-i, j=Math.min(N-1,i+1), v=K.map(function(_,x){ return F[i][1][x]+(F[j][1][x]-F[i][1][x])*fr; });
    var top=zoom?50:Math.max(50,Math.max.apply(null,v)*1.12), cur=fr>0.5?j:i;
    var order=K.map(function(k,x){return x;}).sort(function(a,b){return v[b]-v[a]||a-b;});
    order.forEach(function(x,rank){ var o=rows[K[x]], w=v[x]/top;
      o.el.style.transform='translateY('+(rank*100)+'%)'; o.bar.style.width=(Math.min(1,w)*100).toFixed(2)+'%'; o.bar.classList.toggle('over',w>1);
      o.val.textContent=Math.round(v[x]).toLocaleString('en-GB')+(w>1?' →':''); });
    var pct=Math.min(100,D.t/top*100); tgt.style.left=pct.toFixed(2)+'%'; tgt.classList.toggle('end',pct>58);
    dateEl.textContent=label(cur);
    var d=F[cur][0], ev=null; for(var e=0;e<D.e.length;e++){ if(D.e[e][0]<=d) ev=D.e[e]; }
    var recent=ev&&(new Date(d)-new Date(ev[0]))<120*864e5;
    evEl.textContent=cur===N-1?'Today: working satellites, as counted in the panel below.':recent?(+ev[0].slice(8,10))+' '+MON[ev[0].slice(5,7)-1]+' '+ev[0].slice(0,4)+': '+ev[1]+'.':'';
    range.value=String(cur); range.setAttribute('aria-valuetext',label(cur));
  }
  function stop(){ cancelAnimationFrame(raf); clearTimeout(raf); raf=0; playB.textContent='Replay the race'; }
  function play(){
    stop(); played=true; playB.textContent='Pause';
    if(reduce){ var k=0; (function step(){ render(k); if(k++<N-1) raf=setTimeout(step,600); else stop(); })(); return; }
    var t0=performance.now(), dur=(N-1)*380;
    (function tick(t){ var p=Math.max(0,Math.min(1,(t-t0)/dur))*(N-1); /* rAF's first timestamp can be a hair before t0 */ render(p); if(p<N-1) raf=requestAnimationFrame(tick); else stop(); })(t0);
  }
  playB.addEventListener('click',function(){ if(raf) stop(); else play(); });
  zoomB.addEventListener('click',function(){ zoom=!zoom; zoomB.setAttribute('aria-pressed',String(zoom)); zoomB.textContent=zoom?'Show the full scale':'Zoom in on the smaller networks'; render(pos); });
  range.addEventListener('input',function(){ stop(); render(+range.value); });
  render(N-1);
  if(!reduce&&'IntersectionObserver' in window){
    var io=new IntersectionObserver(function(es){ if(es[0].isIntersecting&&!played){ io.disconnect(); render(0); setTimeout(play,400); } },{threshold:0.5});
    io.observe(plot);
  }
})();
