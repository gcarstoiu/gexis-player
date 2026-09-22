The gexis mark — four letter tiles whose diagonal gap is the x.

```jsx
<Logo size={96} />                                    {/* master, every tile lit */}
<Logo size={64} wordmark />                           {/* horizontal lockup      */}
<Logo size={64} lead="s" wordmark sublabel="sound" /> {/* a property signs itself */}
<Logo size={16} />                                    {/* favicon: tiles only    */}
<Logo size={64} mono="var(--ink)" wordmark />         {/* one colour             */}
```

`g e i s` run clockwise from the top of the diamond. `x` is never a tile — it
is the gap, which is why the mark holds at 16px where a five-letter wordmark
would not.

**`lead` is the only variant that means anything.** Each property takes the
letter its name starts with — g gazette, e engine room, i inbox, s sound — so
the lit tile identifies the surface you are on. Unset is the master mark and
belongs on anything covering all four.

**Letters disappear below 28px.** That is deliberate and measured: four
colours in a diamond are still recognisable at favicon size, four
letterforms are mush. Do not shrink the glyph to fit.

**Do not put this on the panel.** Now Playing and Settings are locked and
contain no mark; they set the device name in plain type, and that stays true.
The mark is for boot, the favicon, an avatar, print and the website. See
`../guidelines/brand-logo.html`.

`mono` flattens to a single colour for embossing, one-colour print and any
ground where four accents would fight the artwork.
