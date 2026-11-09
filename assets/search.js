/* Static site search over search-index.json (built by scripts/build.py). No third parties. */
(function(){
  var input=document.getElementById('q'), out=document.getElementById('s-results'), status=document.getElementById('s-status'); if(!input) return;
  var idx=null;
  function esc(t){ return String(t).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];}); }
  function snippet(text,terms){
    var lo=text.toLowerCase(), i=-1; terms.some(function(t){ i=lo.indexOf(t); return i>-1; });
    var s=Math.max(0,i-80), frag=(s?'…':'')+text.slice(s,s+220)+'…', h=esc(frag);
    terms.forEach(function(t){ if(t.length>1) h=h.replace(new RegExp('('+t.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+')','ig'),'<mark>$1</mark>'); });
    return h;
  }
  function run(){
    var raw=input.value.trim(), terms=raw.toLowerCase().split(/\s+/).filter(Boolean);
    history.replaceState(null,'',location.pathname+(raw?'?q='+encodeURIComponent(raw):''));
    if(!terms.length){ out.innerHTML=''; status.textContent=''; return; }
    var res=idx.map(function(d){
      var t=d.t.toLowerCase(), de=d.d.toLowerCase(), x=d.x.toLowerCase(), score=0;
      for(var i=0;i<terms.length;i++){ var w=terms[i], s=(t.indexOf(w)>-1?10:0)+(de.indexOf(w)>-1?4:0)+(x.indexOf(w)>-1?1+Math.min(5,x.split(w).length-1)*.2:0); if(!s) return null; score+=s; }
      return {d:d,s:score};
    }).filter(Boolean).sort(function(a,b){ return b.s-a.s; }).slice(0,20);
    status.textContent=res.length?res.length+' result'+(res.length>1?'s':'')+' for “'+raw+'”':'No results for “'+raw+'”. Try a country, operator or satellite company.';
    out.innerHTML=res.map(function(r){ return '<li><a href="'+esc(r.d.u)+'">'+esc(r.d.t)+'</a><p>'+snippet(r.d.x,terms)+'</p></li>'; }).join('');
  }
  fetch('search-index.json').then(function(r){return r.json()}).then(function(d){
    idx=d; var q=new URLSearchParams(location.search).get('q'); if(q) input.value=q; run();
    input.addEventListener('input',run);
    input.form.addEventListener('submit',function(e){ e.preventDefault(); run(); });
  }).catch(function(){ status.textContent='Search could not load. Browse the articles or the tracker instead.'; });
})();
