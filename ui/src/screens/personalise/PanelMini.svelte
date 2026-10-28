<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  **The panel in miniature** (ADR-0149). GENERATED from Claude Design's
  `Panel Mini.dc.html` (design/source/14-first-use) by
  `tools/design/gen_personalise.py`: its markup, inline styles, keyframes
  and logic as designed. Change the design, then generate again.
-->
<script>
  import artistPhoto from '../../assets/personalise/artist-photo.webp';
  import calm from '../../assets/personalise/calm.webp';
  import mark from '../../assets/gexis-mark.svg';
  import lyrionIcon from '../../assets/icon-lyrion.svg';
  import spotifyIcon from '../../assets/icon-spotify.png';
  import btIcon from '../../assets/icon-bluetooth.png';
  import airplayIcon from '../../assets/icon-airplay.png';

  let p = $props();

const KINDS = ['lib', 'simple', 'now', 'wait', 'viz', 'clock', 'off', 'custom', 'vu', 'turn', 'code', 'vs', 'tape', 'setup', 'photo', 'flow'];
const CYC = { vu: '0s', viz: '-6s', turn: '-4s', tape: '-2s' };
const cap = k => 'k' + k[0].toUpperCase() + k.slice(1);
const FC = [['Fri', 'part', '18°', '9°'], ['Sat', 'sun', '21°', '11°'], ['Sun', 'rain', '16°', '10°']];
const cond = c => ({ sunDisplay: c === 'sun' || c === 'part' ? 'block' : 'none', cloudDisplay: c === 'part' || c === 'cloud' || c === 'rain' ? 'block' : 'none', rainDisplay: c === 'rain' ? 'block' : 'none' });

  function today(sep = ' ') {
    const d = new Date();
    return d.toLocaleDateString('en-GB', { weekday: 'long' }) + sep + d.toLocaleDateString('en-GB', { day: 'numeric', month: 'long' });
  }

  // The flow's sources: all four in turn (How will you listen?), or the
  // ones chosen (Getting ready), 3 s each.
  const FLOW = ['lyr', 'plex', 'spo', 'bt'], FLOW_DELAY = { lyr: '0s', plex: '-9s', spo: '-6s', bt: '-3s' };
  function flowShow(src) { return !p.marks || p.marks.includes(src) ? 'block' : 'none'; }
  function flowAnim(src) {
    if (!p.marks) return `fuCycle 12s linear ${FLOW_DELAY[src]} infinite`;
    const chosen = FLOW.filter((x) => p.marks.includes(x)), n = chosen.length, k = chosen.indexOf(src);
    if (k < 0) return 'none';
    const name = n >= 4 ? 'fuCycle' : `fuCycle${n}`;
    return `${name} ${3 * n}s linear ${k === 0 ? 0 : 3 * k - 3 * n}s infinite`;
  }


  function idle(p) {
    const bg = p.black ? 'black' : p.bg || 'wall', t = String(p.time || '21:04'), m = t.match(/^(\S+)\s*(am|pm)?$/i) || [t, t, ''];
    return {
      hm: m[1], ampm: m[2] || '', ampmDisplay: m[2] ? 'inline' : 'none', ss: '37',
      artistDisplay: bg === 'artist' ? 'block' : 'none', wallDisplay: bg === 'wall' ? 'block' : 'none',
      bright: bg === 'black' ? '1' : '0.62', stroke: bg === 'black' ? '0' : '0.3125cqw rgba(46,57,66,0.92)', scrim: bg === 'black' ? 'rgba(11,18,24,0.93)' : 'rgba(7,11,15,0.06)',
      credits: [bg === 'wall' ? 'Photos from Pixabay' : bg === 'artist' ? 'Gasca Zurli' : null, p.weather === false ? null : 'Weather data by Open-Meteo.com'].filter(Boolean).join(' · '),
      creditsDisplay: bg !== 'black' || p.weather !== false ? 'block' : 'none',
      wxDays: FC.map(d => Object.assign({ name: d[0], max: d[2], min: d[3] }, cond(d[1])))
    };
  }
  function waitHome(p) {
    const mk = p.marks || [], N = { lyr: ['Lyrion', 'Starts on play'], plex: ['Plexamp', 'Listening'], spo: ['Spotify', 'Listening'], air: ['AirPlay', 'Listening'], bt: ['Bluetooth', 'Pairable'] };
    const tiles = ['lyr', 'plex', 'spo', 'air', 'bt'].filter(k => mk.includes(k)).map(k => { const lead = k === 'lyr'; return { name: N[k][0], status: N[k][1], isLyr: lead, isPlex: k === 'plex', isSpo: k === 'spo', isAir: k === 'air', isBt: k === 'bt',
      border: lead ? 'rgba(126,214,188,0.5)' : 'rgba(233,238,242,0.14)', markBg: lead ? 'rgba(126,214,188,0.1)' : 'rgba(233,238,242,0.08)', statusInk: lead ? '#7ed6bc' : 'rgba(233,238,242,0.6)' }; });
    return { wTiles: tiles, wCols: Math.max(tiles.length, 3), wServices: tiles.length > 0, wNone: !tiles.length, wWall: !p.black };
  }
  function renderVals(p) {
    const kind = p.kind || 'lib', all = kind === 'all', anim = p.animate !== false, rpm = p.rpm === 45 ? 45 : 33;
    const o = {
      wire: p.wire || 'rgba(233,238,242,0.22)', time: p.time || '21:04', place: p.place || 'Berlin', player: p.player || 'Living Room',
      phone: p.phone || 'George’s iPhone', secs: (p.secs ?? 24) + 's', rpm,
      wallSrc: p.wallSrc || calm, photoSrc: p.photo || '', clockDisplay: p.clock === false ? 'none' : 'block', clockFlex: p.clock === false ? 'none' : 'flex', weatherFlex: p.weather === false ? 'none' : 'flex',
      ...idle(p), ...waitHome(p),
      spin: anim ? 'fuSpin ' + (rpm === 45 ? '1.33s' : '1.8s') + ' linear infinite' : 'none', reel: anim ? 'fuSpin 2.4s linear infinite' : 'none',
      marks: (p.marks || []).map(m => ({ isLyr: m === 'lyr', isSpo: m === 'spo', isAir: m === 'air', isBt: m === 'bt', isPlex: m === 'plex' }))
    };
    KINDS.forEach(k => { o[cap(k)] = kind === k; });
    Object.keys(CYC).forEach(k => { if (all) o[cap(k)] = true; o['c' + k] = all ? 'fuCycle 8s linear ' + CYC[k] + ' infinite' : 'none'; });
    return o;
  }

  const V = $derived(renderVals(p));
</script>


