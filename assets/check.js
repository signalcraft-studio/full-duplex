/* "Can my phone connect?" (/check/). Runs entirely in the browser from data embedded at build time
   (data/tracker.json + src/phones.json). No IMEI, no network requests, nothing stored. */
(function(){
  var el=document.getElementById('chk-data'), out=document.getElementById('chk-out'), form=document.getElementById('chk');
  if(!el||!out||!form)return;
  var D=JSON.parse(el.textContent), P=D.phones, M={}, MB={};
  P.models.forEach(function(m){M[m[0]]=m[1];MB[m[0]]=m[2];});
  var MON='Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split(' ');
  function hd(iso){var a=iso.split('-');return +a[2]+' '+MON[+a[1]-1]+' '+a[0];}
  function e(t){return String(t).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
  function a(l,u){return '<a href="'+e(u)+'">'+e(l)+'</a>';}
  var LAB={live:'Live',trial:'Trial',announced:'Announced'}, CL={live:'live',trial:'trial',announced:'ann'};
  var sC=form.querySelector('[name=c]'), sO=form.querySelector('[name=o]'), sP=form.querySelector('[name=p]');
  function srcs(r){return 'Source: '+r.src.map(function(s){return a(s[0],s[1]);}).join(' · ')+' · checked '+e(r.chk);}
  function headline(r){
    if(r.st==='live')return 'Yes. '+r.o+' has satellite-to-phone live, using '+r.sat+'.';
    if(r.st==='trial')return 'Not yet. '+r.o+' is trialling satellite-to-phone with '+r.sat+'. It isn’t open to everyone.';
    return 'Not yet. '+r.o+' has announced a deal with '+r.sat+', with no launch confirmed in our source.';
  }
  function short(r){return r.st==='live'?'live':r.st==='trial'?'on trial':'announced';}
  function phoneFor(r,p,cname){
    // returns {k:'yes'|'part'|'no'|'unk', t:text, s:[label,url]}
    var L=P.lists[r.c+'|'+r.o], src=L?(L.url?[L.label,L.url]:[L.label,r.src[0][1]]):[r.o+': '+r.src[0][0],r.src[0][1]];
    if(r.st!=='live')return {k:'unk',t:'This service isn’t open to the public yet, so there’s no official phone list to check against. Check with your network.',s:null};
    if(MB[p]==='Apple'&&P.apple_carrier.no.indexOf(p)>=0)return {k:'no',t:P.apple_carrier.rule,s:[P.apple_carrier.label,P.apple_carrier.url]};
    if(p==='unsure'||p==='other'){return {k:'unk',t:(L?'Check your exact model on '+L.label+'.':'Check with '+r.o+'. We don’t have an official phone list for it yet.'),s:src};}
    if(L){
      var when=' (checked '+hd(L.checked)+')';
      if(L.yes&&L.yes[p])return {k:'yes',t:'Yes, your phone is on '+L.label+when+(L.yes[p]==='Listed'?'.':': '+L.yes[p]+'.')+(L.extra?' '+L.extra:''),s:src};
      if(L.part&&L.part[p])return {k:'part',t:'Partly: '+L.part[p]+'.'+(L.extra?' '+L.extra:''),s:src};
      if(L.only)return {k:'no',t:L.no_text,s:src};
      return {k:'unk',t:'We couldn’t find your phone on '+L.label+when+'. Check with '+r.o+' before you pay for anything.',s:src};
    }
    return {k:'unk',t:'We don’t have an official phone list for '+r.o+' yet, so check with your network. Their page:',s:src};
  }
  var ICON={yes:'✓',part:'◐',no:'✕',unk:'?'}, KCL={yes:'yes',part:'part',no:'no',unk:'unk'};
  function phoneHtml(x){return '<div class="ck-phone k-'+KCL[x.k]+'"><span class=ck-i aria-hidden=true>'+ICON[x.k]+'</span><p>'+e(x.t)+(x.s?' '+a(x.s[0],x.s[1]):'')+'</p></div>';}
  function extras(p,cname){
    var h='';
    [['apple_sos'],['pixel_sos']].forEach(function(k){var X=P[k[0]];
      if(X.models.indexOf(p)>=0&&(cname==='*'||X.countries.indexOf(cname)>=0))
        h+='<li>'+e(X.text.replace('{country}',cname==='*'?'supported countries':(cname==='United Kingdom'||cname==='United States'?'the ':'')+cname))+(X.caveat?' '+e(X.caveat):'')+' '+a(X.label,X.url)+'</li>';});
    return h?'<div class=ck-extra><h3>Also on your phone</h3><ul>'+h+'</ul></div>':'';
  }
  function howto(p,rows){
    var want={iphone:!p||MB[p]==='Apple'||MB[p]==='Other',pixel:!p||MB[p]==='Google'||MB[p]==='Samsung'||MB[p]==='Other',tmo:rows.some(function(r){return r.o==='T-Mobile';})};
    var h=P.howto.filter(function(x){return want[x.id];}).map(function(x){return '<div><h4>'+e(x.h)+'</h4><ol>'+x.steps.map(function(s){return '<li>'+e(s)+'</li>';}).join('')+'</ol><p class=gl-src>Source: '+a(x.src[0],x.src[1])+'</p></div>';}).join('');
    return h?'<details class=ck-how><summary>How to check on your phone</summary><div class=ck-how-g>'+h+'</div></details>':'';
  }
  function card(r,p){
    return '<article class="ck-row s-'+CL[r.st]+'"><div class=ck-row-h><h3>'+e(r.o)+' <span class=plus>+</span> '+e(r.sat)+'</h3><span class="spill s-'+CL[r.st]+'">'+LAB[r.st]+'</span></div>'+
      '<p>'+e(r.sv)+'</p>'+(p?phoneHtml(phoneFor(r,p)):'')+'<p class=meta>'+srcs(r)+'</p></article>';
  }
  /* Signal follow-up on every answer (UAT 14 Nov 2026): one link to beehiiv's hosted sign-up, tagged by country and network */
  function sig(op,the,c){
    var h=op?'Get told when '+op+' changes':(c==='other'?'Get told when satellite-to-phone reaches you':'Get told when anything changes in '+the);
    var u=D.sub+'&utm_content='+encodeURIComponent((c||'none')+(op?'-'+op.toLowerCase().replace(/[^a-z0-9]+/g,'-'):''));
    return '<div class=ck-signal><div><p class=ck-sig-h>'+e(h)+'</p><p class=ck-sig-p>Signal is free, one email a week: new launches, trials and status changes, with the sources.</p></div>'+
      '<a class="btn signal-btn" href="'+e(u)+'">Get Signal free <span aria-hidden=true>→</span></a></div>';
  }
  function render(c,o,p,push){
    var rows=D.rows.filter(function(r){return r.cs===c;}), multi=D.rows.filter(function(r){return !r.cs;});
    var cname=rows.length?rows[0].c:'', the=(cname==='United Kingdom'||cname==='United States'||cname==='Philippines')?'the '+cname:cname;
    /* rows that group networks ("SoftBank; NTT docomo") carry on:{slug:name}; show only the picked network's name */
    var sel=o&&o!=='other'?rows.filter(function(r){return r.os===o||(r.on&&r.on[o]);}).map(function(r){if(!r.on||!r.on[o])return r;var x={};for(var k in r)x[k]=r[k];x.o=r.on[o];return x;}):[];
    var h, list, tw;
    if(!c)return;
    if(c==='other'){
      h='We don’t track a satellite-to-phone service there yet.'; list=''; tw='Satellite-to-phone isn’t in the tracker for my country yet.';
    } else if(sel.length){
      h=headline(sel[0]); list=sel.map(function(r){return card(r,p);}).join('');
      if(p&&sel[0].st==='live'){var v=phoneFor(sel[0],p).k;
        if(v==='yes')h='Yes. '+sel[0].o+' has satellite-to-phone live with '+sel[0].sat+', and your phone is on the list.';
        else if(v==='part')h='Partly. '+sel[0].o+' has satellite-to-phone live with '+sel[0].sat+', but your phone only gets some of it.';
        else if(v==='no')h='Not on your phone. '+sel[0].o+' has satellite-to-phone live with '+sel[0].sat+', but your phone isn’t supported.';
        else h=sel[0].o+' has satellite-to-phone live with '+sel[0].sat+'. Check your phone with them first.';}
      var others=rows.filter(function(r){return !sel.some(function(s){return s.os===r.os;});});
      if(others.length)list+='<p class=ck-also>Also in '+e(the)+': '+others.map(function(r){return e(r.o)+' ('+short(r)+')';}).join(', ')+'.</p>';
      tw=sel[0].o+' satellite-to-phone in '+the+': '+short(sel[0])+(p&&M[p]?' (I checked my '+M[p]+')':'')+'.';
    } else {
      var nl=rows.filter(function(r){return r.st==='live';}).length;
      h=(o==='other'?'Your network isn’t one we track in '+the+'. ':'')+(nl?'Satellite-to-phone is live in '+the+' on '+nl+' network'+(nl>1?'s':'')+'.':'Nothing is live in '+the+' yet.');
      list=rows.map(function(r){return card(r,p);}).join(''); tw='Satellite-to-phone in '+the+': '+(nl?nl+' network'+(nl>1?'s':'')+' live':'nothing live yet')+'.';
    }
    var mu='<p class=ck-also>Multi-country services we track: '+multi.map(function(r){return e(r.sat)+' ('+e(r.c)+', '+short(r)+')';}).join('; ')+'. See the <a href="../tracker.html">tracker</a>.</p>';
    var q='?c='+encodeURIComponent(c)+(o?'&o='+encodeURIComponent(o):'')+(p?'&p='+encodeURIComponent(p):''), url=D.base+'check/'+q;
    if(push&&history.replaceState)history.replaceState(null,'',q);
    var share='https://x.com/intent/post?text='+encodeURIComponent(tw+' Check yours:')+'&url='+encodeURIComponent(url)+'&via=FullDuplexHQ';
    out.innerHTML='<section class="card ck-result" aria-labelledby=ck-ans><p class=kicker>Your answer · tracker checked '+e(D.checked)+'</p><h2 id=ck-ans tabindex=-1>'+e(h)+'</h2>'+
      (p&&M[p]?'<p class=ck-for>For: '+e(M[p])+'</p>':'')+list+sig(sel.length?sel[0].o:'',the,c)+(p?extras(p,cname||'*'):'')+howto(p,sel.length?sel:rows)+mu+
      '<div class=ck-share><a class="btn ghost" href="'+e(share)+'" target=_blank rel=noopener>Share on X</a><button type=button class="btn ghost" id=ck-copy>Copy link</button><span id=ck-copied class=ck-copied role=status></span></div>'+
      '<p class=fine>Status is what the source said on the date checked. Phone lists change: always confirm with your network before you pay.</p></section>';
    var cp=document.getElementById('ck-copy');
    cp.addEventListener('click',function(){var done=function(){document.getElementById('ck-copied').textContent='Link copied';};
      if(navigator.clipboard)navigator.clipboard.writeText(url).then(done,function(){prompt('Copy this link',url);}); else prompt('Copy this link',url);});
    if(push){var a2=document.getElementById('ck-ans');a2.focus({preventScroll:true});a2.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'start'});}
  }
  form.addEventListener('submit',function(ev){ev.preventDefault();if(!sC.value){sC.focus();return;}render(sC.value,sO.value,sP.value,true);});
  var u=new URLSearchParams(location.search), c=u.get('c')||'', o=u.get('o')||'', p=u.get('p')||'';
  if(c){sC.value=c; sC.dispatchEvent(new Event('change')); if(o)sO.value=o; if(p&&M[p])sP.value=p; render(sC.value,sO.value,sP.value,false);}
})();
