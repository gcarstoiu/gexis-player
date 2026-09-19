// gexis boot frame generator — shared by each render chunk.
// Calibrated empirically: E=36/GAP=9 renders a ~153px mark; the 140px
// wordmark renders ~308px wide, so the text is the larger element.
// Wavefronts launch at MARK_R+22 so they never emerge from behind a tile.
export async function makeRenderer(ctxHelpers) {
  const { readFileBinary, createCanvas, saveFile } = ctxHelpers;
  const blob = await readFileBinary('uploads/BricolageGrotesque-variable.ttf');
  const ff = new FontFace('BricolageG', await blob.arrayBuffer(), { weight: '200 800' });
  await ff.load(); document.fonts.add(ff);

  const W=1280,H=800, INTRO=50, PULSE=50;
  const BG=[16,26,33],UNLIT=[44,64,79],UINK=[118,144,160];
  const HUE={g:[126,214,188],e:[224,167,88],i:[159,180,232],s:[242,164,143]};
  const INK={g:[13,43,36],e:[52,31,2],i:[22,33,61],s:[61,21,9]};
  const ORDER=['g','e','i','s'];
  const E=36, GAP=9, R=10, GL=19, O=(E+GAP)/2;
  const POS={g:[-O,-O],e:[O,-O],i:[-O,O],s:[O,O]};
  const MX=640, MY=290, MARK_R=77;
  const RING0=MARK_R+22, RING1=RING0+205;
  const css=c=>`rgb(${c[0]},${c[1]},${c[2]})`;
  const mix=(a,b,t)=>[0,1,2].map(i=>Math.round(a[i]+(b[i]-a[i])*t));
  const ss=(a,b,t)=>{ if(t<=a)return 0; if(t>=b)return 1; const u=(t-a)/(b-a); return u*u*(3-2*u); };
  const bump=(c,f,w)=>{ const x=Math.abs(f-c)/w; if(x>=1)return 0; const k=Math.cos(Math.PI*x/2); return k*k; };
  const beat=v=>bump(.12,v,.10)+.55*bump(.26,v,.09);
  function wave(v,t0,t1,peak){
    if(v<t0||v>t1) return null;
    const p=(v-t0)/(t1-t0);
    const a=Math.pow(1-p,1.7)*Math.min(1,p/.14)*peak;
    return a<=.004?null:{r:RING0+p*(RING1-RING0),a};
  }
  return async function mk(f){
    const cv=createCanvas(W,H), x=cv.getContext('2d');
    x.fillStyle=css(BG); x.fillRect(0,0,W,H);
    const u=f/INTRO, settle=ss(.46,.58,u), wordA=ss(.55,.75,u), subA=ss(.68,.86,u), fxA=ss(.74,1.0,u);
    const inPulse=f>=INTRO, v=inPulse?(f-INTRO)/PULSE:0, b=inPulse?beat(v):0;
    const glowA=(.085+.085*b)*fxA;
    const litS=Math.max(bump(.46,u,.09), settle*(.93+.07*b));
    x.save(); x.translate(MX,MY);
    if(glowA>.002){
      const g=x.createRadialGradient(0,0,0,0,0,200);
      g.addColorStop(0,`rgba(242,164,143,${glowA.toFixed(3)})`);
      g.addColorStop(1,'rgba(242,164,143,0)');
      x.fillStyle=g; x.beginPath(); x.arc(0,0,200,0,Math.PI*2); x.fill();
    }
    if(inPulse){
      for(const w of [wave(v,.12,.74,.48), wave(v,.26,.86,.30)]){
        if(!w) continue;
        x.beginPath(); x.arc(0,0,w.r,0,Math.PI*2);
        x.strokeStyle=`rgba(242,164,143,${w.a.toFixed(3)})`; x.lineWidth=2; x.stroke();
      }
    }
    x.rotate(Math.PI/4);
    const lit={g:bump(.10,u,.09),e:bump(.22,u,.09),i:bump(.34,u,.09),s:litS};
    for(const l of ORDER){
      const [px,py]=POS[l], t=Math.min(1,lit[l]);
      x.beginPath(); x.roundRect(px-E/2,py-E/2,E,E,R);
      x.fillStyle=css(mix(UNLIT,HUE[l],t)); x.fill();
      x.save(); x.translate(px,py); x.rotate(-Math.PI/4);
      x.font='800 '+GL+'px BricolageG, sans-serif';
      x.textAlign='center'; x.textBaseline='middle';
      x.fillStyle=css(mix(UINK,INK[l],t)); x.fillText(l,0,1); x.restore();
    }
    x.restore();
    if(wordA>.003){
      x.textAlign='center'; x.textBaseline='alphabetic';
      x.globalAlpha=wordA; x.fillStyle='#e8eef2';
      x.font='600 140px BricolageG, sans-serif';
      x.fillText('gexis', MX, 540+(1-wordA)*9); x.globalAlpha=1;
    }
    if(subA>.003){
      const lab='SOUND', fs=26, tr=fs*.20;
      x.globalAlpha=subA; x.font='700 '+fs+'px BricolageG, sans-serif';
      x.textAlign='left'; x.textBaseline='alphabetic';
      let wsum=0; for(const ch of lab) wsum+=x.measureText(ch).width+tr; wsum-=tr;
      let cx=MX-wsum/2; x.fillStyle='#f2a48f';
      for(const ch of lab){ x.fillText(ch,cx,600); cx+=x.measureText(ch).width+tr; }
      x.globalAlpha=1;
    }
    await saveFile(`plymouth/boot-${String(f+1).padStart(4,'0')}.png`, cv);
  };
}
