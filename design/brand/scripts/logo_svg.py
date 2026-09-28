# SPDX-License-Identifier: GPL-3.0-or-later
"""The gexis sound lockup as a standalone SVG, for the README.

`<Logo size={64} lead="s" wordmark sublabel="sound" />`: geometry and colours
from display/Logo.jsx and tokens/brand.css. The letters are outlined, because
GitHub shows an SVG as an image and an image cannot load the brand fonts. It
sits on the panel's ground (--bg-base), since --ink and the coral label are
made for a dark ground and would not read on GitHub's light theme.

    python3 design/brand/scripts/logo_svg.py '#e9eef2' 20 > docs/assets/gexis-sound.svg

Needs fontTools and brotli (Plex Mono ships as woff2).
"""
import math, sys
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

DESIGN=Path(__file__).resolve().parents[2]
BRIC=DESIGN/'brand/assets/fonts/BricolageGrotesque[opsz,wdth,wght].ttf'
def inst(wght, opsz):
    return instantiateVariableFont(TTFont(BRIC), {'wght':wght,'opsz':max(12,min(96,opsz)),'wdth':100})
MONO=TTFont(DESIGN/'fonts/IBMPlexMono-SemiBold.woff2')

def text_path(font, s, size, x, baseline, tracking=0.0):
    gs=font.getGlyphSet(); cmap=font.getBestCmap(); upm=font['head'].unitsPerEm; sc=size/upm
    hmtx=font['hmtx']; d=[]; cx=x
    for ch in s:
        g=cmap[ord(ch)]; pen=SVGPathPen(gs)
        gs[g].draw(TransformPen(pen,(sc,0,0,-sc,cx,baseline)))
        d.append(pen.getCommands()); cx+=hmtx[g][0]*sc+tracking*size
    return ' '.join(d), cx-x-tracking*size
def advance(font,s,size,tracking=0.0):
    return text_path(font,s,size,0,0,tracking)[1]
def metrics(font,size):
    h=font['hhea'];u=font['head'].unitsPerEm;return h.ascent*size/u,-h.descent*size/u,h.lineGap*size/u

size=64; tile=size/2.235; gap=tile*0.235; radius=tile*0.265; glyph=tile*0.53
box=math.sqrt(2)*(tile*2+gap)
UNLIT='#2c404f'; UNLIT_INK='#7690a0'; S_FILL='#f2a48f'; S_INK='#3d1509'
ink=sys.argv[1] if len(sys.argv)>1 else '#e9eef2'
pad=float(sys.argv[2]) if len(sys.argv)>2 else 0

tiles_font=inst(800,glyph); word_font=inst(600,size*0.4)
wf=size*0.4; lf=max(11,size*0.115)
wa,wd,_=metrics(word_font,wf); ma,md,mg=metrics(MONO,lf)
word_w=advance(word_font,'gexis',wf,-0.015)
lab_w=advance(MONO,'SOUND',lf,0.20)+0.20*lf  # CSS letter-spacing trails the last glyph
col_w=max(word_w,lab_w); col_gap=size*0.045
word_h=wf; lab_h=ma+md+mg; col_h=word_h+col_gap+lab_h
W=box+size*0.19+col_w; H=max(box,col_h)
ox=oy=pad
out=[]
# tiles: grid centred in box, rotated 45deg about the box centre
c=box/2; g0=-(tile+gap/2)
cells=[('g',0,0),('e',1,0),('i',0,1),('s',1,1)]
ta,td,_=metrics(tiles_font,glyph)
out.append(f'<g transform="translate({ox+c:.3f},{oy+H/2:.3f}) rotate(45)">')
for l,col,row in cells:
    x=g0+col*(tile+gap); y=g0+row*(tile+gap); lit=(l=='s')
    out.append(f'<rect x="{x:.3f}" y="{y:.3f}" width="{tile:.3f}" height="{tile:.3f}" rx="{radius:.3f}" fill="{S_FILL if lit else UNLIT}"/>')
    tx=x+tile/2; ty=y+tile/2
    w=advance(tiles_font,l,glyph)
    base=(glyph-(ta+td))/2+ta-glyph/2
    d,_=text_path(tiles_font,l,glyph,-w/2,base)
    out.append(f'<g transform="translate({tx:.3f},{ty:.3f}) rotate(-45)"><path d="{d}" fill="{S_INK if lit else UNLIT_INK}"/></g>')
out.append('</g>')
x0=ox+box+size*0.19; top=oy+(H-col_h)/2
d,_=text_path(word_font,'gexis',wf,x0,top+(wf-(wa+wd))/2+wa,-0.015); out.append(f'<path d="{d}" fill="{ink}"/>')
lt=top+word_h+col_gap
d,_=text_path(MONO,'SOUND',lf,x0,lt+mg/2+ma,0.20); out.append(f'<path d="{d}" fill="{S_FILL}"/>')
TW=W+2*pad; TH=H+2*pad
bg=f'<rect width="{TW:.3f}" height="{TH:.3f}" rx="18" fill="#101a21"/>' if pad else ''
print(f'<svg xmlns="http://www.w3.org/2000/svg" width="{TW:.0f}" height="{TH:.0f}" viewBox="0 0 {TW:.3f} {TH:.3f}" role="img" aria-label="gexis sound">{bg}{"".join(out)}</svg>')
