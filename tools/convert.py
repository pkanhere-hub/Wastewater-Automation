"""Convert the MBBR STP slide (pptx) into a grouped, id-addressable SVG.

Each plant component becomes <g id="..." class="component" data-label="...">
so a later "tap to light up" feature can target it directly.
"""
import re, sys, html
import xml.etree.ElementTree as ET

NS = {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
      'p': 'http://schemas.openxmlformats.org/presentationml/2006/main'}
A = '{%s}' % NS['a']
P = '{%s}' % NS['p']
EMU = 9525.0  # EMU per SVG px (12192000 / 1280)
ACCENT1 = '4472C4'

slide = ET.parse(sys.argv[1]).getroot()
out_path = sys.argv[2]

# component id, display label, name patterns (regex on shape name / callout text)
COMPONENTS = [
    ('raw-sewage-inlet', 'Raw sewage inlet', [r'^Label_194$', r'^Inlet_']),
    ('bar-screen', 'Bar Screen Chamber', [r'^BarScreen_', r'^Screen_Bar_', r'^Label_238$']),
    ('pipe-screen-to-trap', 'Pipe: screen to grease trap', [r'^Flow_196$']),
    ('oil-grease-trap', 'Oil & Grease Trap', [r'^OGTrap_', r'^Label_239$']),
    ('pipe-trap-to-eq', 'Pipe: grease trap to EQ tank', [r'^Flow_197$']),
    ('eq-tank', 'Equalization Tank', [r'^EQTank_', r'^EQ_Diffuser', r'^EQ_Bubble', r'^Label_240$']),
    ('eq-lift-pump', 'EQ submersible lift pump', [r'^EQ_LiftPump']),
    ('pipe-eq-to-mbbr1', 'Pipe: EQ lift to MBBR-1', [r'^LiftPipe_']),
    ('mbbr-1', 'MBBR Reactor 1', [r'^MBBR1_', r'^Label_241$']),
    ('pipe-mbbr1-to-mbbr2', 'Pipe: MBBR-1 to MBBR-2', [r'^Flow_201$']),
    ('mbbr-2', 'MBBR Reactor 2', [r'^MBBR2_', r'^Label_242$']),
    ('pipe-mbbr2-to-settler', 'Pipe: MBBR-2 to tube settler', [r'^Flow_202$']),
    ('tube-settler', 'Tube Settler', [r'^Settler_', r'^Label_243$']),
    ('air-blower', 'Air blower', [r'^Blower_', r'^callout:Air blower$']),
    ('air-header', 'Air header and drops', [r'^AirHeader_', r'^AirDrop_']),
    ('pipe-clarified', 'Clarified water line', [r'^ClarifiedPipe_', r'^Label_229$']),
    ('sludge-line', 'Excess sludge line', [r'^SludgePipe_', r'^SludgeOut_', r'^Label_237$']),
    ('sludge-pump', 'Sludge recirculation pump', [r'^Group 373$', r'^SludgePump_Eye_235$', r'^callout:Sludge Recirculation$']),
    ('filter-feed-tank', 'Filter Feed Tank', [r'^FilterFeedTank_', r'^Label_352$']),
    ('pipe-feed-suction', 'Feed pump suction', [r'^FeedSuction_']),
    ('filter-feed-pump', 'Filter feed pump', [r'^FilterFeedPump_', r'^Label_353$', r'^callout:Feed Pump$']),
    ('pipe-to-psf', 'Pipe: feed pump to sand filter', [r'^PSF_Inlet_']),
    ('pressure-sand-filter', 'Pressure Sand Filter', [r'^PSF_', r'^Label_354$']),
    ('pipe-psf-to-acf', 'Pipe: sand filter to carbon filter', [r'^ACF_Inlet_']),
    ('activated-carbon-filter', 'Activated Carbon Filter', [r'^ACF_', r'^Label_355$']),
    ('pipe-acf-outlet', 'Pipe: carbon filter outlet', [r'^Ozone_Inlet_', r'^ToTreatedTank_']),
    ('ozone-vent', 'Off-gas ozone destructor vent', [r'^Vent_', r'^Label_333$']),
    ('treated-water-tank', 'Treated Water Tank', [r'^TreatedWaterTank_', r'^extra:treated-label$']),
    ('naocl-dosing', 'NaOCl dosing', [r'^NaOCl', r'^Label_343$']),
    ('raw-water-pump', 'Raw water pump', [r'^Group 374$', r'^callout:Raw Water Pump$']),
    ('level-sensor-eq', 'Level sensor: EQ tank', [r'^Oval 384$']),
    ('level-sensor-filter-feed', 'Level sensor: filter feed tank', [r'^Oval 386$']),
    ('level-sensor-treated', 'Level sensor: treated water tank', [r'^Oval 388$']),
]

