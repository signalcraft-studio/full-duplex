/* Deal-card filters on the tracker. First 9 cards are in the initial HTML. The rest
   load from assets/deals-more.html when “Show all” or a filter is used. Without JS,
   a noscript link points at the country table. */
(function(){
  var grid=document.getElementById('deals-grid')||document.querySelector('#deals .deals-grid');
  if(!grid) return;
  var moreBtn=document.getElementById('deals-more-btn');
  var count=document.getElementById('deals-count');
  var statusBtns=[].slice.call(document.querySelectorAll('#deals [data-deal-status]'));
  var provBtns=[].slice.call(document.querySelectorAll('#deals [data-deal-provider]'));
  var status='all', prov='all', expanded=false, loading=null;
  var initial=grid.querySelectorAll('.deal').length;
  var total=initial;
  if(moreBtn&&moreBtn.getAttribute('data-src')){
    var m=/Show all (\d+)/.exec(moreBtn.textContent||'');
    if(m) total=parseInt(m[1],10);
  }

  function apply(){
    var n=0, list=[].slice.call(grid.querySelectorAll('.deal'));
    list.forEach(function(c){
      var ok=(status==='all'||c.getAttribute('data-status')===status)&&(prov==='all'||c.getAttribute('data-provider')===prov);
      c.hidden=!ok; if(ok) n++;
    });
    statusBtns.forEach(function(b){ b.setAttribute('aria-pressed', String(b.getAttribute('data-deal-status')===status)); });
    provBtns.forEach(function(b){ b.setAttribute('aria-pressed', String(b.getAttribute('data-deal-provider')===prov)); });
    if(count){
      count.textContent=n+' deal'+(n===1?'':'s')+(n===total?'':' of '+total);
    }
  }
  function stamp(then){
    if(expanded){ if(then) then(); return; }
    var src=moreBtn&&moreBtn.getAttribute('data-src');
    if(!src){ expanded=true; if(then) then(); return; }
    if(loading){ loading.then(then); return; }
    loading=fetch(src).then(function(r){ if(!r.ok) throw new Error('deals-more'); return r.text(); }).then(function(html){
      grid.insertAdjacentHTML('beforeend', html);
      expanded=true;
      if(moreBtn){ moreBtn.setAttribute('aria-expanded','true'); moreBtn.hidden=true; }
    }).catch(function(){
      if(count) count.textContent='Couldn’t load the rest of the deals. See the country table below.';
    }).then(function(){ if(then) then(); });
  }
  function needAll(){ return status!=='all'||prov!=='all'; }
  if(moreBtn){
    moreBtn.hidden=false;
    moreBtn.addEventListener('click', function(){ stamp(apply); });
  }
  statusBtns.forEach(function(b){ b.addEventListener('click', function(){ status=b.getAttribute('data-deal-status'); if(needAll()) stamp(apply); else apply(); }); });
  provBtns.forEach(function(b){ b.addEventListener('click', function(){ prov=b.getAttribute('data-deal-provider'); if(needAll()) stamp(apply); else apply(); }); });
})();
