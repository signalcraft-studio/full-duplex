/* Deal-card filters on the tracker. Progressive enhancement: every card is in the HTML and visible without JS. */
(function(){
  var grid=document.querySelector('#deals .deals-grid'); if(!grid) return;
  var cards=[].slice.call(grid.querySelectorAll('.deal'));
  var count=document.getElementById('deals-count');
  var statusBtns=[].slice.call(document.querySelectorAll('#deals [data-deal-status]'));
  var provBtns=[].slice.call(document.querySelectorAll('#deals [data-deal-provider]'));
  var status='all', prov='all';
  function apply(){
    var n=0;
    cards.forEach(function(c){
      var ok=(status==='all'||c.getAttribute('data-status')===status)&&(prov==='all'||c.getAttribute('data-provider')===prov);
      c.hidden=!ok; if(ok) n++;
    });
    statusBtns.forEach(function(b){ b.setAttribute('aria-pressed', String(b.getAttribute('data-deal-status')===status)); });
    provBtns.forEach(function(b){ b.setAttribute('aria-pressed', String(b.getAttribute('data-deal-provider')===prov)); });
    if(count){
      var total=cards.length;
      count.textContent=n+' deal'+(n===1?'':'s')+(n===total?'':' of '+total);
    }
  }
  statusBtns.forEach(function(b){ b.addEventListener('click', function(){ status=b.getAttribute('data-deal-status'); apply(); }); });
  provBtns.forEach(function(b){ b.addEventListener('click', function(){ prov=b.getAttribute('data-deal-provider'); apply(); }); });
})();
