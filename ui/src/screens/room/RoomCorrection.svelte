<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  Settings → Audio → Room correction (ADR-0175, ADR-0177; design/source/29
  R28-R35, N01-N07, B01-B04, B07; design/source/30 1a, 1d, 1g): on or off for
  the output in use, how far it reaches (*Bass* or *Full range*), *Hear it
  without* (the A/B: tagged, set apart, amber when set), the last measurement
  with its corrections and its chart, and Measure again.

  The phone measures (RoomFlow); the panel and the bars send the owner to
  the phone with a sheet - a QR code that opens this page there, and the
  player's address. Nothing on them starts a run.
-->
<script>
  import { encode } from 'uqr';
  import { onDestroy } from 'svelte';
  import { BOTH, capitalised, chartSpan, correctionGroups, correctionsWho, countWord, cutFreq, cutGain, cutRows,
    outputPhrase, outputShort, rangeWord, resultWords, room, RoomReader, setRoom, sideName, sides } from '../../lib/room.svelte.js';
  import { screen } from '../../lib/family.svelte.js';
  import RoomChart from './RoomChart.svelte';
  import RoomFlow from './RoomFlow.svelte';

  let { surface = 'panel', onback, onhome = null, flat = false } = $props();

  const phone = $derived(surface === 'phone');
  const bar = $derived(surface === 'bar');
  const reader = new RoomReader();
  //: On the phone's Before, the microphone and its file are looked for
  //: every two seconds: plugging it in moves nothing else.
  let view = $state(null);   // phone: 'page' | 'flow'
  const summary = $derived($room);
  const full = $derived(reader.full);
  $effect(() => {
    reader.follow(summary, phone && view === 'flow' && !summary?.run);
  });
  onDestroy(() => reader.stop());

  const measured = $derived(full?.measured ?? null);
  //: The phone opens on Before when never measured, and on the flow while a
  //: run goes on or its end is still to be shown.
  $effect(() => {
    if (!phone || !full) return;
    if (full.run || (full.ended && ['cancelled', 'failed'].includes(full.ended.how))) view = 'flow';
    else if (view === null) view = measured ? 'page' : 'flow';
  });

  let error = $state(null);
  let ch = $state('L');
  let sheet = $state(false);
  //: The switches move from the press; the core's word wins in the end.
  let wantOn = $state(null);
  let wantAb = $state(null);
  let wantReach = $state(null);
  const on = $derived(wantOn ?? !!full?.on);
  const ab = $derived((wantAb ?? !!full?.without) && on);
  const reach = $derived(wantReach ?? full?.reach ?? 'full');
  $effect(() => {
    if (wantOn !== null && !!full?.on === wantOn) wantOn = null;
    if (wantAb !== null && !!full?.without === wantAb) wantAb = null;
    if (wantReach !== null && full?.reach === wantReach) wantReach = null;
  });
  const dsd = $derived(!!full?.dsd);
  const abLive = $derived(on && !!measured && !dsd);
  //: How far the measurement was made: one from before Phase 30 covers the
  //: bass only, and holds the reach at Bass until the room is measured again.
  const range = $derived(measured?.range ?? 'full');
  const bassOnly = $derived(!!measured && range !== 'full');
  const reachLive = $derived(on && !!measured && !dsd);

  async function change(key, value) {
    error = null;
    if (key === 'on') wantOn = value;
    else if (key === 'reach') wantReach = value;
    else wantAb = value;
    try {
      reader.full = await setRoom({ [key]: value });
    } catch (e) {
      error = e.message;
    } finally {
      wantOn = null;
      wantAb = null;
      wantReach = null;
    }
  }
  const toggleOn = () => measured && change('on', !on);
  const toggleAb = () => abLive && change('without', !ab);
  //: The Reaches chips (the design's 1a): a tap is heard at once. Full range
  //: on a bass-only measurement asks for the room measured again - Before on
  //: the phone, the phone's sheet on the panel and the bars.
  function chooseReach(k) {
    if (!reachLive) return;
    if (k === 'full' && bassOnly) {
      if (phone) view = 'flow';
      else sheet = true;
      return;
    }
    if (k !== reach) change('reach', k);
  }
  const REACHES = [['bass', 'Bass', 'Up to 250 Hz'], ['full', 'Full range', '15 Hz to 20 kHz']];

  const chart = $derived(full?.chart ?? null);
  //: A measurement from before both were swept has no Both tab.
  $effect(() => {
    if (chart && !sides(chart).includes(ch)) ch = 'L';
  });
  const both = $derived(ch === BOTH);
  const speaker = $derived(chart?.speakers?.[ch] ?? null);
  const bothAfter = $derived(both && !!speaker?.after?.length);
  const kind = $derived(chart?.after_kind ?? 'measured');
  const notChecked = $derived(!!measured && !measured.checked);
  //: The corrections in two groups (the design's 1g), for the speaker shown.
  const groups = $derived(correctionGroups(ch, speaker, { range, reach }));
  const cutsWho = $derived(correctionsWho(ch, groups[0]?.rows.length ?? 0, groups[1]?.rows.length ?? 0));
  //: The speaker shown: its own numbers, not the larger of the two.
  const words = $derived(resultWords({ speaker, both, range, reach, expectedMark: notChecked }));
  const resultHead = $derived(words[0]);
  const resultLine = $derived(words[1]);
  const span = $derived(chartSpan(chart));
  const positionsWord = $derived(countWord(measured?.positions ?? 0));
  const abSub = $derived(!on ? 'Only while room correction is on.'
    : ab ? 'Now without: no correction at all. Switch back to hear it.'
      : 'Compare: no correction at all, heard at once. Stays where you put it.');
  const abShort = $derived(!on ? 'Only while room correction is on.' : ab ? 'Now without: no correction at all' : 'Compare, heard at once');
  const againLabel = $derived(bassOnly ? 'Measure again for the full range' : 'Measure again');
  const powerNote = $derived(on ? `For ${outputPhrase(full?.output)}. Each output keeps its own.`
    : 'Off: the correction is taken out. With the equaliser also off, the sound is untouched, bit-perfect.');

  //: The sheet's code: the player's page for a phone, opened at Room correction.
  function qrPath(text) {
    const { data, size } = encode(text, { ecc: 'M' });
    let d = '';
    for (let y = 0; y < size; y++)
      for (let x = 0; x < size; x++) if (data[y][x]) d += `M${x + 4} ${y + 4}h1v1h-1z`;
    return { d, extent: size + 8 };
  }
  const qr = $derived(full?.address ? qrPath(full.address.url) : null);
  const wideBar = $derived(screen.width > 1500);
  //: The lead the design gives Before, the panel and the bars when never
  //: measured.
  const LEAD = "The player plays sweeps through your speakers and listens with a measurement microphone at your seat. It cuts the peaks your room adds to the bass, and above the bass evens out the room's broad bumps and dips by 3 dB at most, so your speakers keep their own balance.";
