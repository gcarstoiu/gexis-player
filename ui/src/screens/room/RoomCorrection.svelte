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
  import { capitalised, chartSpan, correctionGroups, correctionsWho, countWord, cutFreq, cutGain, cutRows,
    entryTags, entryWhat, outputPhrase, outputShort, rangeWord, restoreRoom, resultWords, room, roomEntry, RoomReader,
    setRoom, sideName, sides, speakersLine, speakersRows, speakersShort, takenLine, worseLine } from '../../lib/room.svelte.js';
  import { screen } from '../../lib/family.svelte.js';
  import RoomChart from './RoomChart.svelte';
  import RoomFlow from './RoomFlow.svelte';
  import RoomLeft from './RoomLeft.svelte';

  let { surface = 'panel', onback, onhome = null, flat = false } = $props();

  const phone = $derived(surface === 'phone');
  const bar = $derived(surface === 'bar');
  const reader = new RoomReader();
  //: On the phone's Before, the microphone and its file are looked for
  //: every two seconds: plugging it in moves nothing else.
  let view = $state(null);   // phone: 'page' | 'flow'
  //: What the flow's Before starts: the measurement, or the speaker check
  //: on its own (ADR-0188).
  let want = $state('measure');
  const summary = $derived($room);
  const full = $derived(reader.full);
  $effect(() => {
    reader.follow(summary, phone && view === 'flow' && !summary?.run);
  });
  onDestroy(() => reader.stop());

  const measured = $derived(full?.measured ?? null);
  //: The phone opens on the page, never measured too (ADR-0189 C1), and on
  //: the flow while a run goes on or its end is still to be shown.
  $effect(() => {
    if (!phone || !full) return;
    if (full.run || (full.ended && ['cancelled', 'failed'].includes(full.ended.how))) view = 'flow';
    else if (view === null) view = 'page';
  });

  let error = $state(null);
  let ch = $state('L');
  let sheet = $state(false);
  //: The switches move from the press; the core's word wins in the end.
  let wantOn = $state(null);
  let wantAb = $state(null);
  let wantReach = $state(null);
  let wantSpk = $state(null);
  const on = $derived(wantOn ?? !!full?.on);
  //: ADR-0188: the speakers' alignment, its own switch (null: never checked).
  const spk = $derived(full?.speakers ?? null);
  const spkOn = $derived(wantSpk ?? !!spk?.on);
  const ab = $derived((wantAb ?? !!full?.without) && (on || spkOn));
  const reach = $derived(wantReach ?? full?.reach ?? 'full');
  $effect(() => {
    if (wantOn !== null && !!full?.on === wantOn) wantOn = null;
    if (wantAb !== null && !!full?.without === wantAb) wantAb = null;
    if (wantReach !== null && full?.reach === wantReach) wantReach = null;
    if (wantSpk !== null && !!full?.speakers?.on === wantSpk) wantSpk = null;
  });
  const dsd = $derived(!!full?.dsd);
  //: Hear it without takes out room correction and the alignment both.
  const abLive = $derived(((on && !!measured) || spkOn) && !dsd);
  //: ADR-0188 D2: checked since the room was measured, and moved enough
  //: that the bass's cuts can miss.
  const stale = $derived(!!full?.stale);
  //: How far the measurement was made: one from before Phase 30 covers the
  //: bass only, and holds the reach at Bass until the room is measured again.
  const range = $derived(measured?.range ?? 'full');
  const bassOnly = $derived(!!measured && range !== 'full');
  const reachLive = $derived(on && !!measured && !dsd);

  async function change(key, value) {
    error = null;
    if (key === 'on') wantOn = value;
    else if (key === 'reach') wantReach = value;
    else if (key === 'speakers') wantSpk = value;
    else wantAb = value;
    try {
      reader.full = await setRoom({ [key]: value });
    } catch (e) {
      error = e.message;
    } finally {
      wantOn = null;
      wantAb = null;
      wantReach = null;
      wantSpk = null;
    }
  }
  const toggleOn = () => measured && change('on', !on);
  const toggleSpk = () => spk && change('speakers', !spkOn);
  //: The flow, for a measurement or for the speaker check alone.
  function openFlow(what) {
    want = what;
    view = 'flow';
  }
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
  const speaker = $derived(chart?.speakers?.[ch] ?? null);
  const kind = $derived(chart?.after_kind ?? 'measured');
  const notChecked = $derived(!!measured && !measured.checked);
  //: The corrections in two groups (the design's 1g), for the speaker shown.
  const groups = $derived(correctionGroups(speaker, { range, reach }));
  const cutsWho = $derived(correctionsWho(ch, groups[0]?.rows.length ?? 0, groups[1]?.rows.length ?? 0));
  //: The speaker shown: its own numbers, not the larger of the two.
  const words = $derived(resultWords({ speaker, range, reach, expectedMark: notChecked }));
  const resultHead = $derived(words[0]);
  const resultLine = $derived(words[1]);
  const span = $derived(chartSpan(chart));
  const positionsWord = $derived(countWord(measured?.positions ?? 0));
  //: ADR-0188: Hear it without takes out the alignment too (the room
  //: page George chose, 2026-11-23).
  const abSub = $derived(!on && !spkOn ? 'Only while room correction or the speakers are on.'
    : ab ? 'Now without: no room correction and no alignment. Switch back to hear them.'
      : 'Compare: no room correction and no alignment, heard at once.');
  const abShort = $derived(!on && !spkOn ? 'Only while room correction or the speakers are on.'
    : ab ? 'Now without: no correction, no alignment' : wideBar ? 'No correction, no alignment' : 'Takes out both');
  //: ADR-0188 C6 (the panel and the bar George chose, 2026-11-24): the two
  //: switches side by side, each named, with what it does under the name.
  const corrSub = $derived(!measured ? 'Measure first' : on ? (reach === 'bass' || bassOnly ? 'Bass' : 'Full range')
    : spkOn && spk?.plays ? 'Taken out' : 'Bit-perfect');
  const spkSub = $derived(!spk ? 'Check from your phone' : spkOn ? speakersShort(spk) : 'As they are');
  //: The panel's and the bar's button: the phone measures and checks.
  const phoneLabel = $derived(stale ? 'Measure again, from your phone' : bassOnly ? againLabel
    : 'Measure or check, from your phone');
  const againLabel = $derived(bassOnly ? 'Measure again for the full range' : 'Measure again');
  const powerNote = $derived(on ? `For ${outputPhrase(full?.output)}. Each output keeps its own.`
    : spkOn && spk?.plays ? 'Off: the correction is taken out. The speakers stay aligned.'
      : 'Off: the correction is taken out. With the equaliser also off, the sound is untouched, bit-perfect.');

  // ---- ADR-0189 (George's B and H2, 2026-11-25): the three steps, Earlier ----
  //: *18 Nov* from *18 November*.
  const short = (d) => (d ? d.replace(/^(\d+) (\w{3})\w*/, '$1 $2') : '');
  //: Each step: done, now (the next one, lit), amb (to do again) or todo.
  const step1 = $derived(spk ? 'done' : 'now');
  const step2 = $derived(!measured ? (spk ? 'now' : 'todo') : stale ? 'amb' : 'done');
  const step3 = $derived(measured && !notChecked ? 'done' : 'todo');
  const spkNote = $derived(!spk ? 'Not checked yet' : measured ? speakersShort(spk)
    : spkOn ? 'Both reach your seat together and equally loud.' : 'Off: both play as they are.');
  //: *Playing now*: what is heard, in pills.
  const playingPills = $derived.by(() => {
    const pills = [];
    const corr = on && !!measured;
    const aligned = spkOn && !!spk?.plays;
    const roomEntries = (full?.history ?? []).filter((e) => e.kind === 'room').length;
    if (corr) {
      pills.push(stale ? { text: 'Room correction · no longer fits in the bass', tone: 'amb' }
        : { text: `Room correction · ${roomEntries > 1 ? short(measured.day) : reach === 'bass' || bassOnly ? 'bass' : 'full range'}`, tone: 'lms' });
    }
    if (aligned) pills.push({ text: corr ? 'Speakers aligned' : `Speakers aligned · ${speakersShort(spk)}`, tone: 'lms' });
    if (!corr && aligned) pills.push({ text: 'No room correction', tone: '' });
    if (!corr && !aligned) pills.push({ text: full?.eq_on ? 'No room correction' : 'Untouched · bit-perfect', tone: '' });
    return pills;
  });
  const worseNote = $derived(measured && !notChecked && measured.worse?.length ? worseLine(measured.worse) : '');
  const takenNote = $derived(measured ? takenLine(measured.taken) : '');
  const history = $derived(full?.history ?? []);
  const earlier = $derived(history.filter((e) => !e.playing && !e.aligned));
  let opened = $state(null);
  let openedFull = $state(null);
  let openedCh = $state('L');
  let asking = $state(null);
  let choice = $state('its');
  let going = $state(false);
  //: The cuts' grid as drawn: *−11.0*, *+2.5*, the unit in its heading.
  const gainNum = (g) => `${g > 0 ? '+' : '−'}${Math.abs(g).toFixed(1)}`;
  const entryAlign = (e) => speakersShort({ delay_ms: e.delay_ms, level_db: e.level_db });
  async function openEntry(e) {
    opened = e.id;
    openedFull = null;
    try {
      openedFull = await roomEntry(e.id);
    } catch (err) {
      error = err.message;
      opened = null;
    }
  }
  const closeEntry = () => { opened = null; openedFull = null; };
  function askBack(e) {
    asking = e;
    choice = 'its';
  }
  async function goBack() {
    if (!asking) return;
    going = true;
    error = null;
    try {
      // Close to today's, its alignment comes back with it (C3).
      reader.full = await restoreRoom(asking.id, asking.differs ? choice : 'its');
      asking = null;
      closeEntry();
    } catch (err) {
      error = err.message;
      asking = null;
    } finally {
      going = false;
    }
  }
  //: *On 12 November the right speaker stood 33 cm further away than the left.*
  function movedWords(e) {
    const d = e.distance_cm;
    if (d == null || Math.round(Math.abs(d)) < 1) return '';
    return ` On ${e.day} the ${d > 0 ? 'right' : 'left'} speaker stood ${Math.round(Math.abs(d))} cm further away than the ${d > 0 ? 'left' : 'right'}.`;
  }
  const unchangedWords = $derived(`${reach === 'full' && !bassOnly ? 'full range' : 'the bass'}, ${on && spkOn ? 'both switches on'
    : !on && !spkOn ? 'both switches off' : `room correction ${on ? 'on' : 'off'}, the speakers ${spkOn ? 'on' : 'off'}`}`);

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
    {#each sides() as k (k)}
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

{#snippet corrections(size, shown = 2)}
  <span class="who who--{size}">{cutsWho}</span>
  {#each groups.slice(0, shown) as g, i (g.name)}
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

{#snippet num(state, n)}
  <span class="num num--{state}">{#if state === 'done'}<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M3.5 8.5l3 3 6-6.5" /></svg>{:else if state === 'amb'}!{:else}{n}{/if}</span>
{/snippet}

{#snippet phoneGlyph()}
  <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="7" y="2.5" width="10" height="19" rx="2.5"></rect><path d="M11 18.5h2"></path></svg>
{/snippet}

{#if phone && view === 'flow' && full}
  <RoomFlow {full} {flat} {want} onback={() => onback?.()} onpage={() => { view = 'page'; want = 'measure'; }} />
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
      <!-- ADR-0189 (George's B and H2, 2026-11-25): Playing now, then the
           three steps on one rail, then Earlier. -->
      <div class="frame">
        <div class="top top--phone">
          <button class="back" type="button" aria-label="Back" data-dpad-back onclick={() => onback?.()}><span></span></button>
          <div class="top__text">
            <div class="title title--phone">Room correction</div>
            <div class="crumb">Settings · Audio · {outputShort(full.output)}</div>
          </div>
        </div>
        <div class="scroll scroll--steps">
          {@render dsdBanner('phone')}
          <div class="playing">
            <span class="label label--phone">Playing now</span>
            <div class="pills">
              {#each playingPills as pl (pl.text)}<span class="pill pill--{pl.tone}">{pl.text}</span>{/each}
            </div>
            <button type="button" class="abrow" class:is-off={!abLive} aria-pressed={ab} onclick={toggleAb} disabled={!abLive}>
              <span class="tag">A/B</span>
              <span class="abrow__text"><span class="abrow__title">Hear it without</span><span class="abrow__sub">{abSub}</span></span>
              {@render sw(ab, true)}
            </button>
          </div>
          {#if !measured && !spk}
            <div class="lead">Three steps, each with the UMIK-1 at your seat. Measuring the room does all three in about 20 minutes.</div>
          {/if}

          <div class="steps">
            <!-- 1 · Speakers -->
            <div class="step">
              <div class="rail">{@render num(step1, 1)}<span class="line" class:is-done={step1 === 'done'}></span></div>
              <div class="stepbody">
                <div class="stephead"><span class="steph">Speakers</span>
                  <span class="pill pill--lms">{spk ? `Checked ${stale ? 'again ' : ''}${short(spk.day)}` : 'Start here'}</span></div>
                <div class="card stepcard" class:is-lit={step1 === 'now'}>
                  {#if !spk}
                    <div class="note">How far each speaker is, whether they are wired the same way and how loud each is. The nearer is delayed and the louder turned down.</div>
                  {/if}
                  <button type="button" class="srow2" aria-pressed={spkOn} onclick={toggleSpk} disabled={!spk}>
                    <span class="grow"><span class="h">Align the speakers</span>
                      <span class="note" class:mono={!!measured && !!spk}>{spkNote}</span></span>
                    {@render sw(spkOn, false)}
                  </button>
                  {#if spk}
                    <div class="hr"></div>
                    {#each speakersRows(spk) as r (r.text)}
                      <div class="item">
                        <span class="mk mk--{r.kind}" aria-hidden="true">{#if r.kind === 'ok'}<svg viewBox="0 0 16 16"><path d="M3.5 8.5l3 3 6-6.5" /></svg>{:else}!{/if}</span>
                        <span class="item__t">{r.text}</span>
                      </div>
                    {/each}
                    <button type="button" class="btn2" onclick={() => openFlow('speakers')}>Check the speakers</button>
                  {:else}
                    <button type="button" class="btn" onclick={() => openFlow('speakers')}>Check the speakers</button>
                    <div class="btnsub">About two minutes: at your head, then 40 cm to its left.</div>
                  {/if}
                </div>
              </div>
            </div>

            <!-- 2 · Room -->
            <div class="step">
              <div class="rail">{@render num(step2, 2)}<span class="line" class:is-done={step2 === 'done'}></span></div>
              <div class="stepbody">
                <div class="stephead"><span class="steph" class:is-amber={stale}>Room</span>
                  <span class="pill pill--{!measured ? (spk ? 'lms' : '') : stale ? 'amb' : 'lms'}">{!measured ? (spk ? 'Next' : 'Not measured') : stale ? 'Measure again' : `Measured ${short(measured.day)}`}</span></div>
                <div class="card stepcard" class:is-lit={step2 === 'now'} class:is-amber={stale}>
                  {#if stale}
                    <div class="stale"><span>Measured {measured.day}, before the speakers moved: in the bass the correction no longer fits exactly.</span></div>
                    <button type="button" class="btn btn--amber" onclick={() => openFlow('measure')}>Measure again</button>
                    <div class="btnsub">About 20 minutes, the speakers and the check included.</div>
                    <div class="hr"></div>
                  {:else if !measured}
                    <div class="note">Five positions around your head. It cuts the peaks your room adds to the bass, and above the bass evens out its broad bumps and dips by 3 dB at most.</div>
                  {/if}
                  <button type="button" class="srow2" aria-pressed={on} onclick={toggleOn} disabled={!measured}>
                    <span class="grow"><span class="h">Room correction</span>
                      <span class="note">{measured ? `${capitalised(positionsWord)} positions · ${rangeWord(range)}` : 'Measure first'}</span></span>
                    {@render sw(on && !!measured, false)}
                  </button>
                  {#if measured}<span class="label label--phone">Reaches</span>{/if}
                  {@render reaches('phone')}
                  {#if bassOnly}
                    <div class="reach__note">This measurement covers the bass only. Measure again to reach the full range.</div>
                  {/if}
                  {#if measured}
                    <div class="hr"></div>
                    {#each groups as g, i (g.name)}
                      <div class="grp" class:grp--first={i === 0}><span class="grp__n">{i === 1 ? `Above, ${sideName(ch).toLowerCase()}` : g.name}</span><span class="grp__r"></span><span class="grp__k">{i === 0 ? 'narrow cuts' : 'broad'}</span></div>
                      {#if g.rows.length}
                        <div class="cuts">
                          {#each g.rows as c, j (j)}
                            <div class="cut2"><span class="cut2__f">{cutFreq(c)}</span><span class="cut2__g" class:is-up={c.gain > 0}>{gainNum(c.gain)}</span></div>
                          {/each}
                        </div>
                      {:else}
                        <div class="note">{g.empty}</div>
                      {/if}
                    {/each}
                    {#if !stale}<button type="button" class="btn2" onclick={() => openFlow('measure')}>{againLabel}</button>{/if}
                  {:else}
                    <button type="button" class={spk ? 'btn' : 'btn2'} onclick={() => openFlow('measure')}>Measure the room</button>
                    <div class="btnsub">{spk ? 'About 20 minutes. The speakers are checked again first, then step 3 follows.' : 'About 20 minutes. Steps 1 and 3 are part of it.'}</div>
                  {/if}
                </div>
              </div>
            </div>

            <!-- 3 · Checked -->
            <div class="step">
              <div class="rail">{@render num(step3, 3)}{#if earlier.length}<span class="line"></span>{/if}</div>
              <div class="stepbody">
                <div class="stephead"><span class="steph">Checked</span>
                  <span class="pill pill--{!measured ? '' : stale ? '' : notChecked ? 'amb' : 'lms'}">{!measured ? 'After step 2' : stale ? `${short(measured.day)}, before the move` : notChecked ? 'Not checked' : `All ${positionsWord} positions`}</span></div>
                {#if !measured}
                  <div class="stepempty">The correction measured again at each position: the chart of before and after, how long the bass rings, and the dips a cut cannot fill.</div>
                {:else}
                  {#if worseNote}<div class="note">{worseNote}</div>{/if}
                  {#if takenNote}<div class="note">{takenNote}</div>{/if}
                  {@render segs('phone')}
                  <div class="card chartcard" class:is-dim={dsd || !on}>
                    <div class="chartcard__head">
                      <div class="chartcard__title">{resultHead}</div>
                      <div class="chartcard__line">{resultLine}</div>
                    </div>
                    <RoomChart surface="phone" freqs={chart?.freqs ?? []} {speaker} {kind} {span} {reach} {range} />
                  </div>
                  <RoomLeft show="ringing" {speaker} expected={notChecked} />
                  <RoomLeft show="dips" dips={measured.dips} />
                {/if}
              </div>
            </div>
          </div>

          {#if earlier.length}
            <!-- ADR-0189 D2 (H2): Earlier, the steps' timeline. -->
            <div class="tl">
              <div class="tli">
                <div class="tlr"><span class="tl__arrow" aria-hidden="true">▼</span><span class="tll"></span></div>
                <div class="tlb"><span class="label label--phone">Earlier</span>
                  <span class="note">Every measurement and speaker check, newest first. Tap one to see it.</span></div>
              </div>
              {#each earlier as e, i (e.id)}
                {@const last = i === earlier.length - 1}
                <div class="tli">
                  <div class="tlr"><span class="tln tln--{e.kind === 'room' ? 'room' : 'spk'}" class:tln--big={opened === e.id}></span>{#if !last}<span class="tll" class:is-lit={opened === e.id}></span>{/if}</div>
                  <div class="tlb">
                    {#if opened === e.id}
                      <div class="tlb__top"><span class="ewhen grow">{e.day}{#if e.time}<span class="ewhen__t">{e.time}</span>{/if}</span>
                        <button type="button" class="link" onclick={closeEntry}>Close</button></div>
                      <div class="card stepcard is-lit">
                        <div class="etags">
                          <span class="mini">Room measured · {rangeWord(e.range)}</span>
                          {#if e.checked}<span class="mini mini--lms">Checked · within {e.within} dB</span>{/if}
                          {#if e.worse?.length}<span class="mini mini--amb">{e.worse.length === 1 ? `Position ${e.worse[0]}` : `Positions ${e.worse.join(', ')}`} further</span>{/if}
                        </div>
                        <div class="note">Peaks down by up to {e.peaks_down} dB. Speakers as measured <span class="mono">{entryAlign(e)}</span>, {e.differs ? "not today's" : "close to today's"}.</div>
                        {#if openedFull?.id === e.id}
                          <div class="segs segs--phone segs--small" role="group" aria-label="Speaker">
                            {#each sides() as k (k)}
                              <button type="button" class="segbtn" class:is-sel={openedCh === k} aria-pressed={openedCh === k} onclick={() => (openedCh = k)}>{sideName(k)}</button>
                            {/each}
                          </div>
                          <RoomChart surface="phone" freqs={openedFull.chart?.freqs ?? []} speaker={openedFull.chart?.speakers?.[openedCh] ?? null}
                                     kind={openedFull.chart?.after_kind ?? 'measured'} span={chartSpan(openedFull.chart)} reach="full" range={e.range} />
                          <div class="note">Drawn from the sweeps its check kept.</div>
                          <RoomLeft show="ringing" speaker={openedFull.chart?.speakers?.[openedCh] ?? null} expected={!e.checked} />
                          <RoomLeft show="dips" dips={openedFull.dips} />
                        {:else}
                          <div class="note">Reading it…</div>
                        {/if}
                        <button type="button" class="btn" onclick={() => askBack(e)}>Go back to this one</button>
                      </div>
                    {:else if e.kind === 'room'}
                      <button type="button" class="entry" onclick={() => openEntry(e)}>
                        <span class="ewhen">{e.day}{#if e.time}<span class="ewhen__t">{e.time}</span>{/if}</span>
                        <span class="ewhat" class:is-amber={!e.checked}>{entryWhat(e)}</span>
                        <span class="etags">{#each entryTags(e) as tg (tg.text)}<span class="mini mini--{tg.tone}">{tg.text}</span>{/each}</span>
                      </button>
                    {:else}
                      <span class="ewhen">{e.day}{#if e.time}<span class="ewhen__t">{e.time}</span>{/if}</span>
                      <span class="ewhat">{entryWhat(e)}</span>
                      <span class="etags">{#each entryTags(e) as tg (tg.text)}<span class="mini mini--{tg.tone}">{tg.text}</span>{/each}</span>
                    {/if}
                  </div>
                </div>
              {/each}
            </div>
            <div class="tlkey">
              <span class="tlkey__k"><span class="tln tln--room"></span>Room measured</span>
              <span class="tlkey__k"><span class="tln tln--spk"></span>Speakers on their own</span>
            </div>
          {/if}
          {#if error}<div class="error" role="status">{error}</div>{/if}
        </div>
      </div>
      {#if asking}
        <!-- ADR-0189 C3 (H2c, H2d): what going back changes, asked first. -->
        <div class="scrim" aria-hidden="true" onclick={() => (asking = null)}></div>
        <div class="dialog" role="dialog" aria-modal="true" aria-label={`Go back to ${asking.day}`}>
          <div>
            <div class="h h--big">Go back to {asking.day}?</div>
            <div class="note">Room measured{asking.time ? ` at ${asking.time}` : ''} · {asking.checked ? `checked · within ${asking.within} dB` : 'not checked'}</div>
          </div>
          <div class="hr"></div>
          <div class="item"><span class="mk mk--ok" aria-hidden="true"><svg viewBox="0 0 16 16"><path d="M3.5 8.5l3 3 6-6.5" /></svg></span>
            <span class="item__t"><b>Its correction plays at once,</b> in place of {measured ? `${measured.day}'s` : 'none'}.</span></div>
          {#if asking.differs}
            <div class="item"><span class="mk mk--warn" aria-hidden="true">!</span>
              <span class="item__t"><b>Its speakers' alignment differs from today's:</b> <span class="mono">{entryAlign(asking)}</span> against <span class="mono">{speakersShort(spk)}</span>.{movedWords(asking)}</span></div>
            <span class="label label--phone">Which alignment?</span>
            <button type="button" class="choice" class:is-sel={choice === 'its'} aria-pressed={choice === 'its'} onclick={() => (choice = 'its')}>
              <span class="choice__head"><span class="radio" class:is-on={choice === 'its'}></span><b>{asking.day}'s, with its correction</b></span>
              <span class="choice__sub">As it was measured. Right if the speakers are back where they stood then.</span>
            </button>
            <button type="button" class="choice" class:is-sel={choice === 'today'} aria-pressed={choice === 'today'} onclick={() => (choice = 'today')}>
              <span class="choice__head"><span class="radio" class:is-on={choice === 'today'}></span><b>Today's</b></span>
              <span class="choice__sub">The speakers stay as checked on {spk?.day}. In the bass its correction no longer fits exactly: the amber note shows on Room until you measure again.</span>
            </button>
          {:else}
            <div class="item"><span class="mk mk--ok" aria-hidden="true"><svg viewBox="0 0 16 16"><path d="M3.5 8.5l3 3 6-6.5" /></svg></span>
              <span class="item__t"><b>The speakers' alignment it was measured with comes back:</b> <span class="mono">{entryAlign(asking)}</span>.{#if spk}{' '}Close to today's <span class="mono">{speakersShort(spk)}</span>, so the bass still fits.{/if}</span></div>
            <div class="item"><span class="mk mk--todo" aria-hidden="true"></span><span class="item__t">Unchanged: {unchangedWords}.</span></div>
            {#if measured}
              <div class="item"><span class="mk mk--todo" aria-hidden="true"></span><span class="item__t">{measured.day} moves down into Earlier, to come back to.</span></div>
            {/if}
          {/if}
          <div class="dialog__row">
            <button type="button" class="btn2" onclick={() => (asking = null)}>Cancel</button>
            <button type="button" class="btn btn--go" onclick={goBack} disabled={going}>Go back</button>
          </div>
        </div>
      {/if}
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
            <span class="powerbtn__text">
              <span class="powerbtn__name">Correction</span>
              <span class="powerbtn__state" class:is-on={on && measured}>{!measured ? 'Off' : on ? 'On' : 'Off'}</span>
            </span>
            {@render sw(on && !!measured, false)}
          </button>
          <button type="button" class="powerbtn powerbtn--bar" class:is-dim={!spk} aria-pressed={spkOn}
                  onclick={toggleSpk} disabled={!spk}>
            <span class="powerbtn__text">
              <span class="powerbtn__name">Speakers</span>
              <span class="powerbtn__state" class:is-on={spkOn}>{spkOn ? 'On' : 'Off'}</span>
            </span>
            {@render sw(spkOn, false)}
          </button>
        </div>
        <div class="mid" class:mid--narrow={!wideBar}>
          {#if measured}{@render reaches('bar')}{/if}
          {@render abCard('bar')}
          <div class="mcard">
            <span class="mcard__text">
              <span class="mcard__title">{measured ? measured.year : 'Not measured yet'}</span>
              {#if stale}
                <span class="mcard__sub mcard__sub--amber">{wideBar ? 'Speakers checked since: measure again' : 'Checked since: measure again'}</span>
              {:else}
                <span class="mcard__sub">{measured ? `${capitalised(positionsWord)} positions · ${rangeWord(range)}` : 'Measure from your phone'}</span>
              {/if}
              {#if spkOn && spk?.plays}
                <!-- P3's figures, on a line of their own: the bar's width. -->
                <span class="mcard__sub">Speakers: {speakersShort(spk).replace(' · ', ', ')}</span>
              {/if}
            </span>
            {#if notChecked}<span class="flag flag--bar">Not checked</span>{/if}
          </div>
          <div class="spacer"></div>
          <button type="button" class="againbtn againbtn--bar" class:is-lit={!measured || bassOnly || stale} onclick={() => (sheet = true)}>
            {@render phoneGlyph()}{wideBar ? phoneLabel : stale || bassOnly ? 'Measure again' : 'Measure or check'}
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
          <button type="button" class="powerbtn powerbtn--two" class:is-dim={!spk} aria-pressed={spkOn} onclick={toggleSpk} disabled={!spk}>
            <span class="powerbtn__text">
              <span class="powerbtn__state" class:is-on={spkOn}>Speakers · {!spk ? 'not checked' : spkOn ? 'on' : 'off'}</span>
              <span class="powerbtn__sub">{spkSub}</span>
            </span>
            {@render sw(spkOn, false)}
          </button>
          <button type="button" class="powerbtn powerbtn--two" class:is-dim={!measured} aria-pressed={on} onclick={toggleOn} disabled={!measured}>
            <span class="powerbtn__text">
              <span class="powerbtn__state" class:is-on={on && measured}>Correction · {!measured ? 'off' : on ? 'on' : 'off'}</span>
              <span class="powerbtn__sub">{corrSub}</span>
            </span>
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
                {#if stale}
                  <div class="stale"><span class="stale__mark">!</span>
                    <span>The speakers were checked after this was measured: in the bass it no longer fits exactly. Measure again.</span></div>
                {/if}
                <!-- With the stale note, the bass's cuts alone (P2 as drawn). -->
                {@render corrections('panel', stale ? 1 : 2)}
              {:else}
                <div class="lcard__never">Not measured yet</div>
              {/if}
            </div>
            <button type="button" class="againbtn" class:is-lit={!measured || bassOnly || stale} onclick={() => (sheet = true)}>
              {@render phoneGlyph()}{phoneLabel}
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
      <div class="sheet" class:sheet--bar={bar} role="dialog" aria-label="From your phone"
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
          <div class="sheet__title">From your phone</div>
          <div class="sheet__note">You hold the phone at the seat while you move the microphone, to measure the room or check the speakers. Scan this, or open the player's page and go to Settings · Audio · Room correction.</div>
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
  /* ADR-0188 C6: two named switches (the panel and the bar George chose). */
  .powerbtn__text {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 2px;
  }
  .powerbtn__sub,
  .powerbtn__name {
    font-family: var(--font-mono);
    font-size: 12px;
    white-space: nowrap;
    color: var(--ink-muted);
  }
  .powerbtn__name {
    font-size: 11.5px;
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }
  .mcard__sub.mcard__sub--amber {
    color: var(--rc-without);
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
  .reach__note--quiet {
    font-size: 13.5px;
    color: var(--ink-quiet);
  }
  .power.is-dim .power__title {
    opacity: 0.6;
  }
  /* ADR-0188: the Speakers card's rows and button (George's A, 2026-11-23). */
  .srow {
    display: flex;
    gap: 12px;
    align-items: flex-start;
  }
  .srow__mark {
    width: 24px;
    height: 24px;
    flex-shrink: 0;
    position: relative;
    border-radius: 50%;
    box-sizing: border-box;
  }
  .srow__mark--ok {
    background: var(--c-lms-16);
  }
  .srow__mark--warn {
    background: var(--c-warn-16);
    color: var(--rc-without);
    font-family: var(--font-mono);
    font-weight: 700;
    font-size: 14px;
    line-height: 24px;
    text-align: center;
  }
  .srow__tick {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    fill: none;
    stroke: var(--accent-lms);
    stroke-width: 2.5;
    stroke-linecap: round;
    stroke-linejoin: round;
  }
  .srow__text {
    font-size: 15px;
    line-height: 1.4;
    color: var(--c-ink-78);
    text-wrap: pretty;
  }
  .checkbtn {
    height: 50px;
    border-radius: var(--r-15);
    box-sizing: border-box;
    font: inherit;
    font-size: 16px;
    font-weight: 700;
    color: inherit;
    background: var(--ink-fill);
    border: 1px solid var(--c-ink-14);
  }
  .checkbtn:active {
    transform: scale(0.97);
  }
  .stale {
    display: flex;
    gap: 10px;
    align-items: flex-start;
    padding: 10px 12px;
    border-radius: var(--r-md);
    background: var(--rc-without-fill);
    border: 1px solid var(--c-warn-40);
    font-size: 14px;
    line-height: 1.45;
    color: var(--c-ink-78);
    text-wrap: pretty;
  }
  .stale__mark {
    color: var(--rc-without);
    font-weight: 800;
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
    font-size: 14px;
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
  /* The tabs beside the heading on the 1280-wide bar. */
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

  /* ---- ADR-0189 (George's B and H2, 2026-11-25): the phone's page as three
     steps, and Earlier - as drawn, in the UI's tokens. ---- */
  .scroll--steps {
    gap: 14px;
  }
  .playing {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 14px 16px;
    border-radius: var(--r-15);
    background: var(--bg-panel);
    border: 1px solid var(--ink-line);
  }
  .pills,
  .etags {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }
  .pill {
    font-family: var(--font-mono);
    font-size: 12px;
    letter-spacing: 0.04em;
    min-height: 26px;
    padding: 0 10px;
    border-radius: var(--r-pill);
    display: inline-flex;
    align-items: center;
    max-width: 100%;
    padding-top: 3px;
    padding-bottom: 3px;
    line-height: 1.35;
    box-sizing: border-box;
    background: var(--c-ink-08);
    color: var(--c-ink-78);
  }
  .pill--lms {
    background: var(--c-lms-16);
    color: var(--accent-lms);
  }
  .pill--amb {
    background: var(--rc-without-fill);
    color: var(--rc-without);
  }
  .abrow {
    display: flex;
    align-items: center;
    gap: 14px;
    background: none;
    border: 0;
    padding: 0;
    font: inherit;
    color: inherit;
    text-align: left;
    width: 100%;
  }
  .abrow.is-off {
    opacity: 0.45;
  }
  .abrow__text {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .abrow__title {
    font-size: 16px;
    font-weight: 650;
  }
  .abrow__sub,
  .note {
    font-size: 14px;
    line-height: 1.42;
    color: var(--ink-quiet);
  }
  .lead {
    font-size: 15px;
    line-height: 1.45;
    color: var(--ink-body);
    padding: 2px 2px 0;
  }
  .steps {
    display: flex;
    flex-direction: column;
  }
  .step,
  .tli {
    display: grid;
    grid-template-columns: 34px minmax(0, 1fr);
    column-gap: 12px;
  }
  .rail,
  .tlr {
    display: flex;
    flex-direction: column;
    align-items: center;
  }
  .num {
    width: 34px;
    height: 34px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: var(--font-mono);
    font-weight: 600;
    font-size: 15px;
    border: 1.5px solid var(--c-ink-30);
    color: var(--c-ink-70);
    flex-shrink: 0;
    box-sizing: border-box;
  }
  .num svg,
  .mk svg {
    width: 18px;
    height: 18px;
    fill: none;
    stroke: currentColor;
    stroke-width: 2.2;
    stroke-linecap: round;
    stroke-linejoin: round;
  }
  .num--done {
    background: var(--c-lms-16);
    border-color: transparent;
    color: var(--accent-lms);
  }
  .num--now {
    background: var(--accent-lms);
    border-color: var(--accent-lms);
    color: var(--ink-on-accent);
  }
  .num--amb {
    background: var(--c-warn-16);
    border-color: var(--c-warn-50);
    color: var(--rc-without);
    font-weight: 800;
  }
  .line,
  .tll {
    flex: 1;
    width: 2px;
    background: var(--c-ink-14);
    margin: 6px 0;
    min-height: 24px;
  }
  .line.is-done,
  .tll.is-lit {
    background: var(--c-lms-50);
  }
  .stepbody {
    padding-bottom: 22px;
    display: flex;
    flex-direction: column;
    gap: 10px;
    min-width: 0;
  }
  .stephead {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 8px;
    padding-top: 4px;
  }
  .steph,
  .h {
    font-size: 18px;
    font-weight: 650;
    line-height: 1.25;
  }
  .steph.is-amber {
    color: var(--rc-without);
  }
  .h--big {
    font-size: 22px;
    font-weight: 750;
  }
  .stepcard {
    padding: 16px 18px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .stepcard.is-lit {
    border-color: var(--c-lms-55);
    background: var(--c-lms-07);
  }
  .stepcard.is-amber {
    border-color: var(--c-warn-50);
    background: var(--rc-without-fill);
  }
  .srow2 {
    display: flex;
    align-items: center;
    gap: 14px;
    background: none;
    border: 0;
    padding: 0;
    font: inherit;
    color: inherit;
    text-align: left;
    width: 100%;
  }
  .srow2:disabled .switch {
    opacity: 0.4;
  }
  .grow {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .mono {
    font-family: var(--font-mono);
    font-size: 13px;
  }
  .hr {
    height: 1px;
    background: var(--ink-line);
    flex-shrink: 0;
  }
  .item {
    display: flex;
    gap: 12px;
    align-items: flex-start;
  }
  .item__t {
    font-size: 15px;
    line-height: 1.42;
    color: var(--ink-body);
    padding-top: 2px;
  }
  .item__t b {
    color: var(--ink);
    font-weight: 700;
  }
  .mk {
    width: 26px;
    height: 26px;
    border-radius: 50%;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    box-sizing: border-box;
    font-weight: 800;
  }
  .mk svg {
    width: 16px;
    height: 16px;
  }
  .mk--ok {
    background: var(--c-lms-16);
    color: var(--accent-lms);
  }
  .mk--warn {
    background: var(--c-warn-16);
    color: var(--rc-without);
  }
  .mk--todo {
    border: 1.5px dashed var(--c-ink-38);
  }
  .btn,
  .btn2 {
    width: 100%;
    font: inherit;
    border-radius: var(--r-15);
    cursor: pointer;
  }
  .btn {
    height: 54px;
    font-size: 17px;
    font-weight: 750;
    border: 0;
    background: var(--accent-lms);
    color: var(--ink-on-accent);
  }
  .btn--amber {
    background: var(--rc-without);
  }
  .btn2 {
    height: 50px;
    font-size: 16px;
    font-weight: 700;
    background: var(--ink-fill);
    border: 1px solid var(--c-ink-14);
    color: var(--ink);
  }
  .btnsub {
    font-size: 13px;
    line-height: 1.4;
    color: var(--ink-quiet);
    text-align: center;
    margin-top: -4px;
  }
  .grp {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-top: 6px;
  }
  .grp--first {
    margin-top: 0;
  }
  .grp__n {
    font-size: 14px;
    font-weight: 700;
  }
  .grp__r {
    flex: 1;
    height: 1px;
    background: var(--ink-line);
  }
  .grp__k {
    font-family: var(--font-mono);
    font-size: 12px;
    color: var(--ink-quiet);
  }
  .cuts {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 6px;
  }
  .cut2 {
    display: flex;
    flex-direction: column;
    gap: 1px;
    padding: 7px 9px;
    border-radius: var(--r-md);
    background: var(--c-ink-05);
  }
  .cut2__f {
    font-family: var(--font-mono);
    font-size: 13px;
    color: var(--c-ink-70);
  }
  .cut2__g {
    font-family: var(--font-mono);
    font-size: 15px;
    font-weight: 600;
    color: var(--rc-before);
  }
  .cut2__g.is-up {
    color: var(--accent-lms);
  }
  .stepempty {
    border: 1.5px dashed var(--c-ink-20);
    border-radius: var(--r-15);
    padding: 18px;
    text-align: center;
    color: var(--ink-quiet);
    font-size: 14px;
    line-height: 1.45;
  }
  .segs--small .segbtn {
    height: 36px;
    padding: 0 14px;
  }
  .tl {
    display: flex;
    flex-direction: column;
  }
  .tl__arrow {
    font-size: 10px;
    color: var(--ink-quiet);
    margin-top: 2px;
  }
  .tll {
    margin: 4px 0;
    min-height: 18px;
  }
  .tln {
    width: 16px;
    height: 16px;
    border-radius: 50%;
    box-sizing: border-box;
    margin-top: 4px;
    flex-shrink: 0;
    display: inline-block;
  }
  .tln--room {
    background: var(--c-ink-55);
  }
  .tln--spk {
    width: 12px;
    height: 12px;
    margin-top: 6px;
    border: 2px solid var(--rc-dip-cancel);
    background: var(--bg-base);
  }
  .tln--big {
    width: 22px;
    height: 22px;
    margin-top: 1px;
    border: 4px solid var(--c-lms-35);
    background: var(--accent-lms);
  }
  .tlb {
    padding-bottom: 16px;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .tlb__top {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .entry {
    display: flex;
    flex-direction: column;
    gap: 4px;
    background: none;
    border: 0;
    padding: 0;
    font: inherit;
    color: inherit;
    text-align: left;
    width: 100%;
    cursor: pointer;
  }
  .ewhen {
    font-size: 15.5px;
    font-weight: 700;
    line-height: 1.3;
  }
  .ewhen__t {
    font-family: var(--font-mono);
    font-size: 13px;
    font-weight: 500;
    color: var(--ink-quiet);
    margin-left: 6px;
  }
  .ewhat {
    font-size: 13.5px;
    line-height: 1.42;
    color: var(--c-ink-70);
  }
  .ewhat.is-amber {
    color: var(--rc-without);
  }
  .etags {
    margin-top: 3px;
  }
  .mini {
    font-family: var(--font-mono);
    font-size: 11.5px;
    letter-spacing: 0.03em;
    min-height: 22px;
    padding: 0 8px;
    border-radius: var(--r-7);
    display: inline-flex;
    align-items: center;
    box-sizing: border-box;
    background: var(--ink-fill);
    color: var(--c-ink-78);
    white-space: nowrap;
  }
  .mini--lms {
    background: var(--c-lms-14);
    color: var(--accent-lms);
  }
  .mini--amb {
    background: var(--rc-without-fill);
    color: var(--rc-without);
  }
  .mini--blue {
    background: var(--rc-dip-cancel-fill);
    color: var(--rc-dip-cancel);
  }
  .link {
    font: inherit;
    font-size: 14px;
    font-weight: 700;
    color: var(--c-ink-70);
    background: none;
    border: 0;
    padding: 6px 0;
    cursor: pointer;
  }
  .tlkey {
    display: flex;
    flex-wrap: wrap;
    gap: 6px 16px;
    padding: 0 4px;
    font-size: 13px;
    color: var(--c-ink-70);
  }
  .tlkey__k {
    display: inline-flex;
    align-items: center;
    gap: 7px;
  }
  .tlkey__k .tln {
    margin-top: 0;
  }
  /* Absolute in the page, as the scrim: a transformed ancestor makes fixed
     follow it, not the screen. */
  .dialog {
    position: absolute;
    left: 16px;
    right: 16px;
    top: 50%;
    transform: translateY(-50%);
    z-index: 6;
    max-height: calc(100% - 32px);
    overflow-y: auto;
    background: var(--bg-panel);
    border-radius: var(--r-xl);
    border: 1px solid var(--c-ink-12);
    padding: 20px 18px;
    display: flex;
    flex-direction: column;
    gap: 14px;
    box-sizing: border-box;
  }
  .dialog__row {
    display: flex;
    gap: 10px;
  }
  .dialog__row .btn2 {
    flex: 1;
  }
  .btn--go {
    flex: 1.4;
    height: 50px;
  }
  .choice {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 13px 14px;
    border-radius: var(--r-14);
    border: 1px solid var(--c-ink-14);
    background: var(--c-ink-05);
    text-align: left;
    font: inherit;
    color: inherit;
    cursor: pointer;
    width: 100%;
    box-sizing: border-box;
  }
  .choice.is-sel {
    border-color: var(--c-lms-55);
    background: var(--c-lms-10);
  }
  .choice__head {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 16px;
  }
  .choice.is-sel b {
    color: var(--accent-lms);
  }
  .choice__sub {
    font-size: 13.5px;
    line-height: 1.4;
    color: var(--c-ink-70);
  }
  .radio {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    border: 2px solid var(--c-ink-40);
    box-sizing: border-box;
    flex-shrink: 0;
    position: relative;
  }
  .radio.is-on {
    border-color: var(--accent-lms);
  }
  .radio.is-on::after {
    content: '';
    position: absolute;
    left: 3px;
    top: 3px;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: var(--accent-lms);
  }
</style>
