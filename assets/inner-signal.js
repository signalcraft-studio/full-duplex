/* Inner Signal (preview): scroll position drives the Call Pod along each chapter's route. No libraries.
   Without JS, or with prefers-reduced-motion, every pod sits at its destination and everything is visible. */
(function(){
  var d=document, root=d.documentElement; root.classList.add('js');
  var reduce=window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches;
  var chs=[].slice.call(d.querySelectorAll('.ch')), rail=d.getElementById('rail');
  var hdr=d.querySelector('header.site');
  function hh(){root.style.setProperty('--hh',(hdr?hdr.offsetHeight:60)+'px');}
  hh(); addEventListener('resize',hh);

  /* toggles */
  function setReal(b,on){
    var p=d.getElementById(b.getAttribute('aria-controls')); if(!p)return;
    p.classList.toggle('open',on); b.setAttribute('aria-expanded',on?'true':'false');
    b.textContent=on?'Hide the real thing':'Show me the real thing';
  }
  var btns=[].slice.call(d.querySelectorAll('.real-b'));
  btns.forEach(function(b){b.addEventListener('click',function(){setReal(b,b.getAttribute('aria-expanded')!=='true');});});
  var all=d.getElementById('all-real');
  if(all)all.addEventListener('click',function(){
    var on=all.getAttribute('aria-pressed')!=='true'; all.setAttribute('aria-pressed',on?'true':'false');
    all.textContent=on?'Hide the real thing, everywhere':'Show me the real thing, everywhere';
    btns.forEach(function(b){setReal(b,on);});
  });
  [].forEach.call(d.querySelectorAll('.egg-b'),function(b){b.addEventListener('click',function(){b.parentNode.classList.toggle('open');});});
  d.addEventListener('keydown',function(e){if(e.key==='Escape')[].forEach.call(d.querySelectorAll('.egg.open'),function(x){x.classList.remove('open');});});

  /* pods */
  var strips=chs.map(function(c){return c.querySelector('.strip');});
  function visSvg(s){var a=s.querySelector('.sv-h'),b=s.querySelector('.sv-v');return (a&&a.offsetParent!==null)?a:b;}
  var cache=[];
  function pod(i,p){
    var s=strips[i], svg=visSvg(s); if(!svg)return;
    var c=cache[i]; if(!c||c.svg!==svg){var r=svg.querySelector('.route');c={svg:svg,r:r,g:svg.querySelector('.pod'),len:r.getTotalLength()};cache[i]=c;}
    var pt=c.r.getPointAtLength(c.len*p); c.g.setAttribute('transform','translate('+pt.x.toFixed(1)+' '+pt.y.toFixed(1)+')');
  }
  var meter=d.querySelector('[data-meter]'), mT=null, mStart=0;
  function fmt(t){t=Math.round(t);return Math.floor(t/60)+':'+('0'+t%60).slice(-2);}
  function meterRun(on){
    if(!meter||reduce)return;
    if(on&&!mT){mStart=Date.now();mT=setInterval(function(){var t=Math.min(252,(Date.now()-mStart)/1000*21);meter.textContent=fmt(t);if(t>=252){clearInterval(mT);mT=null;}},100);}
    if(!on&&mT){clearInterval(mT);mT=null;}
    if(!on&&!reduce)meter.textContent='0:00';
  }
  var cur=0, ticking=false, shown=false;
  function frame(){
    ticking=false;
    var vh=innerHeight, n=0, frac=0, i;
    for(i=0;i<chs.length;i++){
      var r=chs[i].getBoundingClientRect(), on=r.bottom>0&&r.top<vh;
      if(r.bottom>-vh&&r.top<vh*2){
        var sr=strips[i].getBoundingClientRect(), mid=sr.top+sr.height/2;
        var p=reduce?1:Math.max(0,Math.min(1,(vh*0.92-mid)/(vh*0.5)));
        strips[i].style.setProperty('--p',p.toFixed(3)); pod(i,p);
        var art=chs[i].querySelector('.art'); if(art&&!reduce){var ar=art.getBoundingClientRect();art.style.setProperty('--ap',Math.max(0,Math.min(1,(vh-ar.top)/(vh+ar.height))).toFixed(3));}
      }
      if(on){chs[i].classList.add('in','seen');}else chs[i].classList.remove('in');
      if(r.top<vh*0.4){n=i;frac=Math.max(0,Math.min(1,(vh*0.4-r.top)/r.height));}
      if(chs[i].id==='ch-12')meterRun(on&&r.top<vh*0.6);
    }
    if(rail){
      var f=chs[0].getBoundingClientRect(), l=chs[chs.length-1].getBoundingClientRect();
      rail.style.top=(hdr&&!hdr.classList.contains('hdr-hide'))?'':'0px';
      var show=f.top<vh*0.5&&l.bottom>vh*0.35; rail.classList.toggle('on',show); rail.setAttribute('aria-hidden',show?'false':'true');
      rail.style.setProperty('--rp',Math.min(1,(n+frac)/chs.length).toFixed(3));
      if(n!==cur||!shown){cur=n;shown=true;var c=chs[n];
        d.getElementById('rail-n').textContent=n+1;d.getElementById('rail-title').textContent=c.getAttribute('data-title');d.getElementById('rail-zone').textContent=c.getAttribute('data-zone');}
    }
  }
  function req(){if(!ticking){ticking=true;requestAnimationFrame(frame);}}
  addEventListener('scroll',req,{passive:true}); addEventListener('resize',function(){cache=[];req();});
  if(reduce){chs.forEach(function(c){c.classList.add('seen');});}
  frame();
})();
