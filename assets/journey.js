/* Full Duplex "What happens when you hit send": plays each scene's CSS animation only while it is on screen.
   Animations are pure CSS/SVG (style.css); reduced-motion users get the still scenes. */
(function(){
  document.documentElement.classList.add('js');
  var sc=[].slice.call(document.querySelectorAll('.scene'));
  if(!('IntersectionObserver' in window)){ sc.forEach(function(s){s.classList.add('in','seen');}); return; }
  var io=new IntersectionObserver(function(es){ es.forEach(function(e){ e.target.classList.toggle('in',e.isIntersecting); if(e.isIntersecting) e.target.classList.add('seen'); }); },{threshold:0.3});
  sc.forEach(function(s){ io.observe(s); });
})();
