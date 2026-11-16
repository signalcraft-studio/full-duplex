/* Full Duplex share buttons (preview). "Post to X" is a plain x.com link: no X scripts, no tracking.
   "Save image" downloads the pre-rendered card (share/<slug>/card.jpg), or the live globe with a small Full Duplex watermark. */
(function(){
  var NAVY='#070b14', CYAN='#00cfff';
  function mark(g,x,y,s){ // logo A, simplified: two arcs and a dot
    g.save(); g.lineWidth=s*0.12; g.lineCap='round';
    g.strokeStyle=CYAN; g.beginPath(); g.arc(x,y,s*0.42,Math.PI*0.92,Math.PI*1.72); g.stroke();
    g.strokeStyle='#fff'; g.beginPath(); g.arc(x,y,s*0.42,Math.PI*1.92,Math.PI*2.72); g.stroke();
    g.fillStyle=CYAN; g.beginPath(); g.arc(x,y,s*0.11,0,Math.PI*2); g.fill(); g.restore();
  }
  function stamp(src){
    var w=src.width, h=src.height, bar=Math.round(Math.max(44,w*0.07)), c=document.createElement('canvas');
    c.width=w; c.height=h+bar; var g=c.getContext('2d');
    g.fillStyle=NAVY; g.fillRect(0,0,c.width,c.height); g.drawImage(src,0,0);
    var f=Math.round(bar*0.36); mark(g,bar*0.55,h+bar/2,bar*0.62);
    g.textBaseline='middle'; g.font='700 '+f+'px system-ui,sans-serif'; g.fillStyle='#fff'; g.fillText('Full',bar,h+bar/2);
    var fw=g.measureText('Full').width; g.fillStyle=CYAN; g.fillText('Duplex',bar+fw,h+bar/2);
    g.font='500 '+Math.round(f*0.8)+'px system-ui,sans-serif'; g.fillStyle='#9fb0c8'; g.textAlign='right'; g.fillText('@FullDuplexHQ',w-bar*0.4,h+bar/2);
    return c;
  }
  document.addEventListener('click',function(e){
    var a=e.target.closest&&e.target.closest('a.shr-save[data-canvas]'); if(!a) return;
    var cv=document.querySelector(a.getAttribute('data-canvas'));
    if(!cv||!cv.width||!cv.toBlob){ if(a.getAttribute('href')==='#') e.preventDefault(); return; } // no live globe yet: the link's pre-rendered card downloads instead
    e.preventDefault();
    try{ stamp(cv).toBlob(function(b){ if(!b) return; var u=URL.createObjectURL(b), t=document.createElement('a');
      t.href=u; t.download=(a.getAttribute('download')||'full-duplex.png').replace(/\.jpe?g$/,'.png'); document.body.appendChild(t); t.click(); t.remove(); setTimeout(function(){URL.revokeObjectURL(u);},5000); },'image/png'); }catch(err){}
  });
  // Canvas-only "Save image" links (no pre-rendered card) show once the globe has drawn.
  [].forEach.call(document.querySelectorAll('a.shr-save[data-canvas][hidden]'),function(a){
    var n=0, iv=setInterval(function(){ var cv=document.querySelector(a.getAttribute('data-canvas')); if(cv&&cv.width){ a.hidden=false; clearInterval(iv); } else if(++n>60) clearInterval(iv); },1000);
  });
  // Flight view: keep "Post to X" and "Save image" on the launch that's showing.
  var fs=document.getElementById('fl-share'), fd=document.getElementById('fl-data');
  if(fs&&fd){
    var D={}; try{ JSON.parse(fd.textContent).l.forEach(function(l){ D[l.s]=l; }); }catch(e){}
    var base=new URL('../../',location.href).href, x=fs.querySelector('.shr-x'), sv=fs.querySelector('.shr-save');
    var site=(x.getAttribute('href').match(/[?&]url=([^&]+)/)||[])[1]; site=site?decodeURIComponent(site).replace(/share\/[^/]+\/$/,''):'';
    function set(L){ if(!L||!L.sh||!site) return;
      x.href='https://x.com/intent/post?'+['text='+encodeURIComponent(L.x),'url='+encodeURIComponent(site+'share/'+L.sh+'/'),'via=FullDuplexHQ'].join('&');
      if(sv){ sv.hidden=!L.pg; sv.href=L.pg?base+'share/'+L.sh+'/card.jpg':'#'; sv.setAttribute('download','full-duplex-'+L.sh+'.jpg'); } }
    document.addEventListener('fd:flight',function(e){ set(e.detail); });
    var sel=document.getElementById('fl-sel'); if(sel) set(D[sel.value]);
  }
  // Arriving from a shared link: once the page has laid out (filters, globes), bring the shared item back into view.
  if(location.hash.length>1&&/[?&]utm_medium=share/.test(location.search)){
    var t=document.getElementById(decodeURIComponent(location.hash.slice(1)));
    if(t){ var box=t.closest('article,section')||t; setTimeout(function(){ t.scrollIntoView({block:'start'}); box.classList.add('shr-hit'); setTimeout(function(){box.classList.remove('shr-hit');},2600); },400); }
  }
})();
