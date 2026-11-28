/* Deal-card filters on the tracker. All cards are in the HTML. Without JS,
   every card is visible. With JS, the first 9 show until “Show all” or a
   filter, search or sort needs the rest. */
(function(){
  var grid=document.getElementById('deals-grid')||document.querySelector('#deals .deals-grid');
  if(!grid) return;
  var moreBtn=document.getElementById('deals-more-btn');
  var count=document.getElementById('deals-count');
  var statusBtns=[].slice.call(document.querySelectorAll('#deals [data-deal-status]'));
  var provBtns=[].slice.call(document.querySelectorAll('#deals [data-deal-provider]'));
  var q=document.getElementById('t-q');
  var reg=document.getElementById('t-reg');
  var sort=document.getElementById('t-sort');
  var extras=[].slice.call(grid.querySelectorAll('.deal-extra'));
  var status='all', prov='all', expanded=false;
  var order=[].slice.call(grid.querySelectorAll('.deal'));
  var total=order.length;
  var RANK={live:0,trial:1,announced:2};

  var params=new URLSearchParams(location.search);
  if(q && params.get('q')) q.value=params.get('q');
  if(params.get('status')) status=params.get('status');
  if(params.get('provider')) prov=params.get('provider');
  if(reg && params.get('region')) reg.value=params.get('region');

  function needAll(){
    var s=sort && sort.value && sort.value!=='default';
    var term=q && q.value.trim();
    var r=reg && reg.value;
    return status!=='all'||prov!=='all'||!!term||!!r||s;
  }
  function expand(){
    if(expanded) return;
    extras.forEach(function(c){ c.hidden=false; });
    expanded=true;
    if(moreBtn){ moreBtn.setAttribute('aria-expanded','true'); moreBtn.hidden=true; }
  }
  function apply(){
    if(needAll()) expand();
    var term=q?q.value.trim().toLowerCase():'';
    var r=reg?reg.value:'';
    var s=sort?sort.value:'default';
    var cards=order.slice();
    if(s==='country') cards.sort(function(a,b){ return (a.dataset.country||'').localeCompare(b.dataset.country||''); });
    if(s==='checked') cards.sort(function(a,b){ return (b.dataset.checked||'').localeCompare(a.dataset.checked||''); });
    if(s==='status') cards.sort(function(a,b){ return (RANK[a.dataset.status]||9)-(RANK[b.dataset.status]||9); });
    var n=0;
    cards.forEach(function(c){
      var ok=(status==='all'||c.getAttribute('data-status')===status)
        &&(prov==='all'||c.getAttribute('data-provider')===prov)
        &&(!r||c.getAttribute('data-region')===r)
        &&(!term||c.textContent.toLowerCase().indexOf(term)>-1);
      if(!expanded && c.classList.contains('deal-extra')) ok=false;
      c.hidden=!ok; if(ok) n++;
      grid.appendChild(c);
    });
    statusBtns.forEach(function(b){ b.setAttribute('aria-pressed', String(b.getAttribute('data-deal-status')===status)); });
    provBtns.forEach(function(b){ b.setAttribute('aria-pressed', String(b.getAttribute('data-deal-provider')===prov)); });
    if(count){
      count.textContent = (n===total) ? (n+' deal'+(n===1?'':"s")) : (n+' of '+total+' deals');
    }
    var u=new URLSearchParams();
    if(term) u.set('q', q.value.trim());
    if(status!=='all') u.set('status', status);
    if(prov!=='all') u.set('provider', prov);
    if(r) u.set('region', r);
    history.replaceState(null,'',location.pathname+(u.toString()?'?'+u:'')+location.hash);
  }

  if(moreBtn && extras.length){
    moreBtn.hidden=false;
    extras.forEach(function(c){ c.hidden=true; });
    moreBtn.addEventListener('click', function(){ expand(); apply(); });
  }
  statusBtns.forEach(function(b){ b.addEventListener('click', function(){ status=b.getAttribute('data-deal-status'); apply(); }); });
  provBtns.forEach(function(b){ b.addEventListener('click', function(){ prov=b.getAttribute('data-deal-provider'); apply(); }); });
  if(q) q.addEventListener('input', apply);
  if(reg) reg.addEventListener('change', apply);
  if(sort) sort.addEventListener('change', apply);
  apply();
})();
