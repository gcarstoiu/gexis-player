"""Claude Design .dc.html template -> Svelte markup, mechanically: inline
styles, sizes and keyframes stay exactly as designed; only the template
syntax changes. Top-level names are read from `V` (the design's
renderVals()), loop variables stay as they are."""
import re, sys

ASSETS = {}   # src -> svelte expression

def convert(markup, imports=None):
    imports = imports or {}
    loops = set()
    out = []
    pos = 0
    # Collect loop variable names first.
    for m in re.finditer(r'<sc-for[^>]*\bas="(\w+)"', markup):
        loops.add(m.group(1))

    def expr(e):
        e = e.strip()
        head = re.match(r'[A-Za-z_$][\w$]*', e)
        if head and head.group(0) not in loops and head.group(0) not in ('true', 'false', 'null'):
            return 'V.' + e
        return e

    def attrs_fix(tag):
        # Drop design-tool hints and hover/focus styles.
        tag = re.sub(r'\s(hint-[\w-]+|style-hover|style-focus)="[^"]*"', '', tag)
        tag = re.sub(r'\sref="\{\{\s*(\w+)\s*\}\}"', lambda m: ' bind:this={refs.' + m.group(1) + '}', tag)
        def whole(m):
            name, e = m.group(1), m.group(2)
            name = {'onClick': 'onclick', 'onChange': 'oninput', 'readOnly': 'readonly'}.get(name, name)
            return f' {name}={{{expr(e)}}}'
        tag = re.sub(r'\s([\w-]+)="\{\{\s*([^}]+?)\s*\}\}"', whole, tag)
        tag = re.sub(r'\{\{\s*([^}]+?)\s*\}\}', lambda m: '{' + expr(m.group(1)) + '}', tag)
        tag = re.sub(r'\ssrc="([^"{][^"]*)"', lambda m: ' src={' + imports.get(m.group(1), repr(m.group(1))) + '}', tag)
        return tag

    def dc_import(m):
        body = m.group(0)
        name = re.search(r'name="([^"]+)"', body).group(1).replace(' ', '')
        props = []
        for a, v in re.findall(r'\s([\w-]+)="([^"]*)"', body):
            if a in ('name', 'style') or a.startswith('hint-'):
                continue
            camel = re.sub(r'-(\w)', lambda x: x.group(1).upper(), a)
            mm = re.fullmatch(r'\{\{\s*([^}]+?)\s*\}\}', v)
            props.append(f'{camel}={{{expr(mm.group(1))}}}' if mm else f'{camel}="{v}"')
        return f'<{name} {" ".join(props)} />'

    markup = re.sub(r'<dc-import\b[^>]*>\s*</dc-import>', dc_import, markup)
    markup = re.sub(r'<sc-if value="\{\{\s*([^}]+?)\s*\}\}"[^>]*>', lambda m: '{#if ' + expr(m.group(1)) + '}', markup)
    markup = markup.replace('</sc-if>', '{/if}')
    markup = re.sub(r'<sc-for list="\{\{\s*([^}]+?)\s*\}\}" as="(\w+)"[^>]*>', lambda m: '{#each ' + expr(m.group(1)) + ' as ' + m.group(2) + '}', markup)
    markup = markup.replace('</sc-for>', '{/each}')
    # Tags: fix attributes; text: {{ }} -> { }.
    parts = re.split(r'(<[^>!/][^>]*>)', markup)
    for i, p in enumerate(parts):
        if p.startswith('<') and not p.startswith('</'):
            parts[i] = attrs_fix(p)
        else:
            parts[i] = re.sub(r'\{\{\s*([^}]+?)\s*\}\}', lambda m: '{' + expr(m.group(1)) + '}', p)
    out = ''.join(parts)
    # A void <input ...> written without a slash.
    out = re.sub(r'(<input\b[^>]*?)(?<!/)>', r'\1 />', out)
    # React keeps a space that starts an element's text; Svelte trims it.
    out = re.sub(r'>( +)([^<\s{])', lambda m: '>' + '&#32;' * len(m.group(1)) + m.group(2), out)
    # The player bundles Nunito Sans as a variable font under its own name.
    out = out.replace("font-family:'Nunito Sans',", "font-family:'Nunito Sans Variable','Nunito Sans',")
    return out

if __name__ == '__main__':
    src = open(sys.argv[1]).read()
    body = src[src.index('</helmet>') + len('</helmet>') if '</helmet>' in src else src.index('<x-dc>') + 6: src.index('</x-dc>')]
    print(convert(body))
