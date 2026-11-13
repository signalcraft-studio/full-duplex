/* Welcome concepts B, C and D for review (?welcome=b|c|d). Same shell as concept A in assets/site.js.
   Every element's resting style is its final frame, so with animations off (reduced motion) you get a finished still. */
(function(){
  var css=[
  /* shared */
  '.welcome[class*=" v-"] .wl-art text{font-family:"Inter Tight",system-ui,sans-serif}',
  /* B: full duplex chat */
  '.v-b .wb-lane{stroke-dasharray:230;animation:wb-draw .6s .1s ease-out backwards}',
  '@keyframes wb-draw{from{stroke-dashoffset:230}}',
  '.v-b .wb-up,.v-b .wb-dn{transform-box:fill-box}',
  '.v-b .wb-up{transform-origin:0 100%;animation:wb-up 1.5s .5s cubic-bezier(.45,.05,.3,1) backwards}',
  '.v-b .wb-dn{transform-origin:100% 0;animation:wb-dn 1.5s .5s cubic-bezier(.45,.05,.3,1) backwards}',
  '@keyframes wb-up{from{transform:translate(-84px,60px) scale(.45);opacity:0}12%{opacity:1}}',
  '@keyframes wb-dn{from{transform:translate(96px,-40px) scale(.45);opacity:0}12%{opacity:1}}',
  '.v-b .wb-ping circle{transform-box:fill-box;transform-origin:center;opacity:0;animation:wb-ping .9s 1.95s ease-out}',
  '@keyframes wb-ping{0%{opacity:.9;transform:scale(.4)}100%{opacity:0;transform:scale(1.35)}}',
  '.v-b .wb-tag{animation:wb-fade .4s 2.0s ease-out backwards}',
  '@keyframes wb-fade{from{opacity:0;transform:translateY(3px)}}',
  /* C: no service to signal */
  '.v-c .wc-sat{animation:wc-pass 1.7s .15s cubic-bezier(.3,.1,.3,1) backwards}',
  '@keyframes wc-pass{from{transform:translate(-140px,14px)}}',
  '.v-c .wc-beam{opacity:.22;animation:wc-beam .5s 1.55s ease-out backwards}',
  '@keyframes wc-beam{from{opacity:0}}',
  '.v-c .wc-ns{opacity:0;animation:wc-out .25s 1.6s ease-in backwards}',
  '@keyframes wc-out{from{opacity:1}}',
  '.v-c .wc-sig{animation:wb-fade .3s 1.8s ease-out backwards}',
  '.v-c .wc-bar{animation:wc-bar .2s ease-out backwards}',
  '.v-c .wc-bar:nth-of-type(1){animation-delay:1.85s}.v-c .wc-bar:nth-of-type(2){animation-delay:2s}.v-c .wc-bar:nth-of-type(3){animation-delay:2.15s}.v-c .wc-bar:nth-of-type(4){animation-delay:2.3s}',
  '@keyframes wc-bar{from{opacity:0}}',
  '.v-c .wc-note{animation:wc-note .45s 2.4s cubic-bezier(.2,.8,.3,1.2) backwards}',
  '@keyframes wc-note{from{transform:translateY(-26px);opacity:0}}',
  /* D: constellation becomes logo A */
  '.v-d .wd-dot{opacity:0;animation:wd-fly 1.25s var(--dl,.2s) cubic-bezier(.2,.7,.2,1) both,wd-out .45s 2.15s ease-in forwards}',
  '@keyframes wd-fly{0%{transform:translate(var(--x0),var(--y0));opacity:0}12%{opacity:1}100%{transform:none;opacity:1}}',
  '@keyframes wd-out{from{opacity:1}to{opacity:0}}',
  '.v-d .wd-arc{stroke-dasharray:var(--len);animation:wd-draw .6s 1.75s ease-out backwards}',
  '@keyframes wd-draw{from{stroke-dashoffset:var(--len)}}',
  '.v-d .wd-glyph{transform-box:fill-box;transform-origin:center;animation:wd-pop .45s 2.05s cubic-bezier(.2,.8,.3,1.3) backwards}',
  '@keyframes wd-pop{from{opacity:0;transform:scale(.6)}}',
  '.v-d .wd-orbit{animation:wc-beam 1s .1s ease-out backwards}'
  ].join('');
  var st=document.createElement('style'); st.textContent=css; document.head.appendChild(st);
  var stars='<g fill="#9fb0c3"><circle cx=30 cy=24 r=1.1 /><circle cx=112 cy=12 r=.9 /><circle cx=200 cy=20 r=1.2 /><circle cx=300 cy=70 r=1 /><circle cx=150 cy=86 r=.8 /><circle cx=86 cy=56 r=1 /><circle cx=238 cy=94 r=.9 /></g>';
  var sat='<rect x=-28 y=-5 width=18 height=10 fill="#1d3a66" stroke="#5ec8ff" stroke-width=1 /><rect x=10 y=-5 width=18 height=10 fill="#1d3a66" stroke="#5ec8ff" stroke-width=1 /><rect x=-8 y=-8 width=16 height=16 rx=2 fill="#e8eef7"/><circle cx=0 cy=0 r=3 fill="#00cfff"/>';
  var phone='<rect x=-9 y=-17 width=18 height=32 rx=4 fill="#0f1626" stroke="#e8eef7" stroke-width=1.6 /><rect x=-6 y=-13 width=12 height=21 rx=1.5 fill="#5ec8ff" opacity=".35"/>';
  function bubble(cls,x,y,fill,text,tail){
    return '<g transform="translate('+x+' '+y+')"><g class='+cls+'><rect width=98 height=22 rx=11 fill="'+fill+'"/>'+
      (tail==='bl'?'<path d="M10 20l-6 8 14-7z" fill="'+fill+'"/>':'<path d="M88 2l6-8-14 7z" fill="'+fill+'"/>')+
      '<text x=49 y=15 text-anchor=middle font-size=10 font-weight=600 fill="#06101c">'+text+'</text></g></g>';
  }
  window.FDW={
    b:{cls:'v-b',k:'Sending and receiving, at once',wt:'2.3s',art:'<svg class=wl-art viewBox="0 0 320 150" aria-hidden=true focusable=false>'+stars+
      '<path d="M0 140C80 118 240 118 320 140V150H0z" fill="#16243d"/>'+
      '<path class=wb-lane d="M58 88L238 32" stroke="#5ec8ff" stroke-width=1.2 opacity=".45" stroke-dasharray="230"/>'+
      '<path class=wb-lane d="M250 48L62 106" stroke="#6ee79a" stroke-width=1.2 opacity=".45"/>'+
      '<g transform="translate(46 104)">'+phone+'</g><g transform="translate(256 38) rotate(-12)">'+sat+'</g>'+
      bubble('wb-up',120,8,'#5ec8ff','Hello, space?','bl')+bubble('wb-dn',64,92,'#6ee79a','Hello, Earth!','tr')+
      '<g class=wb-ping fill=none stroke-width=1.6><circle cx=46 cy=102 r=18 stroke="#6ee79a"/><circle cx=256 cy=38 r=20 stroke="#5ec8ff"/></g>'+
      '<g class=wb-tag><rect x=128 y=54 width=64 height=16 rx=8 fill="#0b1322" stroke="#5ec8ff" stroke-opacity=".5"/><text x=160 y=65.5 text-anchor=middle font-size=8 fill="#e8eef7" letter-spacing=".08em">⇅ FULL DUPLEX</text></g></svg>'},
    c:{cls:'v-c',k:'Signal found',wt:'2.75s',art:'<svg class=wl-art viewBox="0 0 320 150" aria-hidden=true focusable=false>'+stars+
      '<path d="M0 150V120L36 98L62 114L104 80L140 108L182 86L224 114L262 92L320 118V150Z" fill="#13203a"/><path d="M0 150V134L60 122L120 136L190 120L250 134L320 126V150Z" fill="#0c1528"/>'+
      '<path class=wc-beam d="M262 40L118 36L118 150Z" fill="#5ec8ff"/>'+
      '<g transform="translate(262 40) rotate(-10)"><g class=wc-sat>'+sat+'</g></g>'+
      '<g transform="translate(22 12)"><rect width=100 height=146 rx=15 fill="#0b1322" stroke="#e8eef7" stroke-width=1.6 /><rect x=5 y=5 width=90 height=136 rx=11 fill="#0f1a2e"/>'+
      '<rect x=36 y=8 width=28 height=7 rx=3.5 fill="#05080f"/>'+
      '<text x=12 y=24 font-size=8 font-weight=600 fill="#e8eef7">9:41</text>'+
      '<text class=wc-ns x=88 y=24 text-anchor=end font-size=7 fill="#9fb0c3">No service</text>'+
      '<g class=wc-sig><text x=66 y=24 text-anchor=end font-size=7 font-weight=700 fill="#6ee79a">SAT</text>'+
      '<g fill="#33415a"><rect x=70 y=21 width=3 height=3 rx=.6 /><rect x=74.5 y=19 width=3 height=5 rx=.6 /><rect x=79 y=17 width=3 height=7 rx=.6 /><rect x=83.5 y=15 width=3 height=9 rx=.6 /></g>'+
      '<g fill="#e8eef7"><rect class=wc-bar x=70 y=21 width=3 height=3 rx=.6 /><rect class=wc-bar x=74.5 y=19 width=3 height=5 rx=.6 /><rect class=wc-bar x=79 y=17 width=3 height=7 rx=.6 /><rect class=wc-bar x=83.5 y=15 width=3 height=9 rx=.6 /></g></g>'+
      '<text x=50 y=58 text-anchor=middle font-size=24 font-weight=600 fill="#e8eef7">9:41</text><text x=50 y=68 text-anchor=middle font-size=6 fill="#9fb0c3">Friday 13 November</text>'+
      '<g class=wc-note><rect x=9 y=78 width=82 height=30 rx=7 fill="#e8eef7" opacity=".96"/><circle cx=19 cy=88 r=5 fill="#070b14"/><circle cx=19 cy=88 r=2 fill="#00cfff"/>'+
      '<text x=28 y=90 font-size=5.4 font-weight=700 fill="#4a5a70" letter-spacing=".06em">FULL DUPLEX · NOW</text><text x=14 y=102 font-size=6.4 font-weight=700 fill="#06101c">Welcome to Full Duplex</text></g></g></svg>'},
    d:{cls:'v-d',k:'Constellation online',wt:'2.4s',art:'<svg class=wl-art viewBox="0 0 320 150" aria-hidden=true focusable=false>'+stars+
      '<g transform="translate(105 20) scale(.2132) translate(-254 -250)">'+
      '<ellipse class=wd-orbit cx=512 cy=508 rx=560 ry=170 transform="rotate(-18 512 508)" fill=none stroke="#5ec8ff" stroke-opacity=".18" stroke-width=6 stroke-dasharray="18 22"/>'+
      '<g fill=none stroke-width=32 stroke-linecap=round><path class=wd-arc d="M279 505A233 233 0 0 1 644.3 313.2" stroke="#00cfff"/><path class=wd-arc d="M744.9 511.9A233 233 0 0 1 383.7 699.5" stroke="#fff"/></g>'+
      '<g class=wd-glyph><circle cx=423 cy=432 r=10 fill="#00cfff"/><path transform="translate(426 517.5) rotate(-15)" fill="#00cfff" fill-rule=evenodd d="M-23.5 -57.5h47a5 5 0 0 1 5 5v105a5 5 0 0 1 -5 5h-47a5 5 0 0 1 -5 -5v-105a5 5 0 0 1 5 -5zM-8.5 -48h17.0a5.5 5.5 0 0 1 5.5 5.5v0.0a5.5 5.5 0 0 1 -5.5 5.5h-17.0a5.5 5.5 0 0 1 -5.5 -5.5v-0.0a5.5 5.5 0 0 1 5.5 -5.5z"/></g>'+
      '<g class=wd-glyph fill="#fff"><path d="M583 488h21l33 32-22 22-32-32z"/><path d="M620 492l20-21 15 14-21 22z"/><path d="M567 545l21-21 14 14-20 20z"/><circle cx=635 cy=541 r=8 /></g>'+
      '<g class=wd-dots></g></g></svg>',
      init:function(card){
        var arcs=card.querySelectorAll('.wd-arc'), g=card.querySelector('.wd-dots'), seed=7, n=0, h='';
        function rnd(){seed=(seed*16807)%2147483647;return seed/2147483647;}
        [].forEach.call(arcs,function(a,k){
          var L=a.getTotalLength(); a.style.setProperty('--len',L.toFixed(1));
          for(var i=0;i<15;i++){var p=a.getPointAtLength(L*i/14), ang=rnd()*6.283, r=420+rnd()*520;
            h+='<circle class=wd-dot cx='+p.x.toFixed(1)+' cy='+p.y.toFixed(1)+' r=15 fill="'+(k?'#fff':'#00cfff')+'" style="--x0:'+(Math.cos(ang)*r).toFixed(0)+'px;--y0:'+(Math.sin(ang)*r*.55).toFixed(0)+'px;--dl:'+(.2+n*.028).toFixed(3)+'s"/>'; n++;}
        });
        g.innerHTML=h;
      }}
  };
})();
