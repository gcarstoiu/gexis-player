<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  Room correction on the phone, from *Before* to *Keep it* (ADR-0175;
  design/source/29 R05-R27; the flow George settled on 2026-11-04 and
  2026-11-05). The run itself is the player's (`room.run`): this page shows
  its step and sends the buttons, so a page closed and opened again picks up
  where it is.

  The calibration is the owner's to give (decision 4 as changed, George
  2026-11-05): the 90° file from miniDSP's page, chosen here.
-->
<script>
  import { cutFreq, cutGain, cutsHeading, dips, dipsLine, giveCalibration, MOVES, outputShort, peaksDown,
    runRoom, worseLine } from '../../lib/room.svelte.js';
  import RoomChart from './RoomChart.svelte';
  import RoomSeat from './RoomSeat.svelte';

  //: `full`: GET /room-correction; `onback`: to Settings · Audio; `onpage`:
  //: to the page (after Keep it, or Back from Before once measured).
  let { full, onback, onpage, flat = false } = $props();

  const MINIDSP = 'https://www.minidsp.com/products/acoustic-measurement/umik-1';
  const run = $derived(full?.run ?? null);
  const ended = $derived(full?.ended ?? null);
  let error = $state(null);
  let sending = $state(false);
  let ch = $state('L');
  let reading = $state(false);
  let fileInput = $state(null);

  //: The page opened onto a run already going (the design's R18).
  let resumed = $state(false);
  let firstStep = $state(undefined);
  $effect(() => {
    const step = run ? `${run.step}:${run.position}:${run.checking}` : null;
    if (firstStep === undefined) {
      firstStep = step;
      resumed = !!run && run.step !== 'place';
    } else if (step !== firstStep) {
      resumed = false;
    }
  });

  //: Which screen: the run's step, or how it ended, or Before.
  const screenName = $derived.by(() => {
    if (run) {
      if (run.step === 'countdown') return 'move';
      if (run.step === 'move' && run.checking) return 'move';
      return run.step;
    }
    if (ended && (ended.how === 'cancelled' || ended.how === 'failed')) return 'cancelled';
    return 'before';
  });
  const inRun = $derived(!!run);
  const counting = $derived(run?.step === 'countdown');
  const n = $derived(run?.position ?? 1);
  const checking = $derived(!!run?.checking);
  const pending = $derived(full?.pending ?? null);
  const speaker = $derived(pending?.chart?.speakers?.[ch] ?? null);
  const freqs = $derived(pending?.chart?.freqs ?? []);
  const tooQuiet = $derived(run?.step === 'level' && run.too_quiet);

  // ---- the buttons ---------------------------------------------------------------

  async function send(action) {
    if (sending) return;
    sending = true;
    error = null;
    try {
      await runRoom(action);
    } catch (e) {
      error = e.message;
    } finally {
      sending = false;
    }
  }
  async function finish(action) {
    await send(action);
  }
  //: *Done* tells the player the end has been shown - always sent, even
  //: with the last button's request still in flight.
  async function sayDone() {
    try {
      await runRoom('done');
    } catch {
      // Nothing to show: the end stays until another page says it.
    }
  }
  async function doneAndLeave(toPage) {
    await sayDone();
    if (toPage) onpage?.();
    else onback?.();
  }
  //: How a run that has ended takes this page: kept, to the page; discarded
  //: or nothing to cut, back to Audio; cancelled, its own screen. An end
  //: this page did not see happen (the page opened after it) is cleared
  //: quietly, and Before shows.
  let sawRun = $state(false);
  let handled = $state(null);
  $effect(() => {
    if (run) sawRun = true;
  });
  $effect(() => {
    const how = ended?.how;
    if (!how || handled === how || run) return;
    handled = how;
    if (how !== 'kept' && how !== 'discarded' && how !== 'done') return;
    if (!sawRun) sayDone();
    else doneAndLeave(how === 'kept');
  });

  async function pick(event) {
    const file = event.currentTarget.files?.[0];
    event.currentTarget.value = '';
    if (!file) return;
    reading = true;
    error = null;
    try {
      await giveCalibration(await file.text(), file.name);
    } catch (e) {
      error = e.message;
    } finally {
      reading = false;
    }
  }

  // ---- Before ---------------------------------------------------------------------

  const mic = $derived(full?.microphone ?? { state: 'absent', calibration: null });
  const cal = $derived(mic.calibration);
  const why = $derived(full?.why_not ?? null);
  const checks = $derived.by(() => {
    const out = [];
    if (mic.state === 'absent') {
      out.push({ kind: 'warn', name: 'Plug in the UMIK-1', sub: "Into one of the player's USB ports. It is found by itself." });
    } else if (mic.state === 'other') {
      out.push({ kind: 'warn', name: 'This microphone is not supported yet', sub: 'Room correction measures with the miniDSP UMIK-1 for now.' });
    } else {
      out.push({ kind: 'ok', name: 'Microphone', sub: cal ? `miniDSP UMIK-1 · ${cal.serial}` : 'miniDSP UMIK-1' });
    }
    if (mic.state !== 'found') {
      out.push({ kind: 'wait', name: 'Calibration', sub: 'Its file from miniDSP, once the microphone is found' });
    } else if (reading) {
      out.push({ kind: 'busy', name: 'Calibration', sub: 'Reading the file…' });
    } else if (!cal) {
      out.push({ kind: 'warn', name: 'Its calibration file', sub: "Get the 90° file for this microphone from miniDSP's page, then choose it here.", give: true });
    } else {
      out.push({ kind: 'ok', name: 'Calibration', sub: `From miniDSP for ${cal.serial} · ${cal.angle}°`, another: true });
    }
    const playing = full?.playing;
    if (why === 'grouped') {
      out.push({ kind: 'warn', name: 'In a group', sub: 'Leave the group to measure the room.' });
    } else if (why === 'busy') {
      out.push({ kind: 'warn', name: 'An update is installing', sub: 'Measure once it has finished.' });
    } else {
      out.push({ kind: 'wait', name: 'A quiet room',
        sub: playing?.dsd ? 'About five minutes. DSD is playing: it stops when you start.'
          : playing?.source ? `About five minutes. ${playing.source} is playing: it stops when you start.`
            : 'About five minutes, music stops' });
    }
    return out;
  });

  // ---- each screen's words -------------------------------------------------------

  const moveText = (k) => `${k === 1 ? 'Back where your head was' : MOVES[k]}, at the same height, still pointing at the ceiling. Step back, then tap Measure here.`;
  const head = $derived.by(() => {
    switch (screenName) {
      case 'before': return ['Correct the bass your room adds', 'The player plays short sweeps through your speakers and listens with a measurement microphone at your seat. It then cuts the peaks the room makes below 250 Hz.'];
      case 'place': return ['Put the microphone where your head is', ''];
      case 'level': return tooQuiet
        ? [`Only ${run.level_db ?? '—'} dB at the seat`, "At the player's maximum level. Turn the amplifier up a little and try again."]
        : ['Finding the level', run.aim_db == null ? 'Listening to the room first.'
          : `Soft noise, getting louder until the microphone hears about ${run.aim_db} dB.`];
      case 'measure': return [`Position ${n} of 5`, ''];
      case 'move': return [checking && n === 1 ? 'Move it back to position 1' : `Move it to position ${n}`, ''];
      case 'correction': return [cutsHeading(pending?.cuts), ''];
      case 'nothing': return ['Nothing to cut', ''];
      case 'checking': return ['Checking, with the correction on', ''];
      case 'result': return run?.expected ? [`${peaksDown(pending?.peaks_down)}, expected`, ''] : [peaksDown(pending?.peaks_down), ''];
      case 'cancelled': return ['Measuring cancelled', 'Nothing changed: the output is as it was. Music can play again.'];
      default: return ['', ''];
    }
  });
  const crumb = $derived({
    before: `Settings · Audio · ${outputShort(full?.output)}`, cancelled: `Settings · Audio · ${outputShort(full?.output)}`,
    place: 'Step 1 of 4', level: 'Step 2 of 4', measure: checking ? 'Checking' : 'Step 3 of 4',
    move: checking ? 'Checking' : 'Step 3 of 4', correction: 'Step 4 of 4', nothing: 'Step 4 of 4',
    checking: 'Checking', result: 'Step 4 of 4',
  }[screenName] ?? '');
  const tail = $derived.by(() => {
    if (screenName === 'place') return { text: `Music stops now, on every source.${full?.screen ? " The player's screen shows that it is measuring." : ''}`, ink: 'quiet' };
    if (screenName === 'correction') return { text: dipsLine(dips(speaker, freqs)), ink: 'quiet' };
    if (screenName === 'nothing') return { text: "Your room's bass is already near the target, so there is nothing worth cutting. Room correction stays off.", ink: 'body' };
    if (screenName === 'result' && !run?.expected) return { text: worseLine(pending?.worse), ink: 'ink' };
    if (screenName === 'result') return { text: 'The check was skipped: this is what the correction should do. Measure again to check it.', ink: 'body' };
    return null;
  });
  const track = $derived([1, 2, 3, 4, 5].map((i) => ({ n: i, state: i < n ? 'done' : i === n ? 'now' : 'next' })));
  const showTracker = $derived(['measure', 'move', 'checking'].includes(screenName));
  const showSeat = $derived(['place', 'measure', 'move', 'checking'].includes(screenName));
  const done = $derived(run?.done ?? []);
  //: The scale round the aim, as the design's 50 · 75 · 85 is round 75.
  const aim = $derived(run?.aim_db ?? 65);
  const levelPct = (db) => `${Math.max(0, Math.min(100, Math.round(((db - (aim - 25)) / 35) * 100)))}%`;
  const checkPct = $derived(`${Math.round(Math.max(0, Math.min(1, ((run?.progress ?? 0.8) - 0.8) / 0.2)) * 100)}%`);

  //: The foot: [quiet, second, primary], each [label, action] or null.
  const foot = $derived.by(() => {
    const cancel = ['Cancel', () => send('cancel')];
    switch (screenName) {
      case 'before': return [null, null, ['Measure', () => send('measure'), !full?.can_measure]];
      case 'place': return [cancel, null, ['Start', () => send('start')]];
      case 'level': return [cancel, null, tooQuiet ? ['Try again', () => send('again')] : null];
      case 'measure': return [cancel, null, null];
      case 'move': return counting ? [cancel, checking ? ['Skip', () => send('skip'), false, true] : null, null]
        : [cancel, checking ? ['Skip', () => send('skip'), false, true] : null, ['Measure here', () => send('next')]];
      case 'correction': return [['Discard', () => finish('discard')], null, ['Check it', () => send('check')]];
      case 'nothing': return [null, null, ['Done', () => finish('done')]];
      case 'checking': return [cancel, ['Skip', () => send('skip')], null];
      case 'result': return [['Discard', () => finish('discard')], null, ['Keep it', () => finish('keep')]];
      case 'cancelled': return [null, null, ['Done', () => doneAndLeave(!!full?.measured)]];
      default: return [null, null, null];
    }
  });
  const back = () => (full?.measured ? onpage?.() : onback?.());

  //: A speaker's row while a position is measured (R16-R18).
  function speakerRow(k) {
    const now = run?.speaker;
    const doneK = now === 'R' && k === 'L';
    const nowK = now === k;
    const noise = nowK && run?.noise;
    return {
      name: k === 'L' ? 'Left speaker' : 'Right speaker',
      kind: doneK ? 'ok' : nowK ? (noise ? 'warn' : 'playing') : 'wait',
      sub: doneK ? 'Two sweeps, they agree' : nowK ? (noise ? 'A noise spoiled this sweep. Measuring it again.' : `Playing · sweep ${run.sweep || 1} of 2`) : 'Two sweeps, after the left',
      amber: noise,
    };
  }
