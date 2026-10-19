/* Full Duplex D2C tracker map. Data: data/tracker.json (single source of truth). */
(function(){
  var box=document.getElementById('fd-map'); if(!box||!window.d3||!window.topojson) return;
  var COL={live:'#6ee79a',trial:'#f5c26b',announced:'#7f93a8'}, NONE='#1f2c44', RANK={live:3,trial:2,announced:1};
  var tip=document.getElementById('fd-map-tip'), multi=document.getElementById('fd-map-multi');
  function esc(t){var d=document.createElement('div');d.innerHTML=t;return d.textContent;}
  function el(tag,cls,txt){var e=document.createElement(tag);if(cls)e.className=cls;if(txt!=null)e.textContent=txt;return e;}
  Promise.all([fetch('data/tracker.json').then(function(r){return r.json()}),fetch('assets/vendor/countries-110m.json').then(function(r){return r.json()})]).then(function(res){
    var data=res[0], world=res[1], by={}, others=[];
    data.rows.forEach(function(r){ if(r.iso_n3){(by[r.iso_n3]=by[r.iso_n3]||[]).push(r);} else others.push(r); });
    var W=960,H=480, proj=d3.geoNaturalEarth1().fitExtent([[4,4],[W-4,H-4]],{type:'Sphere'}), path=d3.geoPath(proj);
    var NS='http://www.w3.org/2000/svg', svg=document.createElementNS(NS,'svg');
    svg.setAttribute('viewBox','0 0 '+W+' '+H); svg.setAttribute('aria-hidden','false');
    var feats=topojson.feature(world,world.objects.countries).features.filter(function(f){return f.id!=='010';});
    var sel=null;
    function show(f,p){
      var rows=by[f.id]; if(sel)sel.classList.remove('sel'); sel=p; p.classList.add('sel');
      tip.innerHTML=''; var c=el('div','card'); c.appendChild(el('strong',null,esc(rows[0].country)));
      var ul=el('ul'); rows.forEach(function(r){var li=el('li');li.appendChild(el('span',null,esc(r.operator)+' + '+esc(r.satellite)+': '));li.appendChild(el('span',r.status==='announced'?'ann':r.status,r.status));li.appendChild(el('span',null,'. '+esc(r.services)));ul.appendChild(li);});
      c.appendChild(ul); tip.appendChild(c);
    }
    feats.forEach(function(f){
      var p=document.createElementNS(NS,'path'); p.setAttribute('d',path(f)||''); p.setAttribute('class','c');
      var rows=by[f.id], best=null;
      if(rows){ rows.forEach(function(r){ if(!best||RANK[r.status]>RANK[best]) best=r.status; });
        p.setAttribute('fill',COL[best]); p.classList.add('has'); p.setAttribute('tabindex','0'); p.setAttribute('role','button');
        p.setAttribute('aria-label',esc(rows[0].country)+': '+best+'. '+rows.map(function(r){return esc(r.operator)+' with '+esc(r.satellite)+', '+r.status}).join('; '));
        p.addEventListener('mouseenter',function(){show(f,p)}); p.addEventListener('click',function(){show(f,p)}); p.addEventListener('focus',function(){show(f,p)});
        p.addEventListener('keydown',function(e){if(e.key==='Enter'||e.key===' '){e.preventDefault();show(f,p);}});
        var t=document.createElementNS(NS,'title'); t.textContent=esc(rows[0].country)+': '+best; p.appendChild(t);
      } else { p.setAttribute('fill',NONE); p.setAttribute('aria-hidden','true'); }
      svg.appendChild(p);
    });
    box.appendChild(svg);
    tip.textContent='Tap or hover a coloured country for details.';
    if(others.length){ multi.appendChild(el('p',null,'Not shown on the map (multi-country or non-country rows):')); var ul=el('ul');
      others.forEach(function(r){var li=el('li');li.appendChild(el('strong',null,esc(r.satellite)));li.appendChild(el('span',null,' ('+esc(r.country)+', '+esc(r.operator)+'): '));li.appendChild(el('span',r.status==='announced'?'ann':r.status,r.status));li.appendChild(el('span',null,'. '+esc(r.services)));ul.appendChild(li);});
      multi.appendChild(ul); }
  }).catch(function(){ tip.textContent='The map could not load. All the data is in the table below.'; });
})();
