/* Tracker 2.0 filters: search, status chips, provider, region, sort. Works on the server-rendered table. */
(function(){
  var table=document.getElementById('tracker-table'); if(!table) return;
  var tbody=table.tBodies[0], rows=[].slice.call(tbody.rows), order=rows.slice();
  var q=document.getElementById('t-q'), prov=document.getElementById('t-prov'), reg=document.getElementById('t-reg'), sort=document.getElementById('t-sort'), count=document.getElementById('t-count');
  var chips=[].slice.call(document.querySelectorAll('.chip')), status='all', RANK={live:0,trial:1,announced:2};
  var params=new URLSearchParams(location.search);
  if(params.get('q')) q.value=params.get('q');
  if(params.get('status')) status=params.get('status');
  if(params.get('provider')) prov.value=params.get('provider');
  if(params.get('region')) reg.value=params.get('region');
  function apply(){
    var term=q.value.trim().toLowerCase(), n=0, p=prov.value, r=reg.value;
    chips.forEach(function(c){ c.setAttribute('aria-pressed', String(c.getAttribute('data-status')===status)); });
    var list=order.slice(), s=sort.value;
    if(s==='country') list.sort(function(a,b){ return a.dataset.country.localeCompare(b.dataset.country); });
    if(s==='checked') list.sort(function(a,b){ return b.dataset.checked.localeCompare(a.dataset.checked); });
    if(s==='status') list.sort(function(a,b){ return RANK[a.dataset.status]-RANK[b.dataset.status]; });
    list.forEach(function(tr){
      var ok=(status==='all'||tr.dataset.status===status)&&(!p||tr.dataset.provider===p)&&(!r||tr.dataset.region===r)&&(!term||tr.textContent.toLowerCase().indexOf(term)>-1);
      tr.hidden=!ok; if(ok) n++; tbody.appendChild(tr);
    });
    count.textContent=n+(n===1?' entry':' entries')+(n===rows.length?'':' of '+rows.length);
    var u=new URLSearchParams(); if(term) u.set('q',q.value.trim()); if(status!=='all') u.set('status',status); if(p) u.set('provider',p); if(r) u.set('region',r);
    history.replaceState(null,'',location.pathname+(u.toString()?'?'+u:'')+location.hash);
  }
  chips.forEach(function(c){ c.addEventListener('click',function(){ status=c.getAttribute('data-status'); apply(); }); });
  [q].forEach(function(e){ e.addEventListener('input',apply); });
  [prov,reg,sort].forEach(function(e){ e.addEventListener('change',apply); });
  apply();
})();