</script>

{#snippet mark(kind)}
  <span class="mark mark--{kind}" aria-hidden="true">
    {#if kind === 'ok'}<span class="tick"></span>{/if}
    {#if kind === 'warn'}!{/if}
    {#if kind === 'playing'}<span class="bars"><i></i><i></i><i></i></span>{/if}
  </span>
{/snippet}

<div class="flow" class:flow--flat={flat}>
  {#if !flat}<div class="weave"></div><div class="veil"></div>{/if}
  <div class="frame">
    <div class="top">
      {#if !inRun}
        <button class="back" type="button" aria-label="Back" data-dpad-back onclick={back}><span></span></button>
      {/if}
      <div class="top__text">
        <div class="title">{inRun ? 'Measure the room' : 'Room correction'}</div>
        <div class="crumb">{crumb}</div>
      </div>
    </div>

    <div class="scroll">
      {#if resumed && inRun}
        <div class="banner"><span class="banner__dot"></span><span>Picked up where it is. The measuring went on while this page was closed.</span></div>
      {/if}

      {#if showTracker}
        <div class="tracker">
          <div class="tracker__bar">{#each track as t (t.n)}<span class="seg seg--{t.state}"></span>{/each}</div>
          <span class="tracker__text">{checking || screenName === 'checking' ? `Checking · position ${n} of 5` : `Position ${n} of 5`}</span>
        </div>
      {/if}

      {#if head[0]}
        <div class="headblock">
          <div class="head" class:is-amber={tooQuiet}>{head[0]}</div>
          {#if screenName === 'result' && run?.expected}<span class="flag">Not checked</span>{/if}
          {#if head[1]}<div class="lead">{head[1]}</div>{/if}
        </div>
      {/if}

      {#if screenName === 'before'}
        <div class="card checks">
          {#each checks as c, i (c.name)}
            <div class="check" class:check--rule={i > 0}>
              {@render mark(c.kind)}
              <div class="check__text">
                <div class="check__name" class:is-amber={c.kind === 'warn'}>{c.name}</div>
                <div class="check__sub">{c.sub}</div>
              </div>
            </div>
            {#if c.give}
              <div class="give">
                <a class="chip chip--quiet" href={MINIDSP} target="_blank" rel="noopener noreferrer">miniDSP's page</a>
                <button type="button" class="chip chip--lit" onclick={() => fileInput?.click()}>Choose the file</button>
              </div>
            {/if}
            {#if c.another}
              <div class="give give--another">
                <button type="button" class="linkish" onclick={() => fileInput?.click()}>Choose another file</button>
              </div>
            {/if}
          {/each}
          <input class="file" type="file" accept=".txt,text/plain" bind:this={fileInput} onchange={pick} />
        </div>
        <div class="card power is-dim">
          <div class="power__text"><div class="power__title">Room correction</div><div class="power__note">Measure first</div></div>
          <span class="switch"><span></span></span>
        </div>
      {/if}

      {#if screenName === 'level'}
        <div class="card level">
          <div class="level__read">
            <span class="level__db" class:is-amber={tooQuiet}>{run.level_db ?? '—'}</span>
            <span class="level__unit">dB at the seat</span>
          </div>
          <div class="track">
            <div class="track__fill" class:is-amber={tooQuiet} style="width:{run.level_db == null ? '0%' : levelPct(run.level_db)}"></div>
            <div class="track__aim" style="left:{levelPct(aim)}"></div>
          </div>
          <div class="scale"><span>{aim - 25}</span><span class="scale__aim">{aim} dB · the aim</span><span>{aim + 10}</span></div>
        </div>
        <div class="note">Never above the maximum level set for this output.</div>
      {/if}

      {#if showSeat}
        <RoomSeat active={screenName === 'place' ? 1 : n} done={screenName === 'place' ? [] : done}
                  playing={screenName === 'measure' || screenName === 'checking' ? run?.speaker : null}
                  arrow={screenName === 'move' && n > 1} />
      {/if}

      {#if screenName === 'place'}
        <div class="after">On a stand at ear height, pointing at the ceiling. Then keep the room quiet: the measurement plays loud sweeps for a few seconds at a time.</div>
      {:else if screenName === 'move' && !counting}
        <div class="after">{moveText(n)}</div>
      {:else if screenName === 'checking'}
        <div class="after">The same five positions again, about a minute more.</div>
      {/if}

      {#if screenName === 'measure'}
        <div class="card speakers">
          {#each ['L', 'R'] as k, i (k)}
            {@const s = speakerRow(k)}
            <div class="check" class:check--rule={i > 0}>
              {@render mark(s.kind)}
              <div class="check__text">
                <div class="check__name">{s.name}</div>
                <div class="check__sub" class:is-amber={s.amber}>{s.sub}</div>
              </div>
            </div>
          {/each}
        </div>
        <div class="note">Nothing to do while it runs, about 25 seconds a position.</div>
      {/if}

      {#if counting}
        <div class="count">
          <span class="count__ring">{run.count}</span>
          <span class="count__text">Sweeps in {run.count}. Stay where you are and keep quiet.</span>
        </div>
      {/if}

      {#if screenName === 'checking'}
        <div class="progress"><div class="progress__fill" style="width:{checkPct}"></div></div>
        <div class="note">Skip keeps the correction as it is worked out, marked Not checked.</div>
      {/if}

      {#if ['correction', 'nothing', 'result'].includes(screenName) && pending}
        <div class="segs" role="group" aria-label="Speaker">
          {#each ['L', 'R'] as k (k)}
            <button type="button" class="segbtn" class:is-sel={ch === k} aria-pressed={ch === k} onclick={() => (ch = k)}>{k === 'L' ? 'Left' : 'Right'}</button>
          {/each}
        </div>
        <div class="card chartcard">
          <RoomChart surface="phone" {freqs} {speaker}
                     kind={screenName === 'nothing' ? '' : screenName === 'result' && !run?.expected ? 'measured' : 'expected'} />
        </div>
      {/if}

      {#if screenName === 'correction' && pending}
        {@const list = pending.cuts?.[ch] ?? []}
        <div class="card cuts">
          <div class="cuts__head"><span>{ch === 'L' ? 'Left' : 'Right'} speaker · {list.length} {list.length === 1 ? 'cut' : 'cuts'}</span><span class="rule"></span></div>
          <div class="cuts__grid">
            {#each list as c (c.freq)}
              <div class="cut"><span class="cut__f">{cutFreq(c)}</span><span class="cut__g">{cutGain(c)}</span></div>
            {/each}
          </div>
        </div>
      {/if}

      {#if tail}
        <div class="tail tail--{tail.ink}">{tail.text}</div>
      {/if}
      {#if error}<div class="error" role="status">{error}</div>{/if}
    </div>

    {#if foot[0] || foot[1] || foot[2]}
      <div class="foot">
        {#if foot[0]}<button type="button" class="btn btn--quiet" onclick={foot[0][1]} disabled={sending}>{foot[0][0]}</button>{/if}
        {#if foot[1]}<button type="button" class="btn btn--second" class:btn--fit={foot[1][3]} onclick={foot[1][1]} disabled={sending}>{foot[1][0]}</button>{/if}
        {#if foot[2]}<button type="button" class="btn btn--primary" class:is-dim={foot[2][2]} disabled={foot[2][2] || sending}
                             onclick={foot[2][1]}>{foot[2][0]}</button>{/if}
      </div>
    {/if}
  </div>
</div>

<style>
  .flow {
    position: absolute;
    inset: 0;
    z-index: 18;
    overflow: hidden;
    background: var(--bg-base);
    color: var(--ink);
    -webkit-tap-highlight-color: transparent;
    user-select: none;
  }
  .flow--flat {
    background: var(--bg-panel);
  }
  .weave {
    position: absolute;
    inset: -90px;
    background: repeating-linear-gradient(var(--weave-angle), var(--bg-weave-a) 0 48px, var(--bg-weave-b) 48px 96px);
    filter: blur(70px);
    transform: scale(1.14);
  }
  .veil {
    position: absolute;
    inset: 0;
    background: var(--cover-veil-deep);
  }
  .frame {
    position: relative;
    height: 100%;
    display: flex;
    flex-direction: column;
  }
  .top {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 16px;
    box-sizing: border-box;
    border-bottom: 1px solid var(--c-ink-09);
    padding: 14px 18px;
    min-height: 78px;
  }
  .back {
    width: 56px;
    height: 56px;
    border-radius: 50%;
    background: var(--ink-fill);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    border: 0;
    padding: 0;
    color: inherit;
  }
  .back:active {
    transform: scale(0.95);
  }
  .back span {
    width: 13px;
    height: 13px;
    border-left: 3px solid var(--ink);
    border-bottom: 3px solid var(--ink);
    transform: rotate(45deg);
    margin-left: 10px;
  }
  .top__text {
    flex: 1;
    min-width: 0;
  }
  .title {
    font-size: 23px;
    font-weight: 700;
    letter-spacing: -0.01em;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
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
  .banner {
    flex-shrink: 0;
    display: flex;
    gap: 12px;
    align-items: flex-start;
    padding: 12px 14px;
    border-radius: var(--r-md);
    background: var(--c-lms-10);
    border: 1px solid var(--c-lms-35);
    font-size: 14px;
    line-height: 1.4;
    text-wrap: pretty;
  }
  .banner__dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--accent-lms);
    flex-shrink: 0;
    margin-top: 6px;
  }
  .tracker {
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .tracker__bar {
    display: flex;
    gap: 4px;
  }
  .seg {
    flex: 1;
    height: 4px;
    border-radius: 2px;
    background: var(--c-ink-12);
  }
  .seg--done {
    background: var(--accent-lms);
  }
  .seg--now {
    background: var(--c-lms-50);
  }
  .tracker__text {
    font-family: var(--font-mono);
    font-size: 12px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--ink-quiet);
  }
  .headblock {
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding-top: 2px;
  }
  .head {
    font-size: 25px;
    font-weight: 800;
    letter-spacing: -0.015em;
    line-height: 1.15;
    text-wrap: balance;
  }
  .lead {
    font-size: 16px;
    line-height: 1.45;
    color: var(--c-ink-78);
    text-wrap: pretty;
  }
  .is-amber {
    color: var(--rc-without);
  }
  .flag {
    align-self: flex-start;
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
  .card {
    flex-shrink: 0;
    border-radius: var(--r-15);
    background: var(--c-white-05);
    border: 1px solid var(--ink-line);
  }
  .check {
    display: flex;
    align-items: flex-start;
    gap: 14px;
    padding: 16px 18px;
    box-sizing: border-box;
  }
  .speakers .check {
    padding: 15px 18px;
  }
  .check--rule {
    border-top: 1px solid var(--c-ink-08);
  }
  .check__text {
    flex: 1;
    min-width: 0;
  }
  .check__name {
    font-size: 17px;
    font-weight: 600;
    line-height: 1.3;
    text-wrap: pretty;
  }
  .check__sub {
    font-size: 14px;
    line-height: 1.4;
    color: var(--ink-quiet);
    margin-top: 3px;
    text-wrap: pretty;
  }
  .check__sub.is-amber {
    color: var(--rc-without);
  }
  .mark {
    width: 26px;
    height: 26px;
    flex-shrink: 0;
    position: relative;
    display: block;
    margin-top: -1px;
    border-radius: 50%;
    box-sizing: border-box;
  }
  .mark--ok {
    background: var(--c-lms-16);
  }
  .tick {
    position: absolute;
    left: 9px;
    top: 5px;
    width: 6px;
    height: 11px;
    border-right: 2.5px solid var(--accent-lms);
    border-bottom: 2.5px solid var(--accent-lms);
    transform: rotate(45deg);
  }
  .mark--wait {
    border: 2px dashed var(--c-ink-40);
    transform: scale(0.85);
  }
  .mark--warn {
    background: var(--c-warn-16);
    color: var(--rc-without);
    font-family: var(--font-mono);
    font-weight: 700;
    font-size: 15px;
    line-height: 26px;
    text-align: center;
  }
  .mark--busy {
    border: 2.5px solid var(--c-lms-20);
    border-top-color: var(--accent-lms);
    transform: scale(0.85);
    animation: spin 900ms linear infinite;
  }
  .mark--playing {
    background: var(--accent-lms);
  }
  .bars {
    position: absolute;
    left: 7px;
    top: 7px;
    width: 12px;
    height: 12px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .bars i {
    width: 2px;
    border-radius: 1px;
    background: var(--ink-on-accent);
    display: block;
  }
  .bars i:nth-child(1) { height: 6px; }
  .bars i:nth-child(2) { height: 12px; }
  .bars i:nth-child(3) { height: 8px; }
  @keyframes spin {
    to { transform: scale(0.85) rotate(360deg); }
  }
  @media (prefers-reduced-motion: reduce) {
    .mark--busy { animation: none; }
  }
  .give {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    padding: 0 18px 18px 58px;
  }
  .give--another {
    padding-top: 0;
    margin-top: -8px;
  }
  .chip {
    height: 48px;
    padding: 0 16px;
    border-radius: var(--r-md);
    box-sizing: border-box;
    display: inline-flex;
    align-items: center;
    font: inherit;
    font-size: 15px;
    font-weight: 700;
    text-decoration: none;
    color: inherit;
  }
  .chip:active {
    transform: scale(0.95);
  }
  .chip--quiet {
    background: var(--c-ink-05);
    border: 1px solid var(--ink-line);
    color: var(--ink-body);
  }
  .chip--lit {
    background: var(--c-lms-16);
    border: 1px solid var(--c-lms-55);
    color: var(--accent-lms);
  }
  .linkish {
    border: 0;
    padding: 6px 0;
    background: none;
    font: inherit;
    font-size: 14px;
    font-weight: 600;
    color: var(--accent-lms);
  }
  .file {
    display: none;
  }
  .power {
    display: flex;
    align-items: center;
    gap: 18px;
    padding: 14px 20px;
    box-sizing: border-box;
  }
  .power.is-dim {
    opacity: 0.5;
  }
  .power__text {
    flex: 1;
    min-width: 0;
  }
  .power__title {
    font-size: 18px;
    font-weight: 600;
  }
  .power__note {
    font-size: 14px;
    color: var(--ink-quiet);
    margin-top: 4px;
  }
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
  }
  .level {
    border-radius: var(--r-18);
    padding: 20px 20px 18px;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }
  .level__read {
    display: flex;
    align-items: baseline;
    gap: 10px;
  }
  .level__db {
    font-family: var(--font-mono);
    font-size: 56px;
    font-weight: 600;
    line-height: 1;
    letter-spacing: -0.02em;
    color: var(--accent-lms);
  }
  .level__db.is-amber {
    color: var(--rc-without);
  }
  .level__unit {
    font-size: 17px;
    font-weight: 600;
    color: var(--ink-muted);
  }
  .track {
    position: relative;
    height: 12px;
    border-radius: var(--r-6);
    background: var(--rc-run-track);
  }
  .track__fill {
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    border-radius: var(--r-6);
    background: var(--accent-lms);
    transition: width 300ms ease;
  }
  .track__fill.is-amber {
    background: var(--rc-without);
  }
  .track__aim {
    position: absolute;
    top: -6px;
    bottom: -6px;
    width: 2px;
    margin-left: -1px;
    background: var(--ink);
  }
  .scale {
    display: flex;
    white-space: nowrap;
    justify-content: space-between;
    font-family: var(--font-mono);
    font-size: 12px;
    color: var(--ink-quiet);
  }
  .scale__aim {
    color: var(--ink);
  }
  .note {
    font-size: 14px;
    line-height: 1.45;
    color: var(--ink-quiet);
    padding: 0 4px;
    text-wrap: pretty;
  }
  .after {
    font-size: 16px;
    line-height: 1.45;
    color: var(--c-ink-78);
    text-wrap: pretty;
    padding: 0 2px;
  }
  .count {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 18px;
    padding: 14px 18px;
    border-radius: var(--r-18);
    background: var(--c-lms-08);
    border: 1px solid var(--c-lms-35);
  }
  .count__ring {
    width: 72px;
    height: 72px;
    border-radius: 50%;
    box-sizing: border-box;
    border: 3px solid var(--accent-lms);
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: var(--font-mono);
    font-size: 38px;
    font-weight: 600;
    color: var(--accent-lms);
    flex-shrink: 0;
  }
  .count__text {
    font-size: 16px;
    line-height: 1.4;
    text-wrap: pretty;
  }
  .progress {
    position: relative;
    height: 10px;
    border-radius: var(--r-5);
    background: var(--rc-run-track);
    flex-shrink: 0;
  }
  .progress__fill {
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    border-radius: var(--r-5);
    background: var(--accent-lms);
    transition: width 300ms ease;
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
  .segbtn.is-sel {
    background: var(--c-lms-16);
    border-color: var(--c-lms-55);
    color: var(--accent-lms);
  }
  .chartcard {
    border-radius: var(--r-18);
    padding: 14px 12px 12px 6px;
    box-sizing: border-box;
  }
  .cuts {
    padding: 14px 18px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .cuts__head {
    display: flex;
    align-items: center;
    gap: 12px;
    font-family: var(--font-mono);
    font-size: 12px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    white-space: nowrap;
    color: var(--ink-quiet);
  }
  .rule {
    flex: 1;
    height: 1px;
    background: var(--ink-line);
  }
  .cuts__grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px 16px;
  }
  .cut {
    display: flex;
    white-space: nowrap;
    justify-content: space-between;
    gap: 8px;
    font-family: var(--font-mono);
    font-size: 15px;
    font-variant-numeric: tabular-nums;
  }
  .cut__f {
    color: var(--c-ink-78);
  }
  .cut__g {
    font-weight: 600;
    color: var(--rc-before);
  }
  .tail {
    font-size: 15px;
    line-height: 1.45;
    padding: 0 4px;
    text-wrap: pretty;
  }
  .tail--quiet {
    color: var(--ink-quiet);
  }
  .tail--body {
    color: var(--c-ink-78);
  }
  .tail--ink {
    color: var(--ink);
  }
  .error {
    font-size: 15px;
    line-height: 1.4;
    color: var(--rc-without);
    padding: 0 4px;
  }
  .foot {
    flex-shrink: 0;
    display: flex;
    gap: 10px;
    padding: 12px 16px 22px;
    box-sizing: border-box;
    border-top: 1px solid var(--c-ink-09);
    background: var(--c-ground-55);
  }
  .btn {
    height: 52px;
    padding: 0 20px;
    border-radius: var(--r-15);
    box-sizing: border-box;
    display: flex;
    align-items: center;
    justify-content: center;
    font: inherit;
    font-size: 16px;
    white-space: nowrap;
    color: inherit;
  }
  .btn:active {
    transform: scale(0.97);
  }
  .btn--quiet {
    font-weight: 600;
    color: var(--ink-body);
    background: var(--c-ink-05);
    border: 1px solid var(--ink-line);
  }
  .btn--quiet:active {
    transform: scale(0.95);
  }
  .btn--second {
    flex: 1;
    font-weight: 700;
    background: var(--c-ink-08);
    border: 1px solid var(--c-ink-16);
  }
  .btn--fit {
    flex: 0 0 auto;
    padding: 0 16px;
  }
  .btn--primary {
    flex: 1;
    font-weight: 800;
    background: var(--accent-lms);
    color: var(--ink-on-accent);
    border: 0;
  }
  .btn.is-dim {
    opacity: 0.4;
    pointer-events: none;
  }
</style>