# Callouts moved so they no longer sit on top of the tank labels (x, y, w, h, size in 1/100 pt)
CALLOUT_MOVES = {
    'Raw Water Pump': (3520440, 3296000, 1371600, 240000, 1400),
    'Sludge Recirculation': (9420000, 3128509, 1300000, 694944, None),
    'Feed Pump': (8540496, 5806440, 1463040, 320040, 1600),
}


SUBTITLE_GREY = '#4B5563'
DROP_SHAPES = {'Label_353'}  # "Feed pumps" note; the Feed Pump callout already names it
# Re-spacing so nothing overlaps: group -> new top-left (EMU); shape -> override box
GROUP_MOVES = {'Group 374': (3557016, 2880360)}  # raw water pump, off the EQ tank label
SHAPE_MOVES = {'Label_194': (137160, 1335024, 548640, 320040, None)}  # "Raw sewage", clear of the flow meter


def comp_for(key):
    for cid, label, pats in COMPONENTS:
        if any(re.search(p, key) for p in pats):
            return cid
    raise SystemExit('unassigned shape: ' + key)


def color(el):
    """Resolve a fill/line colour element (solidFill etc.)."""
    if el is None:
        return None
    c = el.find(A + 'srgbClr')
    if c is not None:
        return '#' + c.get('val')
    c = el.find(A + 'schemeClr')
    if c is not None:
        base = {'bg1': 'FFFFFF', 'lt1': 'FFFFFF', 'tx1': '000000', 'accent1': ACCENT1}[c.get('val')]
        rgb = [int(base[i:i + 2], 16) for i in (0, 2, 4)]
        lm = c.find(A + 'lumMod')
        if lm is not None:
            rgb = [round(v * int(lm.get('val')) / 100000) for v in rgb]
        sh = c.find(A + 'shade')
        if sh is not None:
            rgb = [round(v * int(sh.get('val')) / 100000) for v in rgb]
        return '#%02X%02X%02X' % tuple(rgb)
    return None


def px(v):
    return round(float(v) / EMU, 2)


markers = {}


def marker_for(col):
    mid = 'arrow-' + col.lstrip('#').lower()
    markers[mid] = col
    return mid


def text_width(s, size_px, bold):
    return len(s) * size_px * (0.44 if bold else 0.42)


def wrap(words_runs, width, size_px, bold):
    lines, cur = [], ''
    for w in words_runs.split(' '):
        trial = (cur + ' ' + w).strip()
        if cur and text_width(trial, size_px, bold) > width:
            lines.append(cur)
            cur = w
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


