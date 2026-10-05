<script>
  // ADR-0119 decision C: a note's https:// address is a link that opens a
  // new tab, shown without the scheme (George: "Claim token from
  // plex.tv/claim. The link is tapable").
  //
  // `links` is off where the note sits inside a row's own button - a link
  // inside a button is not something a browser can deliver a tap to - and
  // there the address reads as text, as before.
  let { text = '', links = true } = $props();

  const ADDRESS = /(https:\/\/[^\s)]+[^\s).,;:!?])/;
  const parts = $derived(
    String(text)
      .split(ADDRESS)
      .map((part, i) => (i % 2 ? { href: part, shown: part.replace(/^https:\/\//, '') } : { plain: part })),
  );
</script>

{#each parts as part, i (i)}{#if part.href}{#if links}<a class="note-link" href={part.href} target="_blank" rel="noopener noreferrer">{part.shown}</a>{:else}{part.shown}{/if}{:else}{part.plain}{/if}{/each}

<style>
  .note-link {
    color: var(--accent-lms);
    text-decoration: underline;
    text-underline-offset: 2px;
  }
</style>
