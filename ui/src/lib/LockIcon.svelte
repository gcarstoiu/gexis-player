<!--
  ADR-0046: the padlock that stands in for the volume control when the
  device is not attenuating. It is not a disabled slider - the design
  argued that case out by name, "indistinguishable from a bug" - it is a
  different control saying a different thing, and tapping it still opens
  the drawer, where the sentence is.
-->
<script>
  let { size = 30 } = $props();
</script>

<svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
  <rect x="5" y="10.5" width="14" height="9.5" rx="2.2"
        stroke="currentColor" stroke-width="1.8" />
  <path d="M8.4 10.5V7.9a3.6 3.6 0 0 1 7.2 0v2.6"
        stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
</svg>