def render_text(sp, x, y, w, h, override_size=None):
    tb = sp.find(P + 'txBody')
    if tb is None:
        return ''
    paras = []
    default_col = '#FFFFFF' if sp.find(P + 'style') is not None else '#000000'
    for p in tb.findall(A + 'p'):
        runs = p.findall(A + 'r')
        if not runs:
            continue
        txt = ''.join(r.find(A + 't').text or '' for r in runs)
        rpr = runs[0].find(A + 'rPr')
        sz = override_size or int(rpr.get('sz', 1800))
        bold = rpr.get('b') == '1'
        col = color(rpr.find(A + 'solidFill')) or default_col
        if col.upper() == SUBTITLE_GREY:
            continue  # unit subtitles ("Coarse + fine screens" etc.) are left off the tablet view
        ppr = p.find(A + 'pPr')
        algn = ppr.get('algn', 'l') if ppr is not None else 'l'
        paras.append((txt, sz / 100 * 12700 / EMU, bold, col, algn))
    if not paras:
        return ''
    body = tb.find(A + 'bodyPr')
    anchor = body.get('anchor', 't')
    lines = []
    for txt, size, bold, col, algn in paras:
        for ln in wrap(txt, w + 2, size, bold):
            lines.append((ln, size, bold, col, algn))
    total = sum(l[1] * 1.2 for l in lines)
    cy = y + (h - total) / 2 if anchor == 'ctr' else y
    cx = x + w / 2
    parts = []
    for ln, size, bold, col, algn in lines:
        cy += size * 1.2
        tx, anc = {'l': (x, 'start'), 'r': (x + w, 'end')}.get(algn, (cx, 'middle'))
        parts.append('<text x="%.2f" y="%.2f" font-size="%.2f"%s fill="%s" text-anchor="%s">%s</text>' % (
            tx, cy - size * 0.28, size, ' font-weight="700"' if bold else '', col, anc, html.escape(ln, quote=False)))
    return ''.join(parts)


def render_shape(sp, dx=0, dy=0, override=None):
    sppr = sp.find(P + 'spPr')
    xfrm = sppr.find(A + 'xfrm')
    off, ext = xfrm.find(A + 'off'), xfrm.find(A + 'ext')
    x, y = px(int(off.get('x')) + dx), px(int(off.get('y')) + dy)
    w, h = px(ext.get('cx')), px(ext.get('cy'))
    size_override = None
    if override:
        x, y, w, h = (px(v) for v in override[:4])
        size_override = override[4]
    flipH, flipV = xfrm.get('flipH') == '1', xfrm.get('flipV') == '1'

    fill = color(sppr.find(A + 'solidFill'))
    style = sp.find(P + 'style')
    if fill is None and style is not None and sppr.find(A + 'noFill') is None:
        fill = '#' + ACCENT1
    ln = sppr.find(A + 'ln')
    stroke, sw, dash, tail = None, None, None, False
    if ln is not None and len(ln):
        stroke = color(ln.find(A + 'solidFill'))
        sw = px(ln.get('w', 12700))
        d = ln.find(A + 'prstDash')
        dash = d is not None and d.get('val') == 'dash'
        tail = ln.find(A + 'tailEnd') is not None
    elif style is not None:
        stroke = color(style.find(A + 'lnRef'))
        sw = px(12700)

    geom = sppr.find(A + 'prstGeom')
    prst = geom.get('prst') if geom is not None else 'cust'
    attrs = ' fill="%s"' % (fill or 'none')
    if stroke:
        attrs += ' stroke="%s" stroke-width="%s"' % (stroke, sw)
        if dash:
            attrs += ' stroke-dasharray="%s %s"' % (sw * 4, sw * 3)
    out = ''
    if prst == 'line':
        x1, x2 = (x + w, x) if flipH else (x, x + w)
        y1, y2 = (y + h, y) if flipV else (y, y + h)
        m = ' marker-end="url(#%s)"' % marker_for(stroke) if tail else ''
        out = '<line x1="%s" y1="%s" x2="%s" y2="%s" fill="none" stroke="%s" stroke-width="%s"%s%s/>' % (
            x1, y1, x2, y2, stroke, sw,
            ' stroke-dasharray="%s %s"' % (round(sw * 4, 2), round(sw * 3, 2)) if dash else '', m)
    elif prst == 'rect':
        if fill or stroke:
            out = '<rect x="%s" y="%s" width="%s" height="%s"%s/>' % (x, y, w, h, attrs)
    elif prst == 'roundRect':
        r = min(w, h) * 0.16667
        out = '<rect x="%s" y="%s" width="%s" height="%s" rx="%.2f"%s/>' % (x, y, w, h, r, attrs)
    elif prst == 'ellipse':
        out = '<ellipse cx="%.2f" cy="%.2f" rx="%.2f" ry="%.2f"%s/>' % (x + w / 2, y + h / 2, w / 2, h / 2, attrs)
    else:
        path = sppr.find(A + 'custGeom/' + A + 'pathLst/' + A + 'path')
        pw, ph = float(path.get('w')), float(path.get('h'))
        d = []
        for el in path:
            tag = el.tag.split('}')[1]
            if tag == 'close':
                d.append('Z')
                continue
            pt = el.find(A + 'pt')
            d.append('%s%.2f %.2f' % ({'moveTo': 'M', 'lnTo': 'L'}[tag],
                                      x + float(pt.get('x')) / pw * w, y + float(pt.get('y')) / ph * h))
        out = '<path d="%s"%s stroke-linejoin="round"/>' % (' '.join(d), attrs)
    return out + render_text(sp, x, y, w, h, size_override)


