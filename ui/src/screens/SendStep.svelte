<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  **The Send step** (ADR-0138 §3), the same for the problem report and
  hardware feedback. George, 2026-10-11: *"user is given choice of direct
  submit to GitHub where everything will be prefilled or download zip file to
  send by email. This last step should be the same for the hardware
  feedback."*

  A GitHub link fills in text and cannot attach a file: the problem report's
  issue carries what happened and the log's last errors, and its file is an
  extra, offered beside the button (`attach`). The e-mail address is text with
  Copy - a mail link may open nothing (ADR-0125).
-->
<script>
  let { githubUrl = null, fileHref, fileName, fileKind, email, attach = false, githubSays } = $props();

  let copied = $state(false);
  async function copy() {
    try {
      await navigator.clipboard.writeText(email);
      copied = true;
      setTimeout(() => (copied = false), 2000);
    } catch {
      // No clipboard here: the address stays on screen to copy by hand.
    }
  }
</script>

<div class="send">
  <section class="way">
    <span class="way__name">On GitHub</span>
    <p class="way__text">{githubSays}</p>
    {#if githubUrl}
      <a class="way__go way__go--main" href={githubUrl} target="_blank" rel="noopener">Open it on GitHub ↗</a>
    {:else}
      <span class="way__go way__go--wait">Getting it ready…</span>
    {/if}
    {#if attach}
      <p class="way__text way__text--quiet">
        To add the full report, <a class="way__link" href={fileHref} download={fileName}>download it</a> and drag
        it onto the form.
      </p>
    {/if}
    <p class="way__text way__text--quiet">Needs a GitHub account. Press Create there to send it.</p>
  </section>

  <section class="way">
    <span class="way__name">By e-mail</span>
    <p class="way__text">Download {fileKind}, then send it to:</p>
    <p class="way__addr">
      <span>{email}</span>
      <button type="button" class="way__copy" onclick={copy}>{copied ? 'Copied' : 'Copy'}</button>
    </p>
    <a class="way__go" href={fileHref} download={fileName}>Download {fileName} ↓</a>
  </section>

  <p class="send__foot">
    Nothing is sent until you send it. Read it first: personal details are taken out by pattern, which can miss
    something.
  </p>
</div>

<style>
  .send {
    display: flex;
    flex-direction: column;
    gap: 14px;
  }
  .way {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 16px;
    border-radius: var(--r-lg, 16px);
    border: 1px solid var(--ink-line);
    background: var(--ink-fill);
  }
  .way__name {
    font-family: var(--font-mono);
    font-size: 12px;
    letter-spacing: var(--track-label, 0.08em);
    text-transform: uppercase;
    color: var(--accent-lms);
  }
  .way__text {
    margin: 0;
    font-size: 15px;
    line-height: 1.45;
    color: var(--ink-body, var(--ink));
  }
  .way__text--quiet {
    color: var(--ink-quiet);
    font-size: 14px;
  }
  .way__link {
    color: var(--accent-lms);
  }
  .way__go {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 52px;
    padding: 0 14px;
    border-radius: 15px;
    border: 1px solid rgba(233, 238, 242, 0.14);
    background: rgba(233, 238, 242, 0.07);
    color: var(--ink);
    font-size: 16px;
    font-weight: 600;
    text-align: center;
    text-decoration: none;
    overflow-wrap: anywhere;
  }
  .way__go--main {
    font-weight: 700;
    background: rgba(126, 214, 188, 0.16);
    border-color: rgba(126, 214, 188, 0.4);
    color: var(--accent-lms);
  }
  .way__go--wait {
    color: var(--ink-quiet);
  }
  .way__addr {
    margin: 0;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 10px;
    font-family: var(--font-mono);
    font-size: 14px;
    color: var(--ink);
    overflow-wrap: anywhere;
  }
  .way__copy {
    min-height: 36px;
    padding: 0 14px;
    border-radius: 10px;
    border: 1px solid var(--ink-line);
    background: var(--ink-fill);
    color: var(--ink);
    font: inherit;
    font-size: 14px;
  }
  .send__foot {
    margin: 0;
    font-size: 13px;
    line-height: 1.45;
    color: var(--ink-quiet);
  }
</style>