<div style="position:relative;width:100%;aspect-ratio:16/10;border-radius:9px;background:#0a1015;box-sizing:border-box;overflow:hidden;container-type:inline-size;font-family:'Nunito Sans Variable','Nunito Sans','Avenir Next','Segoe UI',system-ui,sans-serif;border:2px solid {V.wire};">
  {#if V.kLib}
    <div style="position:absolute;inset:12% 9%;display:flex;flex-direction:column;gap:9%;">
      <div style="flex:3;display:flex;gap:5%;"><span style="flex:1;border-radius:3px;background:rgba(233,238,242,0.18);display:block;"></span><span style="flex:1;border-radius:3px;background:rgba(233,238,242,0.18);display:block;"></span><span style="flex:1;border-radius:3px;background:rgba(233,238,242,0.18);display:block;"></span><span style="flex:1;border-radius:3px;background:rgba(233,238,242,0.18);display:block;"></span><span style="flex:1;border-radius:3px;background:rgba(233,238,242,0.18);display:block;"></span></div>
      <div style="flex:2;display:flex;gap:4%;"><span style="flex:1;border-radius:2px;background:rgba(233,238,242,0.09);display:block;"></span><span style="flex:1;border-radius:2px;background:rgba(233,238,242,0.09);display:block;"></span><span style="flex:1;border-radius:2px;background:rgba(233,238,242,0.09);display:block;"></span><span style="flex:1;border-radius:2px;background:rgba(233,238,242,0.09);display:block;"></span><span style="flex:1;border-radius:2px;background:rgba(233,238,242,0.09);display:block;"></span><span style="flex:1;border-radius:2px;background:rgba(233,238,242,0.09);display:block;"></span></div>
      <div style="flex:1.2;border-radius:3px;background:rgba(233,238,242,0.1);display:flex;align-items:center;padding:0 6%;gap:6%;"><span style="height:50%;aspect-ratio:1;border-radius:2px;background:rgba(242,164,143,0.5);display:block;"></span><span style="flex:1;height:22%;border-radius:2px;background:rgba(233,238,242,0.22);display:block;"></span></div>
    </div>
  {/if}
  {#if V.kSimple}
    <div style="position:absolute;inset:12% 9%;display:flex;flex-direction:column;gap:9%;">
      <div style="flex:4;display:flex;gap:6%;"><span style="flex:1;border-radius:4px;background:rgba(233,238,242,0.2);display:block;"></span><span style="flex:1;border-radius:4px;background:rgba(233,238,242,0.2);display:block;"></span><span style="flex:1;border-radius:4px;background:rgba(233,238,242,0.2);display:block;"></span></div>
      <div style="flex:1.2;border-radius:3px;background:rgba(233,238,242,0.1);display:flex;align-items:center;padding:0 6%;gap:6%;"><span style="height:50%;aspect-ratio:1;border-radius:2px;background:rgba(242,164,143,0.5);display:block;"></span><span style="flex:1;height:22%;border-radius:2px;background:rgba(233,238,242,0.22);display:block;"></span></div>
    </div>
  {/if}
  {#if V.kNow}
    <div style="position:absolute;inset:16% 9%;display:flex;gap:9%;align-items:center;">
      <span style="height:100%;aspect-ratio:1;border-radius:4px;background:rgba(242,164,143,0.42);display:block;flex-shrink:0;"></span>
      <span style="flex:1;display:flex;flex-direction:column;gap:6cqw;">
        <span style="height:4cqw;width:86%;border-radius:2px;background:rgba(233,238,242,0.34);display:block;"></span>
        <span style="height:3cqw;width:58%;border-radius:2px;background:#f2a48f;opacity:0.6;display:block;"></span>
        <span style="height:2cqw;width:100%;border-radius:2px;background:rgba(233,238,242,0.14);display:block;"></span>
      </span>
    </div>
  {/if}
  {#if V.kWait}
    <div style="position:absolute;inset:0;z-index:11;background:#000;overflow:hidden;">
      {#if V.wWall}
        <img src={calm} alt="" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;display:block;" />
        <div style="position:absolute;inset:0;background:linear-gradient(180deg, rgba(10,16,22,0.42) 0%, rgba(10,16,22,0) 38%), linear-gradient(0deg, rgba(10,16,22,0.62) 0%, rgba(10,16,22,0) 45%);"></div>
      {/if}
      <div style="position:absolute;top:2.0313cqw;right:2.0313cqw;z-index:2;width:5cqw;height:5cqw;border-radius:1.4063cqw;border:1px solid rgba(233,238,242,0.14);background:rgba(16,26,33,0.6);box-sizing:border-box;display:flex;align-items:center;justify-content:center;"><span style="position:relative;width:2.0313cqw;height:1.4063cqw;display:block;"><span style="position:absolute;left:0;top:0.3125cqw;width:2.0313cqw;height:0.1563cqw;border-radius:1px;background:#e9eef2;opacity:0.55;display:block;"></span><span style="position:absolute;top:0.1172cqw;left:0.4688cqw;width:0.5469cqw;height:0.5469cqw;border-radius:50%;background:#e9eef2;display:block;"></span><span style="position:absolute;left:0;top:0.9375cqw;width:2.0313cqw;height:0.1563cqw;border-radius:1px;background:#e9eef2;opacity:0.55;display:block;"></span><span style="position:absolute;top:0.7422cqw;left:1.1719cqw;width:0.5469cqw;height:0.5469cqw;border-radius:50%;background:#e9eef2;display:block;"></span></span></div>
      <div style="position:absolute;left:4.375cqw;top:3.5938cqw;z-index:1;color:#e9eef2;text-shadow:0 1px 14px rgba(0,0,0,0.35);display:{V.clockDisplay};">
        <div style="font-size:9.375cqw;font-weight:300;line-height:1;letter-spacing:-0.03em;font-variant-numeric:tabular-nums;">{V.time}</div>
        <div style="margin-top:0.7813cqw;font-size:2.0313cqw;font-weight:600;color:rgba(233,238,242,0.88);">{today()}</div>
        <div style="margin-top:1.0938cqw;font-family:'IBM Plex Mono','Courier New',monospace;font-size:1.0938cqw;letter-spacing:0.2em;text-transform:uppercase;color:rgba(233,238,242,0.88);">{V.player}</div>
      </div>
      {#if V.wNone}
        <div style="position:absolute;left:4.375cqw;right:4.375cqw;bottom:4.0625cqw;z-index:1;">
          <div style="font-size:2.3438cqw;font-weight:700;color:#e9eef2;">No sources</div>
          <div style="margin-top:0.9375cqw;font-size:1.3281cqw;color:rgba(233,238,242,0.75);">Every source is switched off. Settings, top right.</div>
        </div>
      {/if}
      {#if V.wServices}
        <div style="position:absolute;left:4.375cqw;right:4.375cqw;bottom:4.0625cqw;z-index:1;display:flex;flex-direction:column;gap:1.25cqw;">
                    <div style="display:grid;grid-template-columns:repeat({V.wCols}, minmax(0,1fr));gap:1.25cqw;justify-items:center;">
            {#each V.wTiles as m}
              <div style="display:flex;flex-direction:column;align-items:center;gap:0.9375cqw;min-width:0;max-width:100%;">
                <div style="position:relative;width:5.625cqw;height:5.625cqw;flex-shrink:0;border-radius:50%;display:flex;align-items:center;justify-content:center;background:{m.markBg};"><span style="position:absolute;inset:-0.47cqw;border-radius:50%;border:0.16cqw solid {m.border};animation:npRing 2800ms ease-out infinite;"></span>
                  {#if m.isLyr}<img src={lyrionIcon} alt="" style="display:block;width:3.9844cqw;height:2.9688cqw;" />{/if}
                  {#if m.isSpo}<img src={spotifyIcon} alt="" style="display:block;width:2.9688cqw;height:2.9688cqw;opacity:0.8;" />{/if}
                  {#if m.isAir}<img src={airplayIcon} alt="" style="display:block;width:2.9688cqw;height:2.9688cqw;opacity:0.8;" />{/if}
                  {#if m.isBt}<img src={btIcon} alt="" style="display:block;width:2.9688cqw;height:2.9688cqw;opacity:0.8;" />{/if}
                  {#if m.isPlex}<span style="font-size:2.6cqw;font-weight:800;color:rgba(233,238,242,0.8);line-height:1;">P</span>{/if}
                </div>
                <div style="min-width:0;max-width:100%;text-align:center;text-shadow:0 1px 8px rgba(0,0,0,0.6);">
                  <div style="font-size:1.9531cqw;font-weight:700;color:#e9eef2;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{m.name}</div>
                  <div style="margin-top:0.625cqw;font-family:'IBM Plex Mono','Courier New',monospace;font-size:0.9375cqw;letter-spacing:0.2em;text-transform:uppercase;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:{m.statusInk};">{m.status}</div>
                </div>
              </div>
            {/each}
          </div>
        </div>
      {/if}
    </div>
  {/if}
  {#if V.kClock}
<div style="position:absolute;inset:0;overflow:hidden;background:#0b1218;">
<img src={artistPhoto} alt="" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;filter:brightness({V.bright}) saturate(0.9);display:{V.artistDisplay};" />
<img src={V.wallSrc} alt="" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;filter:brightness({V.bright}) saturate(0.9);display:{V.wallDisplay};" />
<div style="position:absolute;inset:0;background:{V.scrim};"></div>
<div style="position:absolute;left:4.375cqw;right:4.375cqw;bottom:0.5469cqw;z-index:2;font-family:'IBM Plex Mono','Courier New',monospace;font-size:0.8594cqw;line-height:1.0938cqw;letter-spacing:0.16em;text-transform:uppercase;text-align:center;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:#e9eef2;paint-order:stroke fill;-webkit-text-stroke:{V.stroke};display:{V.creditsDisplay};">{V.credits}</div>
<div style="position:absolute;width:max-content;transform:translate(-50%,-50%);transition:left 1400ms cubic-bezier(0.4,0,0.2,1),top 1400ms cubic-bezier(0.4,0,0.2,1);left:40%;top:36%;display:flex;flex-direction:column;align-items:flex-start;gap:1.25cqw;">
      <div style="align-items:baseline;gap:1.0938cqw;font-family:'IBM Plex Mono','Courier New',monospace;font-weight:300;letter-spacing:-0.02em;white-space:nowrap;display:{V.clockFlex};">
        <span style="font-size:10.3125cqw;line-height:1;color:#e9eef2;paint-order:stroke fill;-webkit-text-stroke:{V.stroke};text-shadow:0 0.1563cqw 0.7813cqw rgba(7,11,15,0.55);">{V.hm}</span>
        <span style="font-size:4.5313cqw;line-height:1;color:#7ed6bc;paint-order:stroke fill;-webkit-text-stroke:{V.stroke};text-shadow:0 0.1563cqw 0.7813cqw rgba(7,11,15,0.55);">{V.ss}</span>
        <span style="font-size:4.5313cqw;line-height:1;color:#7ed6bc;paint-order:stroke fill;-webkit-text-stroke:{V.stroke};text-shadow:0 0.1563cqw 0.7813cqw rgba(7,11,15,0.55);display:{V.ampmDisplay};">{V.ampm}</span>
      </div>
      <div style="font-family:'IBM Plex Mono','Courier New',monospace;font-size:2.0313cqw;letter-spacing:0.2em;text-transform:uppercase;color:#e9eef2;white-space:nowrap;paint-order:stroke fill;-webkit-text-stroke:{V.stroke};text-shadow:0 0.1563cqw 0.7813cqw rgba(7,11,15,0.55);display:{V.clockDisplay};">{today(' · ')}</div>
      
      
    </div>
<div style="position:absolute;left:0;right:0;bottom:0;padding:1.7188cqw 2.1875cqw 2.0313cqw;box-sizing:border-box;align-items:center;gap:1.5625cqw;display:{V.weatherFlex};">
      <div style="display:flex;align-items:center;gap:2.1875cqw;flex-shrink:0;">
        <span style="position:relative;width:9.6875cqw;height:9.6875cqw;zoom:1.065;flex-shrink:0;display:block;">
          <span style="position:absolute;inset:0;display:block;">
              <span style="position:absolute;left:50%;top:50%;width:9.6875cqw;height:9.6875cqw;margin:-4.8438cqw 0 0 -4.8438cqw;animation:wxSpin 18s linear infinite;display:block;">
                <span style="position:absolute;left:50%;top:0;width:0.4688cqw;height:1.6469cqw;margin-left:-0.2344cqw;border-radius:0.1563cqw;background:#f2c14f;display:block;"></span>
                <span style="position:absolute;left:50%;bottom:0;width:0.4688cqw;height:1.6469cqw;margin-left:-0.2344cqw;border-radius:0.1563cqw;background:#f2c14f;display:block;"></span>
                <span style="position:absolute;top:50%;left:0;width:1.6469cqw;height:0.4688cqw;margin-top:-0.2344cqw;border-radius:0.1563cqw;background:#f2c14f;display:block;"></span>
                <span style="position:absolute;top:50%;right:0;width:1.6469cqw;height:0.4688cqw;margin-top:-0.2344cqw;border-radius:0.1563cqw;background:#f2c14f;display:block;"></span>
              </span>
              <span style="position:absolute;left:50%;top:50%;width:4.8438cqw;height:4.8438cqw;margin:-2.4219cqw 0 0 -2.4219cqw;border-radius:50%;background:#f2c14f;box-shadow:0 0 2.9062cqw rgba(242,193,79,0.6);display:block;"></span>
              <span style="position:absolute;left:0;top:2.9062cqw;width:9.6875cqw;height:4.0687cqw;animation:wxDrift 5s ease-in-out infinite;display:block;">
                <span style="position:absolute;left:0;bottom:0;width:9.6875cqw;height:2.5187cqw;border-radius:9.6875cqw;background:#eef3f7;display:block;"></span>
                <span style="position:absolute;left:1.55cqw;top:0;width:4.0687cqw;height:4.0687cqw;border-radius:50%;background:#eef3f7;display:block;"></span>
                <span style="position:absolute;right:1.1625cqw;top:0.9688cqw;width:3.1cqw;height:3.1cqw;border-radius:50%;background:#eef3f7;display:block;"></span>
              </span>
              <span style="position:absolute;left:2.1313cqw;bottom:0;width:0.5469cqw;height:1.9375cqw;border-radius:0.1563cqw;background:#8fc4e8;animation:wxFall 1.1s linear infinite;display:none;"></span>
              <span style="position:absolute;left:4.65cqw;bottom:0;width:0.5469cqw;height:1.9375cqw;border-radius:0.1563cqw;background:#8fc4e8;animation:wxFall 1.1s linear 0.35s infinite;display:none;"></span>
              <span style="position:absolute;left:7.1688cqw;bottom:0;width:0.5469cqw;height:1.9375cqw;border-radius:0.1563cqw;background:#8fc4e8;animation:wxFall 1.1s linear 0.7s infinite;display:none;"></span>
            </span>
          
          
          </span>
        <div style="min-width:0;">
          <div style="display:flex;align-items:center;gap:1.25cqw;">
            <span style="font-size:7.8125cqw;font-weight:300;letter-spacing:-0.03em;line-height:0.94;color:#e9eef2;paint-order:stroke fill;-webkit-text-stroke:{V.stroke};text-shadow:0 0.1563cqw 0.7813cqw rgba(7,11,15,0.55);">17°</span>
            <span style="white-space:nowrap;flex-direction:column;align-items:flex-start;gap:0.1563cqw;display:flex;paint-order:stroke fill;-webkit-text-stroke:{V.stroke};text-shadow:0 0.1563cqw 0.7813cqw rgba(7,11,15,0.55);"><span style="font-size:3.125cqw;font-weight:700;color:#f2a48f;">18°</span><span style="font-size:2.3438cqw;color:#9fb4e8;">9°</span></span>
          </div>
          <div style="font-size:2.3438cqw;font-weight:600;color:#7ed6bc;margin-top:0.625cqw;white-space:nowrap;paint-order:stroke fill;-webkit-text-stroke:{V.stroke};text-shadow:0 0.1563cqw 0.7813cqw rgba(7,11,15,0.55);">Partly cloudy</div>
        </div>
      </div>
      <div style="width:1px;align-self:stretch;background:rgba(233,238,242,0.26);flex-shrink:0;"></div>
      <div style="display:grid;grid-template-columns:minmax(0,1fr);gap:0.9375cqw;flex-shrink:0;paint-order:stroke fill;-webkit-text-stroke:{V.stroke};text-shadow:0 0.1563cqw 0.7813cqw rgba(7,11,15,0.55);">
        <span style="display:block;min-width:0;align-self:center;">
          <span style="display:block;font-size:2.3438cqw;font-weight:700;color:#e9eef2;white-space:nowrap;">15°</span>
        </span>
        <span style="display:block;min-width:0;align-self:center;">
          <span style="display:block;font-size:2.3438cqw;font-weight:700;color:#e9eef2;white-space:nowrap;">12 km/h</span>
        </span>
        <span style="display:flex;flex-direction:column;gap:0.4688cqw;min-width:0;margin-top:0.3125cqw;">
          <span style="display:flex;align-items:center;gap:0.8594cqw;min-width:0;">
            <span style="position:relative;width:2.8125cqw;height:2.8125cqw;flex-shrink:0;display:block;"><span style="position:absolute;left:0;bottom:0.5469cqw;width:2.8125cqw;height:0.2344cqw;border-radius:0.1563cqw;background:#e9eef2;display:block;"></span><span style="position:absolute;left:0.4688cqw;bottom:0.7813cqw;width:1.875cqw;height:0.9375cqw;overflow:hidden;display:block;"><span style="display:block;width:1.875cqw;height:1.875cqw;border-radius:50%;background:#f2c14f;"></span></span><span style="position:absolute;left:1.3281cqw;top:1px;width:0.2344cqw;height:0.625cqw;border-radius:0.1563cqw;background:#f2c14f;display:block;"></span><span style="position:absolute;left:0.3125cqw;top:0.3906cqw;width:0.2344cqw;height:0.625cqw;border-radius:0.1563cqw;background:#f2c14f;transform:rotate(-42deg);display:block;"></span><span style="position:absolute;right:0.3125cqw;top:0.3906cqw;width:0.2344cqw;height:0.625cqw;border-radius:0.1563cqw;background:#f2c14f;transform:rotate(42deg);display:block;"></span></span>
            <span style="font-size:2.3438cqw;font-weight:700;color:#f2c14f;white-space:nowrap;">06:52</span>
          </span>
          <span style="display:flex;align-items:center;gap:0.8594cqw;min-width:0;">
            <span style="position:relative;width:2.8125cqw;height:2.8125cqw;flex-shrink:0;display:block;"><span style="position:absolute;left:0;bottom:1.25cqw;width:2.8125cqw;height:0.2344cqw;border-radius:0.1563cqw;background:#e9eef2;display:block;"></span><span style="position:absolute;left:0.4688cqw;bottom:0.1563cqw;width:1.875cqw;height:0.9375cqw;overflow:hidden;display:block;"><span style="display:block;width:1.875cqw;height:1.875cqw;border-radius:50%;background:#f2a48f;margin-top:-0.9375cqw;"></span></span></span>
            <span style="font-size:2.3438cqw;font-weight:700;color:#f2a48f;white-space:nowrap;">19:24</span>
          </span>
        </span>
      </div>
      <span style="flex:1;min-width:5cqw;"></span>
      <div style="display:flex;align-items:flex-start;gap:3.125cqw;flex-shrink:0;">
        {#each V.wxDays as d}
          <span style="display:flex;flex-direction:column;align-items:center;gap:0.9375cqw;flex-shrink:0;min-width:8.2813cqw;">
            <span style="font-family:'IBM Plex Mono','Courier New',monospace;font-size:2.0313cqw;letter-spacing:0.16em;text-transform:uppercase;color:#e9eef2;display:block;paint-order:stroke fill;-webkit-text-stroke:{V.stroke};text-shadow:0 0.1563cqw 0.7813cqw rgba(7,11,15,0.55);">{d.name}</span>
            <span style="position:relative;width:6.25cqw;height:6.25cqw;zoom:1.25;flex-shrink:0;display:block;">
          <span style="position:absolute;inset:0;display:block;">
              <span style="position:absolute;left:50%;top:50%;width:6.25cqw;height:6.25cqw;margin:-3.125cqw 0 0 -3.125cqw;animation:wxSpin 18s linear infinite;display:{d.sunDisplay};">
                <span style="position:absolute;left:50%;top:0;width:0.3125cqw;height:1.0625cqw;margin-left:-0.1563cqw;border-radius:0.1563cqw;background:#f2c14f;display:block;"></span>
                <span style="position:absolute;left:50%;bottom:0;width:0.3125cqw;height:1.0625cqw;margin-left:-0.1563cqw;border-radius:0.1563cqw;background:#f2c14f;display:block;"></span>
                <span style="position:absolute;top:50%;left:0;width:1.0625cqw;height:0.3125cqw;margin-top:-0.1563cqw;border-radius:0.1563cqw;background:#f2c14f;display:block;"></span>
                <span style="position:absolute;top:50%;right:0;width:1.0625cqw;height:0.3125cqw;margin-top:-0.1563cqw;border-radius:0.1563cqw;background:#f2c14f;display:block;"></span>
              </span>
              <span style="position:absolute;left:50%;top:50%;width:3.125cqw;height:3.125cqw;margin:-1.5625cqw 0 0 -1.5625cqw;border-radius:50%;background:#f2c14f;box-shadow:0 0 1.875cqw rgba(242,193,79,0.6);display:{d.sunDisplay};"></span>
              <span style="position:absolute;left:0;top:1.875cqw;width:6.25cqw;height:2.625cqw;animation:wxDrift 5s ease-in-out infinite;display:{d.cloudDisplay};">
                <span style="position:absolute;left:0;bottom:0;width:6.25cqw;height:1.625cqw;border-radius:6.25cqw;background:#eef3f7;display:block;"></span>
                <span style="position:absolute;left:1cqw;top:0;width:2.625cqw;height:2.625cqw;border-radius:50%;background:#eef3f7;display:block;"></span>
                <span style="position:absolute;right:0.75cqw;top:0.625cqw;width:2cqw;height:2cqw;border-radius:50%;background:#eef3f7;display:block;"></span>
              </span>
              <span style="position:absolute;left:1.375cqw;bottom:0;width:0.3125cqw;height:1.25cqw;border-radius:0.1563cqw;background:#8fc4e8;animation:wxFall 1.1s linear infinite;display:{d.rainDisplay};"></span>
              <span style="position:absolute;left:3cqw;bottom:0;width:0.3125cqw;height:1.25cqw;border-radius:0.1563cqw;background:#8fc4e8;animation:wxFall 1.1s linear 0.35s infinite;display:{d.rainDisplay};"></span>
              <span style="position:absolute;left:4.625cqw;bottom:0;width:0.3125cqw;height:1.25cqw;border-radius:0.1563cqw;background:#8fc4e8;animation:wxFall 1.1s linear 0.7s infinite;display:{d.rainDisplay};"></span>
            </span>
          
          
          </span>
            <span style="display:flex;align-items:baseline;gap:0.7031cqw;">
              <span style="font-size:3.4375cqw;font-weight:700;color:#f2a48f;paint-order:stroke fill;-webkit-text-stroke:{V.stroke};text-shadow:0 0.1563cqw 0.7813cqw rgba(7,11,15,0.55);">{d.max}</span>
              <span style="font-size:2.6563cqw;color:#9fb4e8;paint-order:stroke fill;-webkit-text-stroke:{V.stroke};text-shadow:0 0.1563cqw 0.7813cqw rgba(7,11,15,0.55);">{d.min}</span>
            </span>
          </span>
        {/each}
      </div>
    </div>
</div>
{/if}
  {#if V.kOff}
    <div style="position:absolute;inset:0;background:#000;display:flex;align-items:center;justify-content:center;font-family:'IBM Plex Mono','Courier New',monospace;font-size:3.8cqw;letter-spacing:0.2em;text-transform:uppercase;color:rgba(233,238,242,0.4);">Off until 07:00</div>
  {/if}
  {#if V.kFlow}
    <div style="position:absolute;inset:0;background:radial-gradient(ellipse at 50% 30%, #1a2a35 0%, #0d151b 70%);overflow:hidden;">
      <div style="position:absolute;left:50cqw;top:4cqw;transform:translateX(-50%);display:flex;align-items:flex-end;gap:2.6cqw;">
        <div style="width:11cqw;height:25cqw;border-radius:1.2cqw;border:0.18cqw solid rgba(233,238,242,0.35);background:#0d151b;box-sizing:border-box;display:flex;flex-direction:column;align-items:center;gap:2.8cqw;padding-top:2.8cqw;flex-shrink:0;"><div style="width:3cqw;height:3cqw;border-radius:50%;box-sizing:border-box;border:0.18cqw solid rgba(233,238,242,0.4);"></div><div style="position:relative;width:7.4cqw;height:7.4cqw;border-radius:50%;box-sizing:border-box;border:0.18cqw solid rgba(233,238,242,0.45);display:flex;align-items:center;justify-content:center;"><div style="width:4cqw;height:4cqw;border-radius:50%;background:rgba(233,238,242,0.28);animation:pmPump 470ms ease-in-out infinite;"></div><div style="position:absolute;inset:-0.18cqw;border-radius:50%;border:0.18cqw solid #7ed6bc;animation:fuRing 1.4s ease-out infinite;"></div></div></div>
        <div style="width:32cqw;height:20cqw;border-radius:1.6cqw;border:0.22cqw solid #9fb4e8;background:#0d151b;box-sizing:border-box;display:flex;align-items:flex-end;justify-content:center;gap:1cqw;padding-bottom:3.2cqw;margin-bottom:2.5cqw;box-shadow:0 0 7cqw rgba(126,214,188,0.2);"><div style="width:1.5cqw;height:4.70cqw;border-radius:0.3cqw;background:#7ed6bc;transform-origin:bottom;animation:fuBar 420ms ease-in-out 0ms infinite alternate;"></div><div style="width:1.5cqw;height:7.43cqw;border-radius:0.3cqw;background:#7ed6bc;transform-origin:bottom;animation:fuBar 380ms ease-in-out 180ms infinite alternate;"></div><div style="width:1.5cqw;height:5.87cqw;border-radius:0.3cqw;background:#7ed6bc;transform-origin:bottom;animation:fuBar 460ms ease-in-out 90ms infinite alternate;"></div><div style="width:1.5cqw;height:9.00cqw;border-radius:0.3cqw;background:#7ed6bc;transform-origin:bottom;animation:fuBar 400ms ease-in-out 270ms infinite alternate;"></div><div style="width:1.5cqw;height:6.65cqw;border-radius:0.3cqw;background:#7ed6bc;transform-origin:bottom;animation:fuBar 440ms ease-in-out 60ms infinite alternate;"></div><div style="width:1.5cqw;height:7.83cqw;border-radius:0.3cqw;background:#7ed6bc;transform-origin:bottom;animation:fuBar 360ms ease-in-out 210ms infinite alternate;"></div><div style="width:1.5cqw;height:4.30cqw;border-radius:0.3cqw;background:#7ed6bc;transform-origin:bottom;animation:fuBar 480ms ease-in-out 120ms infinite alternate;"></div><div style="width:1.5cqw;height:7.04cqw;border-radius:0.3cqw;background:#7ed6bc;transform-origin:bottom;animation:fuBar 410ms ease-in-out 150ms infinite alternate;"></div><div style="width:1.5cqw;height:5.48cqw;border-radius:0.3cqw;background:#7ed6bc;transform-origin:bottom;animation:fuBar 450ms ease-in-out 30ms infinite alternate;"></div></div>
        <div style="width:11cqw;height:25cqw;border-radius:1.2cqw;border:0.18cqw solid rgba(233,238,242,0.35);background:#0d151b;box-sizing:border-box;display:flex;flex-direction:column;align-items:center;gap:2.8cqw;padding-top:2.8cqw;flex-shrink:0;"><div style="width:3cqw;height:3cqw;border-radius:50%;box-sizing:border-box;border:0.18cqw solid rgba(233,238,242,0.4);"></div><div style="position:relative;width:7.4cqw;height:7.4cqw;border-radius:50%;box-sizing:border-box;border:0.18cqw solid rgba(233,238,242,0.45);display:flex;align-items:center;justify-content:center;"><div style="width:4cqw;height:4cqw;border-radius:50%;background:rgba(233,238,242,0.28);animation:pmPump 470ms ease-in-out infinite;"></div><div style="position:absolute;inset:-0.18cqw;border-radius:50%;border:0.18cqw solid #7ed6bc;animation:fuRing 1.4s ease-out infinite;"></div></div></div>
      </div>
      <div style="position:absolute;inset:0;z-index:2;opacity:0;animation:{flowAnim('lyr')};display:{flowShow('lyr')};">
        <span style="position:absolute;left:48cqw;top:38.5cqw;margin-left:-1cqw;margin-top:-2cqw;font-size:3cqw;line-height:1;color:#7ed6bc;opacity:0;animation:pmRiseA 2s ease-in-out 0ms infinite;">♪</span><span style="position:absolute;left:51.5cqw;top:38.5cqw;margin-left:-1cqw;margin-top:-2cqw;font-size:2.5cqw;line-height:1;color:#7ed6bc;opacity:0;animation:pmRiseB 2.5s ease-in-out 350ms infinite;">♫</span><span style="position:absolute;left:50cqw;top:38.5cqw;margin-left:-1cqw;margin-top:-2cqw;font-size:3.4cqw;line-height:1;color:#7ed6bc;opacity:0;animation:pmRiseA 1.8s ease-in-out 1100ms infinite;">♪</span><span style="position:absolute;left:49cqw;top:38.5cqw;margin-left:-1cqw;margin-top:-2cqw;font-size:2.7cqw;line-height:1;color:#7ed6bc;opacity:0;animation:pmRiseB 2.8s ease-in-out 1350ms infinite;">♩</span><span style="position:absolute;left:52cqw;top:38.5cqw;margin-left:-1cqw;margin-top:-2cqw;font-size:3cqw;line-height:1;color:#7ed6bc;opacity:0;animation:pmRiseA 2.2s ease-in-out 2200ms infinite;">♫</span>
        <div style="position:absolute;left:50cqw;top:45cqw;width:0;height:0;"><div style="position:absolute;left:-5cqw;top:-5cqw;width:10cqw;height:10cqw;border-radius:50%;border:0.18cqw solid rgba(233,238,242,0.5);box-sizing:border-box;animation:npRing 1800ms ease-out infinite;"></div><div style="position:absolute;left:-5cqw;top:-5cqw;width:10cqw;height:10cqw;border-radius:50%;background:rgba(16,26,33,0.92);border:1px solid rgba(233,238,242,0.2);box-sizing:border-box;display:flex;align-items:center;justify-content:center;"><img src={lyrionIcon} alt="" style="width:5.4cqw;height:4cqw;display:block;" /></div><div style="position:absolute;left:-12cqw;width:24cqw;top:6.2cqw;text-align:center;font-family:'IBM Plex Mono','Courier New',monospace;font-size:1.8cqw;letter-spacing:0.16em;text-transform:uppercase;color:rgba(233,238,242,0.75);">Lyrion</div></div>
      </div>
      <div style="position:absolute;inset:0;z-index:2;opacity:0;animation:{flowAnim('plex')};display:{flowShow('plex')};">
        <span style="position:absolute;left:48cqw;top:38.5cqw;margin-left:-1cqw;margin-top:-2cqw;font-size:3cqw;line-height:1;color:#7ed6bc;opacity:0;animation:pmRiseB 2s ease-in-out 0ms infinite;">♪</span><span style="position:absolute;left:51.5cqw;top:38.5cqw;margin-left:-1cqw;margin-top:-2cqw;font-size:2.5cqw;line-height:1;color:#7ed6bc;opacity:0;animation:pmRiseA 2.5s ease-in-out 350ms infinite;">♫</span><span style="position:absolute;left:50cqw;top:38.5cqw;margin-left:-1cqw;margin-top:-2cqw;font-size:3.4cqw;line-height:1;color:#7ed6bc;opacity:0;animation:pmRiseB 1.8s ease-in-out 1100ms infinite;">♪</span><span style="position:absolute;left:49cqw;top:38.5cqw;margin-left:-1cqw;margin-top:-2cqw;font-size:2.7cqw;line-height:1;color:#7ed6bc;opacity:0;animation:pmRiseA 2.8s ease-in-out 1350ms infinite;">♩</span><span style="position:absolute;left:52cqw;top:38.5cqw;margin-left:-1cqw;margin-top:-2cqw;font-size:3cqw;line-height:1;color:#7ed6bc;opacity:0;animation:pmRiseB 2.2s ease-in-out 2200ms infinite;">♫</span>
        <div style="position:absolute;left:50cqw;top:45cqw;width:0;height:0;"><div style="position:absolute;left:-5cqw;top:-5cqw;width:10cqw;height:10cqw;border-radius:50%;border:0.18cqw solid rgba(233,238,242,0.5);box-sizing:border-box;animation:npRing 1800ms ease-out infinite;"></div><div style="position:absolute;left:-5cqw;top:-5cqw;width:10cqw;height:10cqw;border-radius:50%;background:rgba(16,26,33,0.92);border:1px solid rgba(233,238,242,0.2);box-sizing:border-box;display:flex;align-items:center;justify-content:center;"><span style="font-size:4.4cqw;font-weight:800;color:#e9eef2;line-height:1;">P</span></div><div style="position:absolute;left:-12cqw;width:24cqw;top:6.2cqw;text-align:center;font-family:'IBM Plex Mono','Courier New',monospace;font-size:1.8cqw;letter-spacing:0.16em;text-transform:uppercase;color:rgba(233,238,242,0.75);">Plexamp</div></div>
      </div>
      <div style="position:absolute;inset:0;z-index:2;opacity:0;animation:{flowAnim('spo')};display:{flowShow('spo')};">
        <span style="position:absolute;left:48cqw;top:38.5cqw;margin-left:-1cqw;margin-top:-2cqw;font-size:3cqw;line-height:1;color:#7ed6bc;opacity:0;animation:pmRiseA 2s ease-in-out 0ms infinite;">♪</span><span style="position:absolute;left:51.5cqw;top:38.5cqw;margin-left:-1cqw;margin-top:-2cqw;font-size:2.5cqw;line-height:1;color:#7ed6bc;opacity:0;animation:pmRiseB 2.5s ease-in-out 350ms infinite;">♫</span><span style="position:absolute;left:50cqw;top:38.5cqw;margin-left:-1cqw;margin-top:-2cqw;font-size:3.4cqw;line-height:1;color:#7ed6bc;opacity:0;animation:pmRiseA 1.8s ease-in-out 1100ms infinite;">♪</span><span style="position:absolute;left:49cqw;top:38.5cqw;margin-left:-1cqw;margin-top:-2cqw;font-size:2.7cqw;line-height:1;color:#7ed6bc;opacity:0;animation:pmRiseB 2.8s ease-in-out 1350ms infinite;">♩</span><span style="position:absolute;left:52cqw;top:38.5cqw;margin-left:-1cqw;margin-top:-2cqw;font-size:3cqw;line-height:1;color:#7ed6bc;opacity:0;animation:pmRiseA 2.2s ease-in-out 2200ms infinite;">♫</span>
        <div style="position:absolute;left:50cqw;top:45cqw;width:0;height:0;"><div style="position:absolute;left:-5cqw;top:-5cqw;width:10cqw;height:10cqw;border-radius:50%;border:0.18cqw solid rgba(233,238,242,0.5);box-sizing:border-box;animation:npRing 1800ms ease-out infinite;"></div><div style="position:absolute;left:-5cqw;top:-5cqw;width:10cqw;height:10cqw;border-radius:50%;background:rgba(16,26,33,0.92);border:1px solid rgba(233,238,242,0.2);box-sizing:border-box;display:flex;align-items:center;justify-content:center;"><img src={spotifyIcon} alt="" style="width:4.4cqw;height:4.4cqw;display:block;opacity:0.85;" /></div><div style="position:absolute;left:-12cqw;width:24cqw;top:6.2cqw;text-align:center;font-family:'IBM Plex Mono','Courier New',monospace;font-size:1.8cqw;letter-spacing:0.16em;text-transform:uppercase;color:rgba(233,238,242,0.75);">Spotify</div></div>
      </div>
      <div style="position:absolute;inset:0;z-index:2;opacity:0;animation:{flowAnim('bt')};display:{flowShow('bt')};">
        <span style="position:absolute;left:48cqw;top:38.5cqw;margin-left:-1cqw;margin-top:-2cqw;font-size:3cqw;line-height:1;color:#7ed6bc;opacity:0;animation:pmRiseB 2s ease-in-out 0ms infinite;">♪</span><span style="position:absolute;left:51.5cqw;top:38.5cqw;margin-left:-1cqw;margin-top:-2cqw;font-size:2.5cqw;line-height:1;color:#7ed6bc;opacity:0;animation:pmRiseA 2.5s ease-in-out 350ms infinite;">♫</span><span style="position:absolute;left:50cqw;top:38.5cqw;margin-left:-1cqw;margin-top:-2cqw;font-size:3.4cqw;line-height:1;color:#7ed6bc;opacity:0;animation:pmRiseB 1.8s ease-in-out 1100ms infinite;">♪</span><span style="position:absolute;left:49cqw;top:38.5cqw;margin-left:-1cqw;margin-top:-2cqw;font-size:2.7cqw;line-height:1;color:#7ed6bc;opacity:0;animation:pmRiseA 2.8s ease-in-out 1350ms infinite;">♩</span><span style="position:absolute;left:52cqw;top:38.5cqw;margin-left:-1cqw;margin-top:-2cqw;font-size:3cqw;line-height:1;color:#7ed6bc;opacity:0;animation:pmRiseB 2.2s ease-in-out 2200ms infinite;">♫</span>
        <div style="position:absolute;left:50cqw;top:45cqw;width:0;height:0;"><div style="position:absolute;left:-5cqw;top:-5cqw;width:10cqw;height:10cqw;border-radius:50%;border:0.18cqw solid rgba(233,238,242,0.5);box-sizing:border-box;animation:npRing 1800ms ease-out infinite;"></div><div style="position:absolute;left:-5cqw;top:-5cqw;width:10cqw;height:10cqw;border-radius:50%;background:rgba(16,26,33,0.92);border:1px solid rgba(233,238,242,0.2);box-sizing:border-box;display:flex;align-items:center;justify-content:center;"><img src={btIcon} alt="" style="width:4.4cqw;height:4.4cqw;display:block;opacity:0.85;" /></div><div style="position:absolute;left:-12cqw;width:24cqw;top:6.2cqw;text-align:center;font-family:'IBM Plex Mono','Courier New',monospace;font-size:1.8cqw;letter-spacing:0.16em;text-transform:uppercase;color:rgba(233,238,242,0.75);">Bluetooth</div></div>
      </div>
    </div>
  {/if}
  {#if V.kPhoto}
    <img src={V.photoSrc} alt="" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;display:block;" />
  {/if}
  {#if V.kSetup}
    <div style="position:absolute;inset:0;background:#0d151b;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2.6cqw;">
      <img src={mark} alt="" style="width:11cqw;height:11cqw;display:block;" />
      <div style="font-size:4.4cqw;font-weight:700;color:#e9eef2;">Join gexis-setup</div>
      <div style="font-family:'IBM Plex Mono','Courier New',monospace;font-size:2.4cqw;letter-spacing:0.16em;text-transform:uppercase;color:rgba(233,238,242,0.6);">on your phone’s Wi-Fi</div>
    </div>
  {/if}
  {#if V.kViz}<div style="position:absolute;inset:0;animation:{V.cviz};">
    <div style="position:absolute;inset:0;background:#0a1015;"></div>
    <div style="position:absolute;left:9%;right:9%;top:16%;bottom:16%;display:flex;align-items:flex-end;gap:1.6%;">
      <span style="flex:1;height:38%;border-radius:1px;background:#c8a2d8;display:block;transform-origin:50% 100%;animation:fuBar 0.8s ease-in-out infinite alternate;animation-delay:0s;"></span>
      <span style="flex:1;height:62%;border-radius:1px;background:#c8a2d8;display:block;transform-origin:50% 100%;animation:fuBar 0.8s ease-in-out infinite alternate;animation-delay:-0.17s;"></span>
      <span style="flex:1;height:80%;border-radius:1px;background:#c8a2d8;display:block;transform-origin:50% 100%;animation:fuBar 0.8s ease-in-out infinite alternate;animation-delay:-0.34s;"></span>
      <span style="flex:1;height:55%;border-radius:1px;background:#c8a2d8;display:block;transform-origin:50% 100%;animation:fuBar 0.8s ease-in-out infinite alternate;animation-delay:-0.51s;"></span>
      <span style="flex:1;height:92%;border-radius:1px;background:#c8a2d8;display:block;transform-origin:50% 100%;animation:fuBar 0.8s ease-in-out infinite alternate;animation-delay:-0.68s;"></span>
      <span style="flex:1;height:70%;border-radius:1px;background:#c8a2d8;display:block;transform-origin:50% 100%;animation:fuBar 0.8s ease-in-out infinite alternate;animation-delay:-0.05s;"></span>
      <span style="flex:1;height:48%;border-radius:1px;background:#c8a2d8;display:block;transform-origin:50% 100%;animation:fuBar 0.8s ease-in-out infinite alternate;animation-delay:-0.22s;"></span>
      <span style="flex:1;height:84%;border-radius:1px;background:#c8a2d8;display:block;transform-origin:50% 100%;animation:fuBar 0.8s ease-in-out infinite alternate;animation-delay:-0.39s;"></span>
      <span style="flex:1;height:66%;border-radius:1px;background:#c8a2d8;display:block;transform-origin:50% 100%;animation:fuBar 0.8s ease-in-out infinite alternate;animation-delay:-0.56s;"></span>
      <span style="flex:1;height:40%;border-radius:1px;background:#c8a2d8;display:block;transform-origin:50% 100%;animation:fuBar 0.8s ease-in-out infinite alternate;animation-delay:-0.73s;"></span>
      <span style="flex:1;height:74%;border-radius:1px;background:#c8a2d8;display:block;transform-origin:50% 100%;animation:fuBar 0.8s ease-in-out infinite alternate;animation-delay:-0.10s;"></span>
      <span style="flex:1;height:58%;border-radius:1px;background:#c8a2d8;display:block;transform-origin:50% 100%;animation:fuBar 0.8s ease-in-out infinite alternate;animation-delay:-0.27s;"></span>
      <span style="flex:1;height:88%;border-radius:1px;background:#c8a2d8;display:block;transform-origin:50% 100%;animation:fuBar 0.8s ease-in-out infinite alternate;animation-delay:-0.44s;"></span>
      <span style="flex:1;height:50%;border-radius:1px;background:#c8a2d8;display:block;transform-origin:50% 100%;animation:fuBar 0.8s ease-in-out infinite alternate;animation-delay:-0.61s;"></span>
    </div>
  </div>{/if}
  {#if V.kVu}<div style="position:absolute;inset:0;animation:{V.cvu};">
    <div style="position:absolute;inset:0;background:#1b140d;"></div>
    <div style="position:absolute;left:7%;right:7%;top:13%;bottom:13%;display:flex;gap:5%;">
      <div style="flex:1;position:relative;border-radius:2cqw;background:#eadfc4;overflow:hidden;box-shadow:inset 0 0 0 0.6cqw #3a2a1a;">
        <div style="position:absolute;left:-25%;width:150%;top:30%;aspect-ratio:1;border-radius:50%;border:0.5cqw solid #2a2016;box-sizing:border-box;"></div>
        <div style="position:absolute;left:-25%;width:150%;top:30%;aspect-ratio:1;border-radius:50%;border:1.1cqw solid transparent;border-top-color:#b8382b;box-sizing:border-box;transform:rotate(48deg);"></div>
        <div style="position:absolute;left:0;right:0;top:52%;text-align:center;font-size:3.4cqw;font-weight:800;color:#2a2016;">VU</div>
        <div style="position:absolute;left:50%;bottom:0;width:0.5cqw;margin-left:-0.25cqw;height:64%;background:#1a1410;transform-origin:50% 100%;animation:fuNeedleA 1.6s ease-in-out infinite alternate;"></div>
        <div style="position:absolute;left:0;right:0;bottom:0;height:14%;background:#2a2016;"></div>
      </div>
      <div style="flex:1;position:relative;border-radius:2cqw;background:#eadfc4;overflow:hidden;box-shadow:inset 0 0 0 0.6cqw #3a2a1a;">
        <div style="position:absolute;left:-25%;width:150%;top:30%;aspect-ratio:1;border-radius:50%;border:0.5cqw solid #2a2016;box-sizing:border-box;"></div>
        <div style="position:absolute;left:-25%;width:150%;top:30%;aspect-ratio:1;border-radius:50%;border:1.1cqw solid transparent;border-top-color:#b8382b;box-sizing:border-box;transform:rotate(48deg);"></div>
        <div style="position:absolute;left:0;right:0;top:52%;text-align:center;font-size:3.4cqw;font-weight:800;color:#2a2016;">VU</div>
        <div style="position:absolute;left:50%;bottom:0;width:0.5cqw;margin-left:-0.25cqw;height:64%;background:#1a1410;transform-origin:50% 100%;animation:fuNeedleB 1.9s ease-in-out infinite alternate;"></div>
        <div style="position:absolute;left:0;right:0;bottom:0;height:14%;background:#2a2016;"></div>
      </div>
    </div>
  </div>{/if}
  {#if V.kTurn}<div style="position:absolute;inset:0;animation:{V.cturn};">
    <div style="position:absolute;inset:0;background:linear-gradient(150deg,#3b2e21,#221a12);"></div>
    <div style="position:absolute;left:6.5%;top:7%;height:86%;aspect-ratio:1;border-radius:50%;background:#2e2e2e;box-shadow:0 1.4cqw 3cqw rgba(0,0,0,0.55);"></div>
    <div style="position:absolute;left:8.2%;top:9.8%;height:80.4%;aspect-ratio:1;border-radius:50%;background:repeating-radial-gradient(circle,#0e0e0e 0 0.5cqw,#262626 0.5cqw 0.8cqw);box-shadow:inset 0 0 0 0.5cqw #050505;animation:{V.spin};">
      <div style="position:absolute;left:33%;top:33%;width:34%;height:34%;border-radius:50%;background:conic-gradient(#f2a48f 0 180deg,#e9eef2 180deg 360deg);"></div>
      <div style="position:absolute;left:47.5%;top:47.5%;width:5%;height:5%;border-radius:50%;background:#1a1a1a;"></div>
    </div>
    <div style="position:absolute;left:8.2%;top:9.8%;height:80.4%;aspect-ratio:1;border-radius:50%;background:conic-gradient(from 20deg,transparent 0 30deg,rgba(255,255,255,0.13) 45deg,transparent 60deg 210deg,rgba(255,255,255,0.13) 225deg,transparent 240deg);"></div>
    <div style="position:absolute;left:78%;top:15%;width:7cqw;height:7cqw;margin:-3.5cqw 0 0 -3.5cqw;border-radius:50%;background:#3a3a3a;border:0.6cqw solid #9a9a9a;box-sizing:border-box;"></div>
    <div style="position:absolute;left:78%;top:15%;width:1.1cqw;margin-left:-0.55cqw;height:54%;background:#cfcfcf;border-radius:1cqw;transform-origin:50% 0;transform:rotate(42deg);"><div style="position:absolute;left:-1.1cqw;bottom:-1.2cqw;width:3.3cqw;height:4cqw;border-radius:0.6cqw;background:#e9eef2;"></div></div>
    <div style="position:absolute;right:6%;bottom:10%;font-family:'IBM Plex Mono','Courier New',monospace;font-size:3cqw;letter-spacing:0.14em;color:rgba(233,238,242,0.6);">{V.rpm}</div>
  </div>{/if}
  {#if V.kTape}<div style="position:absolute;inset:0;animation:{V.ctape};">
    <div style="position:absolute;inset:0;background:linear-gradient(150deg,#26221e,#15120f);"></div>
    <div style="position:absolute;left:13%;right:13%;top:13%;bottom:13%;border-radius:2.6cqw;background:#3d3834;box-shadow:inset 0 0 0 0.5cqw #4d4742,0 1.4cqw 3cqw rgba(0,0,0,0.5);">
      <div style="position:absolute;left:6%;right:6%;top:8%;height:64%;border-radius:1.6cqw;background:#e6d9bd;overflow:hidden;">
        <div style="position:absolute;left:0;right:0;top:12%;height:13%;background:#f2a48f;"></div>
        <div style="position:absolute;left:5%;top:12%;height:13%;display:flex;align-items:center;font-family:'IBM Plex Mono','Courier New',monospace;font-size:2.6cqw;font-weight:700;color:#2a2016;">A</div>
        <div style="position:absolute;left:16%;right:16%;top:36%;height:50%;border-radius:6cqw;background:#14110e;overflow:hidden;">
          <div style="position:absolute;left:21%;top:50%;width:15cqw;height:15cqw;margin:-7.5cqw 0 0 -7.5cqw;border-radius:50%;background:#4a2f1c;"></div>
          <div style="position:absolute;left:79%;top:50%;width:10cqw;height:10cqw;margin:-5cqw 0 0 -5cqw;border-radius:50%;background:#4a2f1c;"></div>
          <div style="position:absolute;left:21%;top:50%;width:8cqw;height:8cqw;margin:-4cqw 0 0 -4cqw;border-radius:50%;background:conic-gradient(#e9eef2 0 28deg,#2a2522 28deg 120deg,#e9eef2 120deg 148deg,#2a2522 148deg 240deg,#e9eef2 240deg 268deg,#2a2522 268deg);animation:{V.reel};"><div style="position:absolute;inset:36%;border-radius:50%;background:#14110e;"></div></div>
          <div style="position:absolute;left:79%;top:50%;width:8cqw;height:8cqw;margin:-4cqw 0 0 -4cqw;border-radius:50%;background:conic-gradient(#e9eef2 0 28deg,#2a2522 28deg 120deg,#e9eef2 120deg 148deg,#2a2522 148deg 240deg,#e9eef2 240deg 268deg,#2a2522 268deg);animation:{V.reel};"><div style="position:absolute;inset:36%;border-radius:50%;background:#14110e;"></div></div>
        </div>
      </div>
      <div style="position:absolute;left:24%;right:24%;bottom:0;height:20%;border-radius:1.6cqw 1.6cqw 0 0;background:#2f2b27;"></div>
    </div>
  </div>{/if}
  {#if V.kVs}
    <div style="position:absolute;inset:0;background:#17120d;"></div>
    <div style="position:absolute;left:8%;right:8%;top:10%;height:44%;display:flex;gap:5%;">
      <div style="flex:1;position:relative;border-radius:1.6cqw;background:#eadfc4;overflow:hidden;box-shadow:inset 0 0 0 0.5cqw #3a2a1a;"><div style="position:absolute;left:-10%;width:120%;top:30%;aspect-ratio:1;border-radius:50%;border:0.4cqw solid #2a2016;box-sizing:border-box;"></div><div style="position:absolute;left:50%;bottom:0;width:0.45cqw;margin-left:-0.22cqw;height:78%;background:#1a1410;transform-origin:50% 100%;animation:fuNeedleA 1.6s ease-in-out infinite alternate;"></div></div>
      <div style="flex:1;position:relative;border-radius:1.6cqw;background:#eadfc4;overflow:hidden;box-shadow:inset 0 0 0 0.5cqw #3a2a1a;"><div style="position:absolute;left:-10%;width:120%;top:30%;aspect-ratio:1;border-radius:50%;border:0.4cqw solid #2a2016;box-sizing:border-box;"></div><div style="position:absolute;left:50%;bottom:0;width:0.45cqw;margin-left:-0.22cqw;height:78%;background:#1a1410;transform-origin:50% 100%;animation:fuNeedleB 1.9s ease-in-out infinite alternate;"></div></div>
    </div>
    <div style="position:absolute;left:8%;right:8%;bottom:10%;height:28%;display:flex;align-items:flex-end;gap:1.4%;">
      <span style="flex:1;height:40%;border-radius:1px;background:#e0a758;display:block;transform-origin:50% 100%;animation:fuBar 0.8s ease-in-out infinite alternate;animation-delay:0s;"></span>
      <span style="flex:1;height:66%;border-radius:1px;background:#e0a758;display:block;transform-origin:50% 100%;animation:fuBar 0.8s ease-in-out infinite alternate;animation-delay:-0.17s;"></span>
      <span style="flex:1;height:84%;border-radius:1px;background:#e0a758;display:block;transform-origin:50% 100%;animation:fuBar 0.8s ease-in-out infinite alternate;animation-delay:-0.34s;"></span>
      <span style="flex:1;height:58%;border-radius:1px;background:#e0a758;display:block;transform-origin:50% 100%;animation:fuBar 0.8s ease-in-out infinite alternate;animation-delay:-0.51s;"></span>
      <span style="flex:1;height:92%;border-radius:1px;background:#e0a758;display:block;transform-origin:50% 100%;animation:fuBar 0.8s ease-in-out infinite alternate;animation-delay:-0.68s;"></span>
      <span style="flex:1;height:72%;border-radius:1px;background:#e0a758;display:block;transform-origin:50% 100%;animation:fuBar 0.8s ease-in-out infinite alternate;animation-delay:-0.05s;"></span>
      <span style="flex:1;height:50%;border-radius:1px;background:#e0a758;display:block;transform-origin:50% 100%;animation:fuBar 0.8s ease-in-out infinite alternate;animation-delay:-0.22s;"></span>
      <span style="flex:1;height:86%;border-radius:1px;background:#e0a758;display:block;transform-origin:50% 100%;animation:fuBar 0.8s ease-in-out infinite alternate;animation-delay:-0.39s;"></span>
      <span style="flex:1;height:64%;border-radius:1px;background:#e0a758;display:block;transform-origin:50% 100%;animation:fuBar 0.8s ease-in-out infinite alternate;animation-delay:-0.56s;"></span>
      <span style="flex:1;height:44%;border-radius:1px;background:#e0a758;display:block;transform-origin:50% 100%;animation:fuBar 0.8s ease-in-out infinite alternate;animation-delay:-0.73s;"></span>
      <span style="flex:1;height:76%;border-radius:1px;background:#e0a758;display:block;transform-origin:50% 100%;animation:fuBar 0.8s ease-in-out infinite alternate;animation-delay:-0.10s;"></span>
      <span style="flex:1;height:56%;border-radius:1px;background:#e0a758;display:block;transform-origin:50% 100%;animation:fuBar 0.8s ease-in-out infinite alternate;animation-delay:-0.27s;"></span>
      <span style="flex:1;height:88%;border-radius:1px;background:#e0a758;display:block;transform-origin:50% 100%;animation:fuBar 0.8s ease-in-out infinite alternate;animation-delay:-0.44s;"></span>
      <span style="flex:1;height:48%;border-radius:1px;background:#e0a758;display:block;transform-origin:50% 100%;animation:fuBar 0.8s ease-in-out infinite alternate;animation-delay:-0.61s;"></span>
    </div>
  {/if}
  {#if V.kCode}
    <div style="position:absolute;inset:0;background:#0d151b;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:3.6cqw;">
      <div style="font-family:'IBM Plex Mono','Courier New',monospace;font-size:1.8cqw;letter-spacing:0.34em;text-transform:uppercase;color:rgba(233,238,242,0.5);">Pairing request</div>
      <div style="display:flex;flex-direction:column;align-items:center;gap:2.4cqw;">
        <div style="position:relative;width:15.5cqw;height:15.5cqw;display:flex;align-items:center;justify-content:center;flex-shrink:0;">
          <div style="position:absolute;inset:0;border-radius:50%;border:0.25cqw solid #9fb4e8;animation:fuRing 2800ms ease-out 0ms infinite;"></div>
          <div style="position:absolute;inset:0;border-radius:50%;border:0.25cqw solid #9fb4e8;animation:fuRing 2800ms ease-out 1400ms infinite;"></div>
          <div style="position:absolute;inset:0;border-radius:50%;border:0.25cqw solid #9fb4e8;background:rgba(159,180,232,0.14);box-shadow:0 0 5cqw rgba(159,180,232,0.2);display:flex;align-items:center;justify-content:center;"><img src={btIcon} alt="" style="width:6cqw;height:6cqw;display:block;" /></div>
        </div>
        <div style="font-size:3.5cqw;font-weight:700;color:#e9eef2;white-space:nowrap;">{V.phone}</div>
      </div>
      <div style="display:flex;flex-direction:column;align-items:center;gap:1.4cqw;">
        <div style="font-family:'IBM Plex Mono','Courier New',monospace;font-size:1.6cqw;letter-spacing:0.22em;text-transform:uppercase;color:rgba(233,238,242,0.6);">Code on your phone</div>
        <div style="font-family:'IBM Plex Mono','Courier New',monospace;font-size:8.4cqw;font-weight:700;letter-spacing:0.16em;color:#9fb4e8;line-height:1;">418 205</div>
      </div>
      <div style="font-family:'IBM Plex Mono','Courier New',monospace;font-size:1.5cqw;letter-spacing:0.16em;text-transform:uppercase;color:rgba(233,238,242,0.6);">Expires in {V.secs}</div>
    </div>
  {/if}
  {#if V.kCustom}
    <div style="position:absolute;inset:12%;border:2px dashed rgba(233,238,242,0.28);border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:12cqw;font-weight:300;color:rgba(233,238,242,0.55);">+</div>
  {/if}
  {#if p.kind === 'flow' && p.status}
    <div style="position:absolute;left:61.4cqw;top:2.9cqw;z-index:4;width:8.2cqw;height:8.2cqw;border-radius:50%;box-sizing:border-box;display:flex;align-items:center;justify-content:center;font-size:4.6cqw;font-weight:800;line-height:1;box-shadow:0 0 0 1cqw #0d151b;background:{p.status === 'done' ? '#7ed6bc' : p.status === 'warn' ? '#e0a758' : '#0d151b'};color:#0d151c;border:{p.status === 'busy' ? '0.3cqw solid rgba(126,214,188,0.55)' : 'none'};">
      {#if p.status === 'done'}✓{:else if p.status === 'warn'}!{:else}<span style="width:5cqw;height:5cqw;border-radius:50%;border:0.75cqw solid rgba(233,238,242,0.16);border-top-color:#7ed6bc;box-sizing:border-box;display:block;animation:fuSpin 0.9s linear infinite;"></span>{/if}
    </div>
  {/if}
  {#if p.pointer}
    <div style="position:absolute;inset:0;z-index:30;pointer-events:none;">
      <span style="position:absolute;width:4.6cqw;height:4.6cqw;margin:-2.3cqw 0 0 -2.3cqw;animation:tpMove 6.4s cubic-bezier(0.45,0,0.25,1) infinite;">
        <span style="position:absolute;inset:0;border-radius:999px;border:0.55cqw solid #7ed6bc;box-sizing:border-box;opacity:0;animation:tpRing 6.4s ease-out infinite;"></span>
        <span style="position:absolute;inset:0;border-radius:999px;background:#7ed6bc;border:0.45cqw solid #0c1014;box-sizing:border-box;animation:tpPress 6.4s ease-out infinite;"></span>
      </span>
    </div>
  {/if}
</div>

<style>
  :global {

  @keyframes fuSpin{to{transform:rotate(360deg);}}
  @keyframes fuNeedleA{0%{transform:rotate(-42deg);}30%{transform:rotate(6deg);}50%{transform:rotate(-14deg);}78%{transform:rotate(24deg);}100%{transform:rotate(-4deg);}}
  @keyframes fuNeedleB{0%{transform:rotate(-30deg);}28%{transform:rotate(18deg);}58%{transform:rotate(-20deg);}84%{transform:rotate(12deg);}100%{transform:rotate(-38deg);}}
  @keyframes fuBar{0%{transform:scaleY(0.3);}100%{transform:scaleY(1);}}
  @keyframes fuRing{0%{transform:scale(0.82);opacity:0.55;}100%{transform:scale(1.75);opacity:0;}}
  @keyframes wxSpin{to{transform:rotate(360deg);}}
  @keyframes wxDrift{0%,100%{transform:translateX(-0.23cqw);}50%{transform:translateX(0.23cqw);}}
  @keyframes wxFall{0%{transform:translateY(-0.3cqw);opacity:0;}30%{opacity:1;}100%{transform:translateY(0.94cqw);opacity:0;}}
  @keyframes wxPulse{0%,100%{opacity:0.55;}50%{opacity:1;}}
  @keyframes npRing{0%{transform:scale(0.82);opacity:0.55;}100%{transform:scale(1.75);opacity:0;}}
  @keyframes pmRiseA{0%{transform:translate(0,0) scale(0.6);opacity:0;}12%{opacity:1;}50%{transform:translate(-3cqw,-12cqw) scale(1);}85%{opacity:1;}100%{transform:translate(0,-24cqw) scale(0.7);opacity:0;}}
  @keyframes pmRiseB{0%{transform:translate(0,0) scale(0.6);opacity:0;}12%{opacity:1;}50%{transform:translate(3cqw,-12cqw) scale(1);}85%{opacity:1;}100%{transform:translate(0,-24cqw) scale(0.7);opacity:0;}}
  @keyframes pmPump{0%,100%{transform:scale(0.86);}50%{transform:scale(1.06);}}
  @keyframes fuCycle{0%,22%{opacity:1;}25%,97%{opacity:0;}100%{opacity:1;}}

  @keyframes fuCycle1{0%,100%{opacity:1;}}
  @keyframes fuCycle2{0%,44%{opacity:1;}50%,94%{opacity:0;}100%{opacity:1;}}
  @keyframes fuCycle3{0%,29.3%{opacity:1;}33.3%,96%{opacity:0;}100%{opacity:1;}}

  @keyframes tpMove{0%{left:74%;top:84%;}20%,32%{left:32.8%;top:27%;}50%,62%{left:67.2%;top:27%;}80%,90%{left:40%;top:82%;}100%{left:74%;top:84%;}}
  @keyframes tpPress{0%,21%,27%,51%,57%,81%,87%,100%{transform:scale(1);}24%,54%,84%{transform:scale(0.7);}}
  @keyframes tpRing{0%,23%{transform:scale(0.8);opacity:0;}24%{opacity:0.95;}36%{transform:scale(2.6);opacity:0;}53%{transform:scale(0.8);opacity:0;}54%{opacity:0.95;}66%{transform:scale(2.6);opacity:0;}83%{transform:scale(0.8);opacity:0;}84%{opacity:0.95;}96%{transform:scale(2.6);opacity:0;}100%{opacity:0;}}

  }
</style>