def key_of(el):
    name = el.find('.//' + P + 'cNvPr').get('name')
    if el.tag == P + 'sp':
        ts = [t.text or '' for t in el.iter(A + 't')]
        if name == 'Label_211' or name == 'Label_343':
            if ''.join(ts) and name == 'Label_211':
                return 'callout:' + ''.join(ts), ''.join(ts)
    return name, None


groups, order = {}, []
tree = slide.find(P + 'cSld/' + P + 'spTree')
for el in tree:
    if el.tag not in (P + 'sp', P + 'grpSp'):
        continue
    key, callout = key_of(el)
    if key in DROP_SHAPES:
        continue
    cid = comp_for(key)
    if el.tag == P + 'grpSp':
        gx = el.find(P + 'grpSpPr/' + A + 'xfrm')
        ox, oy = GROUP_MOVES.get(key, (int(gx.find(A + 'off').get('x')), int(gx.find(A + 'off').get('y'))))
        dx = ox - int(gx.find(A + 'chOff').get('x'))
        dy = oy - int(gx.find(A + 'chOff').get('y'))
        svg = ''.join(render_shape(c, dx, dy) for c in el.findall(P + 'sp'))
    elif callout:
        svg = '<g class="callout">%s</g>' % render_shape(el, override=CALLOUT_MOVES.get(callout))
    else:
        svg = render_shape(el, override=SHAPE_MOVES.get(key))
    if cid not in groups:
        groups[cid] = []
        order.append(cid)
    groups[cid].append(svg)

# The treated water tank has no name label on the slide; add one in the same style as the others.
groups['treated-water-tank'].append(
    '<text x="%.2f" y="%.2f" font-size="14" font-weight="700" fill="#111827" text-anchor="middle">Treated Water Tank</text>'
    % (px(2943107 + 1463040 / 2), px(4798027) + 22))



def flow_meter(cx, cy):
    """Inline flow meter on a horizontal pipe at (cx, cy): spool body, flanges and a dial below."""
    dy = cy + 27
    return (
        '<rect x="%.2f" y="%.2f" width="22" height="14" rx="2" fill="#64748B" stroke="#334155" stroke-width="1.2"/>'
        '<rect x="%.2f" y="%.2f" width="3.5" height="20" fill="#334155"/>'
        '<rect x="%.2f" y="%.2f" width="3.5" height="20" fill="#334155"/>'
        '<path d="M%.2f %.2f V%.2f" stroke="#334155" stroke-width="3"/>'
        '<circle cx="%.2f" cy="%.2f" r="13" fill="#FFFFFF" stroke="#1F3A5F" stroke-width="2.4"/>'
        '<path d="M%.2f %.2f A9 9 0 0 1 %.2f %.2f" fill="none" stroke="#94A3B8" stroke-width="2"/>'
        '<path d="M%.2f %.2f L%.2f %.2f" stroke="#D97706" stroke-width="2.2" stroke-linecap="round"/>'
        '<circle cx="%.2f" cy="%.2f" r="2" fill="#1F3A5F"/>'
        '<text x="%.2f" y="%.2f" font-size="10.5" font-weight="700" fill="#1F3A5F" text-anchor="middle">Flow meter</text>'
    ) % (cx - 11, cy - 7, cx - 14, cy - 10, cx + 10.5, cy - 10,
         cx, cy + 7, dy - 13,
         cx, dy, cx - 8, dy + 3, cx + 8, dy + 3,
         cx, dy, cx + 6, dy - 5, cx, dy, cx, dy + 26)