</script>

{#snippet sw(lit, amber)}
  <span class="switch" class:is-on={lit} class:is-amber={amber}><span></span></span>
{/snippet}

{#snippet abCard(size)}
  <button type="button" class="ab ab--{size}" class:is-without={ab} class:is-off={!abLive} aria-pressed={ab}
          onclick={toggleAb} disabled={!abLive}>
    {#if size === 'panel'}
      <span class="ab__row">
        <span class="tag">A/B</span>
        <span class="ab__title">Hear it without</span>
        {@render sw(ab, true)}
      </span>
      <span class="ab__sub">{abSub}</span>
    {:else}
      <span class="tag">A/B</span>
      <span class="ab__text">
        <span class="ab__title">Hear it without</span>
        <span class="ab__sub">{size === 'bar' ? abShort : abSub}</span>
      </span>
      {@render sw(ab, true)}
    {/if}
  </button>
{/snippet}

{#snippet dsdBanner(size)}
  {#if dsd}
    <div class="dsd dsd--{size}"><span class="dsd__tag">DSD</span>
      <span>DSD plays untouched. Room correction stands aside for this track and is back for the next PCM one.</span></div>
  {/if}
{/snippet}

{#snippet segs(size)}
  <div class="segs segs--{size}" role="group" aria-label="Speaker">
    {#each sides(chart) as k (k)}
      <button type="button" class="segbtn" class:is-sel={ch === k} aria-pressed={ch === k} onclick={() => (ch = k)}>{sideName(k)}</button>
    {/each}
  </div>
{/snippet}

{#snippet reaches(size)}
  <div class="reach reach--{size}" class:is-off={!reachLive} role="group" aria-label="How far it reaches">
    {#each REACHES as [k, name, sub] (k)}
      {@const locked = k === 'full' && bassOnly}
      <button type="button" class="chip" class:is-sel={reach === k} class:is-locked={locked} aria-pressed={reach === k}
              onclick={() => chooseReach(k)} disabled={!reachLive}>
        <!-- George, 2026-11-10: Full range is marked as being tested, in
             AirPlay's words and the Tested tag's look (ADR-0167). -->
        {#if k === 'full'}<span class="testing">Limited testing</span>{/if}
        <span class="chip__name">{name}</span>
        <span class="chip__sub">{locked ? 'Measure again' : sub}</span>
      </button>
    {/each}
  </div>
{/snippet}

{#snippet corrections(size)}
  <span class="who who--{size}">{cutsWho}</span>
  {#each groups as g, i (g.name)}
    <div class="group group--{size}" class:group--first={i === 0}>
      <span class="group__name">{g.name}</span><span class="rule"></span><span class="group__kind">{g.kind}</span>
    </div>
    {#if g.rows.length}
      <div class="rows rows--{size}">
        {#each g.rows as c, j (j)}
          <div class="cut"><span class="cut__f">{cutFreq(c)}</span><span class="cut__g" class:is-up={c.gain > 0}>{cutGain(c)}</span></div>
        {/each}
      </div>
    {:else}
      <div class="empty empty--{size}">{g.empty}</div>
    {/if}
  {/each}
{/snippet}

{#snippet phoneGlyph()}
  <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="7" y="2.5" width="10" height="19" rx="2.5"></rect><path d="M11 18.5h2"></path></svg>
{/snippet}

{#if phone && view === 'flow' && full}
  <RoomFlow {full} {flat} onback={() => onback?.()} onpage={() => (view = 'page')} />
{:else}
  <div class="room room--{surface}" class:room--flat={flat} data-dpad-layer>
    {#if bar}
      <div class="ground ground--bar"></div><div class="veil veil--bar"></div>
    {:else if !flat}
      <div class="weave"></div><div class="veil"></div>
    {/if}

    {#if !full}
      <div class="frame">
        <div class="top">
          <button class="back" type="button" aria-label="Back" data-dpad-back onclick={() => onback?.()}><span></span></button>
          <div class="top__text"><div class="title">Room correction</div></div>
        </div>
        {#if reader.error}<p class="none">{reader.error}</p>{/if}
      </div>
    {:else if phone}
      <div class="frame">
        <div class="top top--phone">
          <button class="back" type="button" aria-label="Back" data-dpad-back onclick={() => onback?.()}><span></span></button>
          <div class="top__text">
            <div class="title title--phone">Room correction</div>
            <div class="crumb">Settings · Audio · {outputShort(full.output)}</div>
          </div>
        </div>
        <div class="scroll">
          {@render dsdBanner('phone')}
          <div class="card powercard">
            <button type="button" class="power" aria-pressed={on} onclick={toggleOn}>
              <span class="power__text">
                <span class="power__title">Room correction</span>
                <span class="power__note">{powerNote}</span>
              </span>
              {@render sw(on && !!measured, false)}
            </button>
            <div class="powercard__rule"></div>
            <span class="label label--phone">Reaches</span>
            {@render reaches('phone')}
            {#if bassOnly}
              <div class="reach__note">This measurement covers the bass only. Measure again to reach the full range.</div>
            {/if}
          </div>
          {@render abCard('phone')}
          <div class="card measuredcard">
            <div class="power__text">
              <div class="power__title">Measured</div>
              <div class="power__note">{measured?.year} · {positionsWord} positions · {rangeWord(range)}</div>
            </div>
            {#if notChecked}<span class="flag">Not checked</span>{/if}
          </div>
          {@render segs('phone')}
          <div class="card chartcard" class:is-dim={dsd || !on}>
            <div class="chartcard__head">
              <div class="chartcard__title">{resultHead}</div>
              <div class="chartcard__line">{resultLine}</div>
            </div>
            <RoomChart surface="phone" freqs={chart?.freqs ?? []} {speaker} {kind} {span} {reach} {range} />
          </div>
          <button type="button" class="again" class:is-lit={bassOnly} onclick={() => (view = 'flow')}>{againLabel}</button>
          {#if error}<div class="error" role="status">{error}</div>{/if}
        </div>
      </div>
    {:else if bar}
      <div class="frame frame--bar">
        <div class="side">
          <div class="side__buttons">
            <button class="back back--bar" type="button" aria-label="Back" data-dpad-back onclick={() => onback?.()}><span></span></button>
            {#if onhome}
              <button class="home" type="button" aria-label="Home" onclick={() => onhome()}><span class="grid"><i></i><i></i><i></i><i></i></span></button>
            {/if}
          </div>
          <div class="title title--bar">Room correction</div>
          <div class="crumb crumb--bar">Audio · {outputShort(full.output)}</div>
          <div class="side__rest"></div>
          <button type="button" class="powerbtn powerbtn--bar" class:is-dim={!measured} aria-pressed={on}
                  onclick={toggleOn} disabled={!measured}>
            <span class="powerbtn__state" class:is-on={on && measured}>{!measured ? 'Off' : on ? 'On' : 'Off'}</span>
            {@render sw(on && !!measured, false)}
          </button>
        </div>
        <div class="mid" class:mid--narrow={!wideBar}>
          {#if measured}{@render reaches('bar')}{/if}
          {@render abCard('bar')}
          <div class="mcard">
            <span class="mcard__text">
              <span class="mcard__title">{measured ? measured.year : 'Not measured yet'}</span>
              <span class="mcard__sub">{measured ? `${capitalised(positionsWord)} positions · ${rangeWord(range)}` : 'Measure from your phone'}</span>
            </span>
            {#if notChecked}<span class="flag flag--bar">Not checked</span>{/if}
          </div>
          <div class="spacer"></div>
          <button type="button" class="againbtn againbtn--bar" class:is-lit={!measured || bassOnly} onclick={() => (sheet = true)}>
            {@render phoneGlyph()}{!measured ? 'Measure from your phone' : bassOnly && wideBar ? againLabel : 'Measure again'}
          </button>
        </div>
        <div class="right" class:right--narrow={!wideBar}>
          {#if measured}
            <div class="right__head">
              <div class="right__text">
                <span class="right__title">{resultHead}</span>
                <span class="right__line">{resultLine}</span>
              </div>
              {@render segs('bar')}
            </div>
            <div class="chartbar" class:is-dim={dsd || !on}>
              <RoomChart surface="bar" freqs={chart?.freqs ?? []} {speaker} {kind} {span} {reach} {range} />
            </div>
          {:else}
            <div class="never never--bar">
              <div class="never__title">Correct what your room adds to the sound</div>
              <div class="never__text">{LEAD} You measure from the phone.</div>
            </div>
          {/if}
        </div>
      </div>
    {:else}
      <div class="frame">
        <div class="top">
          <button class="back" type="button" aria-label="Back" data-dpad-back onclick={() => onback?.()}><span></span></button>
          <div class="top__text">
            <div class="title">Room correction</div>
            <div class="crumb">Audio · for {outputPhrase(full.output)} · each output keeps its own</div>
          </div>
          {#if dsd}
            <div class="dsdpill"><span class="dsd__tag">DSD</span><span>Plays untouched. Room correction stands aside.</span></div>
          {/if}
          <button type="button" class="powerbtn" class:is-dim={!measured} aria-pressed={on} onclick={toggleOn} disabled={!measured}>
            <span class="powerbtn__state" class:is-on={on && measured}>{!measured ? 'Measure first' : on ? 'On' : 'Off · bit-perfect'}</span>
            {@render sw(on && !!measured, false)}
          </button>
        </div>
        <div class="body">
          <div class="left">
            {#if measured}
              <div class="rcard">
                <span class="label">Reaches</span>
                {@render reaches('panel')}
              </div>
            {/if}
            {@render abCard('panel')}
            <div class="lcard">
              <div class="label"><span>Last measurement</span><span class="rule"></span></div>
              {#if measured}
                <div class="lcard__when">
                  <span class="lcard__text"><span class="lcard__date">{measured.year}</span><span class="lcard__pos">{capitalised(positionsWord)} positions · {rangeWord(range)}</span></span>
                  {#if notChecked}<span class="flag flag--panel">Not checked</span>{/if}
                </div>
                {@render corrections('panel')}
              {:else}
                <div class="lcard__never">Not measured yet</div>
              {/if}
            </div>
            <button type="button" class="againbtn" class:is-lit={!measured || bassOnly} onclick={() => (sheet = true)}>
              {@render phoneGlyph()}{measured ? againLabel : 'Measure from your phone'}
            </button>
          </div>
          <div class="card chartpanel" class:is-dim={!!measured && (dsd || !on)}>
            {#if measured}
              <div class="chartpanel__head">
                <div class="chartpanel__text">
                  <div class="chartpanel__title">{resultHead}</div>
                  <div class="chartpanel__line">{resultLine}</div>
                </div>
                {@render segs('panel')}
              </div>
              <RoomChart surface="panel" freqs={chart?.freqs ?? []} {speaker} {kind} {span} {reach} {range} />
            {:else}
              <div class="never">
                <div class="never__title">Correct what your room adds to the sound</div>
                <div class="never__text">{LEAD}</div>
                <div class="never__text">You measure from the phone, which you hold at the seat while you move the microphone. This screen shows that it is running.</div>
              </div>
            {/if}
          </div>
        </div>
      </div>
    {/if}

    {#if error && !phone}<div class="toast" role="status">{error}</div>{/if}

    {#if sheet}
      <div class="scrim" role="presentation" onclick={() => (sheet = false)}></div>
      <div class="sheet" class:sheet--bar={bar} role="dialog" aria-label="Measure from your phone"
           ondpadback={(event) => { event.preventDefault(); sheet = false; }}>
        {#if qr}
          <svg class="qr" viewBox="0 0 {qr.extent} {qr.extent}" shape-rendering="crispEdges"
               aria-label={`QR code to open ${full?.address?.shown ?? ''}`}>
            <rect width={qr.extent} height={qr.extent} fill="#e9eef2" />
            <path d={qr.d} fill="#101a21" />
          </svg>
        {:else}
          <div class="qr qr--empty"></div>
        {/if}
        <div class="sheet__text">
          <div class="sheet__title">Measure from your phone</div>
          <div class="sheet__note">You hold the phone at the seat while you move the microphone. Scan this, or open the player's page and go to Settings · Audio · Room correction.</div>
          {#if bar}
            <div class="sheet__row">
              <span class="sheet__addr">{full?.address?.shown ?? ''}</span>
              <button type="button" class="sheet__close" data-dpad-back onclick={() => (sheet = false)}>Close</button>
            </div>
          {:else}
            <div class="sheet__addr">{full?.address?.shown ?? ''}</div>
            <div class="spacer"></div>
            <div class="sheet__actions">
              <button type="button" class="sheet__close" data-dpad-back onclick={() => (sheet = false)}>Close</button>
            </div>
          {/if}
        </div>
      </div>
    {/if}
  </div>
{/if}

<style>
  .room {
    position: absolute;
    inset: 0;
    z-index: 30;
    overflow: hidden;
    background: var(--bg-base);
    color: var(--ink);
    -webkit-tap-highlight-color: transparent;
    user-select: none;
  }
  .room--phone {
    z-index: 18;
  }
  .room--flat {
    background: var(--bg-panel);
  }
  .weave {
    position: absolute;
    inset: -90px;
    background: repeating-linear-gradient(var(--weave-angle), var(--bg-weave-a) 0 48px, var(--bg-weave-b) 48px 96px);
    filter: blur(70px);
    transform: scale(1.14);
  }
  .ground--bar {
    position: absolute;
    inset: 0;
    background: var(--c-weave-m);
  }
  .veil {
    position: absolute;
    inset: 0;
    background: var(--cover-veil-deep);
  }
  .veil--bar {
    background: var(--cover-veil-strong);
  }
  .frame {
    position: relative;
    height: 100%;
    display: flex;
    flex-direction: column;
    min-height: 0;
  }
  .frame--bar {
    flex-direction: row;
  }
  .none {
    padding: 40px 36px;
    font-size: 19px;
    color: var(--ink-muted);
  }
  .spacer {
    flex: 1;
  }

  /* -- the head -- */
  .top {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 18px;
    padding: 0 36px;
    min-height: 92px;
    border-bottom: 1px solid var(--c-ink-09);
  }
  .top--phone {
    gap: 16px;
    padding: 14px 18px;
    min-height: 78px;
  }
  .top__text {
    flex: 1;
    min-width: 0;
  }
  .title {
    font-size: 25px;
    font-weight: 700;
    letter-spacing: -0.01em;
    white-space: nowrap;
  }
  .title--phone {
    font-size: 23px;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .title--bar {
    font-size: 26px;
    margin-top: 8px;
    line-height: 1.15;
    white-space: normal;
  }
  .crumb {
    font-family: var(--font-mono);
    font-size: 13px;
    letter-spacing: 0.06em;
    color: var(--ink-quiet);
    margin-top: 4px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .crumb--bar {
    font-size: 15px;
    margin-top: 0;
  }
  .back,
  .home {
    width: 56px;
    height: 56px;
    border-radius: 50%;
    flex-shrink: 0;
    border: 0;
    padding: 0;
    background: var(--ink-fill);
    display: flex;
    align-items: center;
    justify-content: center;
    color: inherit;
  }
  .back span {
    width: 13px;
    height: 13px;
    border-left: 3px solid var(--ink);
    border-bottom: 3px solid var(--ink);
    transform: rotate(45deg);
    margin-left: 10px;
  }
  .back--bar,
  .home {
    width: 60px;
    height: 60px;
  }
  .back--bar span {
    width: 14px;
    height: 14px;
    margin-left: 11px;
  }
  .grid {
    width: 22px;
    height: 22px;
    display: grid;
    grid-template-columns: 1fr 1fr;
    grid-template-rows: 1fr 1fr;
    gap: 3.5px;
  }
  .grid i {
    border-radius: 2px;
    background: var(--c-ink-85);
  }
  .back:active,
  .home:active {
    transform: scale(0.95);
  }

  /* -- switches -- */
  .switch {
    width: 60px;
    height: 34px;
    border-radius: var(--r-17);
    flex-shrink: 0;
    position: relative;
    box-sizing: border-box;
    display: block;
    background: var(--c-ink-08);
    border: 1px solid var(--c-ink-16);
    transition: background 140ms ease;
  }
  .switch span {
    position: absolute;
    top: 3px;
    left: 3px;
    width: 26px;
    height: 26px;
    border-radius: 50%;
    display: block;
    background: var(--ink-quiet);
    transition: left 140ms ease;
  }
  .switch.is-on {
    background: var(--c-lms-32);
    border-color: var(--c-lms-50);
  }
  .switch.is-on span {
    left: 29px;
    background: var(--accent-lms);
  }
  .switch.is-on.is-amber {
    background: var(--rc-without-switch);
    border-color: var(--c-warn-55);
  }
  .switch.is-on.is-amber span {
    background: var(--rc-without);
  }

  .powerbtn {
    display: flex;
    align-items: center;
    gap: 16px;
    height: 58px;
    padding: 0 14px 0 20px;
    border-radius: var(--r-15);
    background: var(--c-white-05);
    border: 1px solid var(--ink-line);
    box-sizing: border-box;
    color: inherit;
    flex-shrink: 0;
    font: inherit;
  }
  .powerbtn:active,
  .ab:active,
  .againbtn:active {
    transform: scale(0.95);
  }
  .powerbtn--bar {
    gap: 12px;
    height: 60px;
    padding: 0 12px 0 16px;
  }
  .powerbtn__state {
    font-family: var(--font-mono);
    font-size: 13px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    white-space: nowrap;
    color: var(--ink-muted);
  }
  .powerbtn--bar .powerbtn__state {
    flex: 1;
    min-width: 0;
    text-align: left;
    font-size: 15px;
  }
  .powerbtn__state.is-on {
    color: var(--accent-lms);
  }
  .is-dim {
    opacity: 0.5;
  }
  .powerbtn.is-dim {
    pointer-events: none;
  }

  /* -- cards -- */
  .card {
    flex-shrink: 0;
    border-radius: var(--r-15);
    background: var(--c-white-05);
    border: 1px solid var(--ink-line);
    box-sizing: border-box;
    color: inherit;
    font: inherit;
    text-align: left;
    transition: opacity 160ms ease;
  }
  .power,
  .measuredcard {
    display: flex;
    align-items: center;
    gap: 18px;
    padding: 14px 20px;
    width: 100%;
    box-sizing: border-box;
  }
  .measuredcard {
    gap: 14px;
  }
  /* The phone's switch card holds the Reaches chips under on/off (1a). */
  .powercard {
    display: flex;
    flex-direction: column;
    gap: 14px;
    padding: 14px 18px 16px;
  }
  .powercard .power {
    padding: 0;
    border: 0;
    background: none;
    color: inherit;
    font: inherit;
    text-align: left;
  }
  .powercard__rule {
    height: 1px;
    background: var(--c-ink-08);
  }
  .label--phone {
    letter-spacing: 0.16em;
  }
  .reach {
    display: flex;
    gap: 8px;
    transition: opacity 160ms ease;
  }
  .reach.is-off {
    opacity: 0.45;
    pointer-events: none;
  }
  .chip {
    position: relative;
    flex: 1;
    min-width: 0;
    min-height: 64px;
    padding: 10px 14px;
    border-radius: var(--r-md);
    box-sizing: border-box;
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 4px;
    font: inherit;
    text-align: left;
    color: var(--ink);
    background: var(--c-ink-05);
    border: 1px solid var(--c-ink-12);
  }
  .chip:active {
    transform: scale(0.97);
  }
  .chip__name {
    font-size: 16px;
    font-weight: 700;
    white-space: nowrap;
  }
  .chip__sub {
    font-family: var(--font-mono);
    font-size: 12px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    color: var(--ink-muted);
  }
  .chip.is-sel {
    background: var(--c-lms-16);
    border-color: var(--c-lms-55);
  }
  .chip.is-sel .chip__name {
    color: var(--accent-lms);
  }
  .chip.is-sel .chip__sub {
    color: var(--c-ink-78);
  }
  .chip.is-locked {
    background: transparent;
    border: 1.5px dashed var(--rc-reach-locked-line);
  }
  .chip.is-locked .chip__name {
    color: var(--ink-quiet);
  }
  .chip.is-locked .chip__sub {
    color: var(--rc-without);
  }
  .reach--panel .chip__name {
    font-size: 17px;
  }
  .reach--bar .chip {
    height: 64px;
    padding: 0 14px;
    border-radius: var(--r-14);
    gap: 3px;
  }
  .reach--bar .chip__name {
    font-size: 18px;
  }
  .reach--bar .chip__sub {
    font-size: 13px;
  }
  /* On the chip's top edge, so it fits the chip at every width. */
  .testing {
    position: absolute;
    top: -8px;
    right: 10px;
    padding: 1px 6px;
    border-radius: var(--r-6);
    border: 1px solid var(--c-ink-14);
    background: var(--bg-panel);
    font-family: var(--font-mono);
    font-size: 10px;
    line-height: 13px;
    letter-spacing: var(--track-label);
    text-transform: uppercase;
    white-space: nowrap;
    color: var(--ink-quiet);
  }
  .reach__note {
    font-size: 14px;
    line-height: 1.45;
    color: var(--c-ink-78);
    text-wrap: pretty;
  }
  .power__text {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
  }
  .power__title {
    font-size: 18px;
    font-weight: 600;
  }
  .power__note {
    font-size: 14px;
    line-height: 1.36;
    color: var(--ink-quiet);
    margin-top: 5px;
    text-wrap: pretty;
  }
  .ab {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 14px;
    border-radius: var(--r-15);
    padding: 14px 20px;
    box-sizing: border-box;
    background: var(--c-white-05);
    border: 1px solid var(--ink-line);
    color: inherit;
    font: inherit;
    text-align: left;
    width: 100%;
    transition: opacity 160ms ease;
  }
  .ab.is-without {
    background: var(--rc-without-fill);
    border-color: var(--rc-without-line);
  }
  .ab.is-off {
    opacity: 0.4;
    pointer-events: none;
  }
  .ab--panel {
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
    border-radius: var(--r-20);
    padding: 16px 18px;
  }
  .ab--bar {
    min-height: 84px;
    border-radius: var(--r-18);
    padding: 12px 16px 12px 18px;
  }
  .ab__row {
    display: flex;
    align-items: center;
    gap: 14px;
  }
  .ab__text {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
  }
  .ab__title {
    font-size: 18px;
    font-weight: 600;
  }
  .ab--panel .ab__title {
    flex: 1;
    min-width: 0;
    font-size: 20px;
    font-weight: 700;
  }
  .ab--bar .ab__title {
    font-size: 20px;
    font-weight: 700;
  }
  .ab__sub {
    font-size: 14px;
    line-height: 1.36;
    margin-top: 5px;
    text-wrap: pretty;
    color: var(--ink-quiet);
  }
  .ab--panel .ab__sub {
    font-size: 15px;
    line-height: 1.4;
    margin-top: 0;
  }
  .ab--bar .ab__sub {
    font-size: 16px;
    margin-top: 3px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .ab.is-without .ab__sub {
    color: var(--rc-without);
  }
  .tag {
    flex-shrink: 0;
    height: 26px;
    padding: 0 7px;
    border-radius: var(--r-7);
    box-sizing: border-box;
    display: flex;
    align-items: center;
    font-family: var(--font-mono);
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.08em;
    border: 1.5px solid var(--c-ink-40);
    color: var(--ink-body);
  }
  .ab--panel .tag,
  .ab--bar .tag {
    height: 30px;
    padding: 0 9px;
    border-radius: var(--r-sm);
    font-size: 13px;
  }
  .ab--bar .tag {
    font-size: 14px;
  }
  .ab.is-without .tag {
    border-color: var(--rc-without);
    color: var(--rc-without);
  }
  .flag {
    flex-shrink: 0;
    height: 28px;
    padding: 0 10px;
    border-radius: var(--r-sm);
    box-sizing: border-box;
    display: flex;
    align-items: center;
    font-family: var(--font-mono);
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    background: var(--rc-flag-fill);
    border: 1px solid var(--c-warn-40);
    color: var(--rc-without);
  }
  .flag--panel {
    height: 30px;
  }
  .flag--bar {
    height: 30px;
    font-size: 13px;
    letter-spacing: 0.12em;
  }
  .dsd {
    flex-shrink: 0;
    display: flex;
    gap: 12px;
    align-items: flex-start;
    padding: 12px 14px;
    border-radius: var(--r-md);
    background: var(--c-ink-06);
    border: 1px solid var(--c-ink-14);
    font-size: 14px;
    line-height: 1.4;
    text-wrap: pretty;
  }
  .dsd--panel {
    padding: 14px 16px;
    border-radius: var(--r-14);
    font-size: 15px;
  }
  .dsd__tag {
    flex-shrink: 0;
    height: 24px;
    padding: 0 7px;
    border-radius: var(--r-6);
    border: 1px solid var(--c-ink-30);
    display: flex;
    align-items: center;
    font-family: var(--font-mono);
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.1em;
  }
  .dsd--panel .dsd__tag {
    height: 26px;
    padding: 0 8px;
    border-radius: var(--r-7);
    font-size: 12px;
  }

  /* -- the phone -- */
  .scroll {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    scrollbar-width: none;
    box-sizing: border-box;
    padding: 16px 16px 28px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .scroll::-webkit-scrollbar {
    display: none;
  }
  .segs {
    flex-shrink: 0;
    align-self: flex-start;
    display: flex;
    gap: 4px;
    padding: 3px;
    border-radius: var(--r-14);
    background: var(--ink-fill);
  }
  .segs--panel,
  .segs--bar {
    align-self: auto;
    padding: 4px;
    border-radius: var(--r-lg);
  }
  .segbtn {
    height: 42px;
    padding: 0 20px;
    border-radius: var(--r-11);
    box-sizing: border-box;
    display: flex;
    align-items: center;
    font: inherit;
    font-size: 15px;
    font-weight: 700;
    background: transparent;
    border: 1px solid transparent;
    color: var(--c-ink-78);
  }
  .segs--panel .segbtn {
    height: 50px;
    padding: 0 24px;
    border-radius: var(--r-md);
    font-size: 17px;
  }
  .segs--bar .segbtn {
    height: 52px;
    padding: 0 22px;
    border-radius: var(--r-md);
    font-size: 18px;
  }
  .segbtn.is-sel {
    background: var(--c-lms-16);
    border-color: var(--c-lms-55);
    color: var(--accent-lms);
  }
  .chartcard {
    display: flex;
    flex-direction: column;
    gap: 10px;
    border-radius: var(--r-18);
    padding: 14px 12px 12px;
  }
  .chartcard__head {
    padding: 0 4px;
  }
  .chartcard__title {
    font-size: 18px;
    font-weight: 700;
  }
  .chartcard__line {
    font-size: 14px;
    line-height: 1.4;
    color: var(--c-ink-78);
    margin-top: 3px;
    text-wrap: pretty;
  }
  .again {
    flex-shrink: 0;
    height: 52px;
    border-radius: var(--r-15);
    box-sizing: border-box;
    display: flex;
    align-items: center;
    justify-content: center;
    font: inherit;
    font-size: 16px;
    font-weight: 700;
    white-space: nowrap;
    color: inherit;
    background: var(--ink-fill);
    border: 1px solid var(--c-ink-14);
  }
  .again.is-lit {
    background: var(--c-lms-16);
    border-color: var(--c-lms-55);
    color: var(--accent-lms);
  }
  .again:active {
    transform: scale(0.97);
  }
  .error {
    font-size: 15px;
    color: var(--rc-without);
    padding: 0 4px;
  }

  /* -- the panel -- */
  .body {
    flex: 1;
    min-height: 0;
    display: flex;
    gap: 24px;
    padding: 22px 36px 26px;
    box-sizing: border-box;
  }
  .left {
    width: 340px;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    gap: 12px;
    min-height: 0;
  }
  .rcard {
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    gap: 10px;
    border-radius: var(--r-20);
    padding: 16px 18px;
    box-sizing: border-box;
    background: var(--c-white-05);
    border: 1px solid var(--ink-line);
  }
  .lcard {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 10px;
    border-radius: var(--r-20);
    padding: 16px 18px;
    box-sizing: border-box;
    background: var(--c-white-05);
    border: 1px solid var(--ink-line);
    min-height: 0;
    overflow: hidden;
  }
  .label {
    display: flex;
    align-items: center;
    gap: 12px;
    font-family: var(--font-mono);
    font-size: 12px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    white-space: nowrap;
    color: var(--ink-quiet);
  }
  .rule {
    flex: 1;
    height: 1px;
    background: var(--ink-line);
    display: block;
  }
  .lcard__when {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .lcard__text {
    flex: 1;
    min-width: 0;
  }
  .lcard__date {
    display: block;
    font-size: 19px;
    font-weight: 700;
    white-space: nowrap;
  }
  .lcard__pos {
    display: block;
    font-size: 14px;
    color: var(--ink-quiet);
    margin-top: 2px;
  }
  /* The corrections in two groups (1g). */
  .who {
    font-size: 15px;
    font-weight: 700;
    margin-top: 2px;
  }
  .group {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-top: 6px;
  }
  .group--first {
    margin-top: 2px;
  }
  .group__name {
    font-family: var(--font-mono);
    font-size: 11px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    white-space: nowrap;
    color: var(--ink-quiet);
  }
  .group__kind {
    font-size: 12px;
    white-space: nowrap;
    color: var(--ink-quiet);
  }
  .rows {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 6px 16px;
  }
  .empty {
    font-size: 14px;
    line-height: 1.4;
    color: var(--c-ink-78);
    text-wrap: pretty;
  }
  .lcard__never {
    font-size: 20px;
    font-weight: 700;
  }
  .cut {
    display: flex;
    align-items: baseline;
    white-space: nowrap;
    justify-content: space-between;
    gap: 6px;
    font-family: var(--font-mono);
    font-size: 14px;
    font-variant-numeric: tabular-nums;
  }
  .cut__f {
    color: var(--c-ink-78);
  }
  .cut__g {
    font-weight: 600;
    color: var(--rc-before);
  }
  .cut__g.is-up {
    color: var(--rc-after);
  }
  /* The panel's header: DSD as a pill beside the power control (§5). */
  .dsdpill {
    flex-shrink: 0;
    display: flex;
    gap: 10px;
    align-items: center;
    height: 58px;
    padding: 0 16px;
    border-radius: var(--r-15);
    box-sizing: border-box;
    background: var(--c-ink-06);
    border: 1px solid var(--c-ink-14);
    font-size: 15px;
    white-space: nowrap;
  }
  .dsdpill .dsd__tag {
    height: 26px;
    padding: 0 8px;
    border-radius: var(--r-7);
    box-sizing: border-box;
    font-size: 12px;
  }
  .againbtn {
    height: 58px;
    border-radius: var(--r-15);
    box-sizing: border-box;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
    font: inherit;
    font-size: 17px;
    font-weight: 700;
    flex-shrink: 0;
    background: var(--ink-fill);
    border: 1px solid var(--c-ink-14);
    color: var(--ink);
  }
  .againbtn.is-lit {
    background: var(--c-lms-16);
    border-color: var(--c-lms-55);
    color: var(--accent-lms);
  }
  .againbtn--bar {
    height: 60px;
    font-size: 18px;
  }
  .chartpanel {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 10px;
    border-radius: var(--r-xl);
    padding: 20px 22px 16px;
  }
  .chartpanel__head {
    display: flex;
    align-items: center;
    gap: 8px 14px;
    flex-shrink: 0;
  }
  .chartpanel__text {
    flex: 1;
    min-width: 0;
  }
  .chartpanel__title {
    font-size: 26px;
    font-weight: 700;
    letter-spacing: -0.01em;
  }
  .chartpanel__line {
    font-size: 16px;
    color: var(--ink-muted);
    margin-top: 4px;
  }
  .never {
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 14px;
    padding: 12px 20px 12px 24px;
  }
  .never__title {
    font-size: 32px;
    font-weight: 800;
    letter-spacing: -0.015em;
    line-height: 1.15;
    text-wrap: balance;
  }
  .never__text {
    font-size: 18px;
    line-height: 1.5;
    color: var(--c-ink-78);
    text-wrap: pretty;
  }
  .never--bar {
    gap: 12px;
    padding: 0 12px;
  }
  .never--bar .never__title {
    font-size: 28px;
  }
  .never--bar .never__text {
    line-height: 1.45;
    max-width: 760px;
  }

  /* -- the bars -- */
  .side {
    width: 220px;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 28px 24px 24px;
    box-sizing: border-box;
    border-right: 1px solid var(--c-ink-09);
  }
  .side__buttons {
    display: flex;
    gap: 10px;
  }
  .side__rest {
    flex: 1;
  }
  .mid {
    width: 400px;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 22px 20px 22px 22px;
    box-sizing: border-box;
    border-right: 1px solid var(--c-ink-09);
  }
  .mid--narrow {
    width: 360px;
  }
  .mcard {
    display: flex;
    align-items: center;
    gap: 12px;
    min-height: 68px;
    border-radius: var(--r-18);
    padding: 10px 18px;
    box-sizing: border-box;
    background: var(--c-white-05);
    border: 1px solid var(--ink-line);
  }
  .mcard__text {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
  }
  .mcard__title {
    font-size: 19px;
    font-weight: 700;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .mcard__sub {
    font-size: 16px;
    color: var(--ink-quiet);
    margin-top: 2px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .right {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 20px 32px 18px 24px;
    box-sizing: border-box;
  }
  .right__head {
    display: flex;
    align-items: center;
    gap: 20px;
    flex-shrink: 0;
  }
  .right__text {
    flex: 1;
    min-width: 0;
    display: flex;
    align-items: baseline;
    gap: 16px;
  }
  .right__title {
    font-size: 26px;
    font-weight: 700;
    letter-spacing: -0.01em;
    white-space: nowrap;
  }
  .right--narrow .right__text {
    flex-direction: column;
    align-items: flex-start;
    gap: 2px;
  }
  .right--narrow .right__title {
    font-size: 22px;
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  /* Three tabs (Both) beside the heading on the 1280-wide bar. */
  .right--narrow .segs--bar .segbtn {
    height: 46px;
    padding: 0 12px;
    font-size: 16px;
  }
  .right--narrow .right__line {
    font-size: 15px;
    max-width: 100%;
  }
  .right__line {
    font-size: 17px;
    color: var(--ink-muted);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .chartbar {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    transition: opacity 160ms ease;
  }

  /* -- the sheet -- */
  .scrim {
    position: absolute;
    inset: 0;
    background: var(--bg-scrim);
    z-index: 5;
  }
  .sheet {
    position: absolute;
    left: 50%;
    top: 50%;
    transform: translate(-50%, -50%);
    width: 720px;
    background: var(--bg-panel);
    border-radius: var(--r-xl);
    padding: 30px 32px 28px;
    box-sizing: border-box;
    display: flex;
    gap: 30px;
    box-shadow: 0 34px 90px var(--c-black-60);
    z-index: 6;
  }
  .sheet--bar {
    width: 820px;
    height: 320px;
    padding: 26px 30px;
    gap: 28px;
    align-items: center;
  }
  .qr {
    width: 200px;
    height: 200px;
    flex-shrink: 0;
    border-radius: var(--r-14);
    display: block;
  }
  .qr--empty {
    background: var(--ink-fill);
  }
  .sheet__text {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .sheet--bar .sheet__text {
    gap: 10px;
  }
  .sheet__title {
    font-size: 24px;
    font-weight: 700;
    letter-spacing: -0.01em;
  }
  .sheet__note {
    font-size: 16px;
    line-height: 1.5;
    color: var(--c-ink-78);
    text-wrap: pretty;
  }
  .sheet--bar .sheet__note {
    font-size: 17px;
    line-height: 1.45;
  }
  .sheet__addr {
    font-family: var(--font-mono);
    font-size: 16px;
    color: var(--accent-lms);
  }
  .sheet--bar .sheet__addr {
    flex: 1;
    font-size: 17px;
  }
  .sheet__row {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-top: 6px;
  }
  .sheet__actions {
    display: flex;
    justify-content: flex-end;
  }
  .sheet__close {
    height: 58px;
    padding: 0 28px;
    border-radius: var(--r-15);
    box-sizing: border-box;
    display: flex;
    align-items: center;
    font: inherit;
    font-size: 17px;
    font-weight: 600;
    background: var(--ink-fill);
    border: 1px solid var(--c-ink-14);
    color: inherit;
  }
  .sheet--bar .sheet__close {
    height: 60px;
    font-size: 18px;
  }
  .sheet__close:active {
    transform: scale(0.95);
  }
  .toast {
    position: absolute;
    left: 50%;
    bottom: 28px;
    transform: translateX(-50%);
    padding: 14px 22px;
    border-radius: var(--r-md);
    background: var(--bg-panel);
    border: 1px solid var(--c-warn-40);
    color: var(--rc-without);
    font-size: 17px;
    z-index: 7;
  }
</style>
