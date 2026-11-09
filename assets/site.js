/* Full Duplex site script: lazy beehiiv embeds, iframe titles, sticky subscribe bar. No trackers. */
(function(){
  var LOADER='https://subscribe-forms.beehiiv.com/v3/loader.js';
  // 1. Lazy-load the beehiiv form only when a Signal block nears the viewport (saves ~250 KB up front).
  function load(slot){
    if(slot.getAttribute('data-loaded'))return; slot.setAttribute('data-loaded','1');
    var s=document.createElement('script'); s.async=true; s.src=LOADER; s.setAttribute('data-beehiiv-form',slot.getAttribute('data-form'));
    slot.appendChild(s);
  }
  var slots=[].slice.call(document.querySelectorAll('.bh-slot'));
  if(slots.length){
    if('IntersectionObserver' in window){
      var io=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting){io.unobserve(e.target);load(e.target);}});},{rootMargin:'300px 0px'});
      slots.forEach(function(s){io.observe(s);});
    } else slots.forEach(load);
    // 2. Accessibility: give beehiiv's iframes a title.
    if('MutationObserver' in window){
      new MutationObserver(function(){
        [].forEach.call(document.querySelectorAll('.bh-slot iframe:not([title])'),function(f){f.setAttribute('title','Subscribe to Signal, the Full Duplex newsletter');});
      }).observe(document.body,{childList:true,subtree:true});
    }
  }
  // 3. Mobile sticky subscribe bar: appears after 40% scroll, dismissible, remembered for 30 days.
  var bar=document.querySelector('.stickybar'); if(!bar)return;
  var KEY='fd_bar_dismissed', until=0; try{until=+localStorage.getItem(KEY)||0;}catch(e){}
  if(Date.now()<until)return;
  var shown=false;
  function onScroll(){
    var h=document.documentElement.scrollHeight-innerHeight; var past=h>0&&scrollY/h>0.4;
    if(past&&!shown){bar.hidden=false;shown=true;} else if(!past&&shown&&scrollY/h<0.3){bar.hidden=true;shown=false;}
  }
  addEventListener('scroll',onScroll,{passive:true});
  bar.querySelector('.x').addEventListener('click',function(){bar.hidden=true;removeEventListener('scroll',onScroll);try{localStorage.setItem(KEY,String(Date.now()+30*864e5));}catch(e){}});
})();