# Flow meters (not on the slide): one on the raw sewage inlet, one on the line into the treated water tank.
# The slide has no treated water outlet, so draw one leaving the tank's left wall near the floor.
OUT_Y, OUT_X1, OUT_X2, OUT_DROP = 490, px(4406147), 525, 592
order += ['pipe-treated-outlet', 'flow-meter-inlet', 'flow-meter-treated', 'pressure-sensor-psf']
groups['pipe-treated-outlet'] = [
    '<path d="M%.2f %s H%s V%s" fill="none" stroke="#1F3A5F" stroke-width="4" stroke-linejoin="round" marker-end="url(#%s)"/>'
    % (OUT_X1, OUT_Y, OUT_X2, OUT_DROP, marker_for('#1F3A5F')),
    '<text x="%s" y="%s" font-size="11.3" font-weight="700" fill="#1F3A5F">Treated water out</text>' % (OUT_X2 + 8, OUT_DROP)]
groups['flow-meter-inlet'] = [flow_meter(px(137160 + 548640 / 2), px(1847088))]
groups['flow-meter-treated'] = [flow_meter(492, OUT_Y)]

# Pressure gauge on the riser from the filter feed pump up to the sand filter.
PX, PY = px(8796528), 432
groups['pressure-sensor-psf'] = [
    '<path d="M%.2f %s H%.2f" stroke="#334155" stroke-width="3"/>' % (PX, PY, PX + 13)
    + '<circle cx="%.2f" cy="%s" r="12" fill="#FFFFFF" stroke="#1F3A5F" stroke-width="2.4"/>' % (PX + 25, PY)
    + '<path d="M%.2f %.2f A8 8 0 1 1 %.2f %.2f" fill="none" stroke="#94A3B8" stroke-width="2"/>' % (PX + 19, PY + 5, PX + 31, PY + 5)
    + '<path d="M%.2f %s L%.2f %.2f" stroke="#DC2626" stroke-width="2" stroke-linecap="round"/>' % (PX + 25, PY, PX + 20, PY - 5)
    + '<circle cx="%.2f" cy="%s" r="1.8" fill="#1F3A5F"/>' % (PX + 25, PY)
    + '<text x="%.2f" y="%s" font-size="10.5" font-weight="700" fill="#1F3A5F" text-anchor="middle">Pressure</text>' % (PX + 27, PY + 26)]
labels_extra = {'pressure-sensor-psf': 'Pressure sensor: sand filter inlet'}
labels = {cid: label for cid, label, _ in COMPONENTS}
labels['flow-meter-inlet'] = 'Flow meter: raw sewage inlet'
labels['pipe-treated-outlet'] = 'Treated water outlet'
labels.update(labels_extra)
labels['flow-meter-treated'] = 'Flow meter: treated water outlet'
body = []
for cid in order:
    body.append('<g id="%s" class="component" data-label="%s">%s</g>' % (
        cid, html.escape(labels[cid]), ''.join(groups[cid])))

defs = ''.join(
    '<marker id="%s" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="3.2" markerHeight="3.2" orient="auto-start-reverse">'
    '<path d="M0 0 L10 5 L0 10 Z" fill="%s"/></marker>' % (mid, col) for mid, col in markers.items())

svg = ('<svg id="schematic" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" '
       'font-family="Calibri, Carlito, \'Segoe UI\', Arial, sans-serif" role="img" '
       'aria-label="MBBR sewage treatment plant pictorial schematic">'
       '<defs>%s</defs><rect id="sheet" width="1280" height="720" fill="#FFFFFF"/>%s</svg>') % (defs, ''.join(body))
open(out_path, 'w').write(svg)
print('components:', len(order), 'bytes:', len(svg))
