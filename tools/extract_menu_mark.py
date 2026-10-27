#!/usr/bin/env python3
"""Extract the Omarchy menu mark (U+E900) from an omarchy.ttf into path data.

Stdlib-only TrueType reader for the single glyph the Omabuntu bar renders.
The upstream font also carries third-party agent marks, so the binary is not
imported; only Omarchy's own U+E900 outline is recorded, as path data in
upstream/omarchy-mark.json (same recorded-data pattern as config/menu/themes.json).

Usage: extract_menu_mark.py <omarchy.ttf> [--record <output.json>]
Prints the SVG path (y-flipped screen coordinates) on stdout.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path

GLYPH_CODEPOINT = 0xE900


def read_tables(data):
    count = struct.unpack_from('>H', data, 4)[0]
    tables = {}
    for i in range(count):
        offset = 12 + 16 * i
        tag = data[offset:offset + 4].decode('latin-1')
        table_offset, table_length = struct.unpack_from('>II', data, offset + 8)
        tables[tag] = (table_offset, table_length)
    return tables


def cmap_lookup(data, sub_offset, codepoint):
    """Return the glyph index for codepoint in a format 4 or 12 subtable."""
    fmt = struct.unpack_from('>H', data, sub_offset)[0]
    if fmt == 4:
        seg2 = struct.unpack_from('>H', data, sub_offset + 6)[0] * 2
        base = sub_offset + 14
        for seg in range(seg2 // 2):
            end = struct.unpack_from('>H', data, base + 2 * seg)[0]
            if codepoint > end:
                continue
            start = struct.unpack_from('>H', data, base + seg2 + 2 * seg)[0]
            if codepoint < start:
                return 0
            delta = struct.unpack_from('>h', data, base + 2 * seg2 + 2 * seg)[0]
            range_offset = struct.unpack_from('>H', data, base + 3 * seg2 + 2 * seg)[0]
            if range_offset == 0:
                return (codepoint + delta) & 0xFFFF
            index = base + 3 * seg2 + 2 * seg + range_offset + 2 * (codepoint - start)
            glyph = struct.unpack_from('>H', data, index)[0]
            return (glyph + delta) & 0xFFFF if glyph else 0
        return 0
    if fmt == 12:
        groups = struct.unpack_from('>I', data, sub_offset + 12)[0]
        for group in range(groups):
            offset = sub_offset + 16 + 12 * group
            start, end, first_glyph = struct.unpack_from('>III', data, offset)
            if start <= codepoint <= end:
                return first_glyph + (codepoint - start)
        return 0
    raise ValueError('Unsupported cmap subtable format: %d' % fmt)


def glyph_outline(data, tables, glyph_index):
    """Return [(x, y, on_curve)] point lists, one per contour, in font units."""
    head = tables['head'][0]
    loca_format = struct.unpack_from('>h', data, head + 50)[0]
    loca = tables['loca'][0]
    if loca_format == 0:
        starts = struct.unpack_from('>H', data, loca + 2 * glyph_index)[0] * 2
        ends = struct.unpack_from('>H', data, loca + 2 * glyph_index + 2)[0] * 2
    else:
        starts = struct.unpack_from('>I', data, loca + 4 * glyph_index)[0]
        ends = struct.unpack_from('>I', data, loca + 4 * glyph_index + 4)[0]
    glyf = tables['glyf'][0]
    glyph = data[glyf + starts:glyf + ends]
    if not glyph:
        raise ValueError('Empty glyph')
    contours = struct.unpack_from('>h', glyph, 0)[0]
    if contours < 0:
        raise ValueError('Composite glyphs are not supported')
    if contours == 0:
        return []
    ends = [struct.unpack_from('>H', glyph, 10 + 2 * i)[0] for i in range(contours)]
    total = ends[-1] + 1
    instruction_length = struct.unpack_from('>H', glyph, 10 + 2 * contours)[0]
    offset = 12 + 2 * contours + instruction_length
    flags = []
    while len(flags) < total:
        flag = glyph[offset]
        offset += 1
        flags.append(flag)
        if flag & 8:
            repeats = glyph[offset]
            offset += 1
            flags.extend([flag] * repeats)
    flags = flags[:total]
    xs, x = [], 0
    for flag in flags:
        if flag & 2:
            step = glyph[offset]
            offset += 1
            if not flag & 16:
                step = -step
        elif not flag & 16:
            step = struct.unpack_from('>h', glyph, offset)[0]
            offset += 2
        else:
            step = 0
        x += step
        xs.append(x)
    ys, y = [], 0
    for flag in flags:
        if flag & 4:
            step = glyph[offset]
            offset += 1
            if not flag & 32:
                step = -step
        elif not flag & 32:
            step = struct.unpack_from('>h', glyph, offset)[0]
            offset += 2
        else:
            step = 0
        y += step
        ys.append(y)
    points = [(xs[i], ys[i], bool(flags[i] & 1)) for i in range(total)]
    contours_out, start = [], 0
    for end in ends:
        contours_out.append(points[start:end + 1])
        start = end + 1
    return contours_out


def svg_path(contours, units_per_em):
    """TrueType quadratic contours to an SVG path in flipped screen coordinates."""
    parts = []
    for contour in contours:
        first_on = next((i for i, point in enumerate(contour) if point[2]), None)
        if first_on is None:
            raise ValueError('Contour without an on-curve point')
        sequence = contour[first_on:] + contour[:first_on]
        path = 'M %g %g' % (sequence[0][0], -sequence[0][1])
        index, count = 1, len(sequence)
        while index < count:
            point = sequence[index]
            nxt = sequence[(index + 1) % count]
            if point[2]:
                path += ' L %g %g' % (point[0], -point[1])
                index += 1
            elif nxt[2]:
                path += ' Q %g %g %g %g' % (point[0], -point[1], nxt[0], -nxt[1])
                index += 2
            else:
                middle = ((point[0] + nxt[0]) / 2.0, (point[1] + nxt[1]) / 2.0)
                path += ' Q %g %g %g %g' % (point[0], -point[1], middle[0], -middle[1])
                index += 1
        parts.append(path + ' Z')
    return ' '.join(parts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('font', type=Path)
    parser.add_argument('--record', type=Path, help='Write provenance JSON with the path data')
    args = parser.parse_args()
    data = args.font.read_bytes()
    tables = read_tables(data)
    head = tables['head'][0]
    units_per_em = struct.unpack_from('>H', data, head + 18)[0]
    cmap = tables['cmap'][0]
    subtables = [struct.unpack_from('>HHI', data, cmap + 4 + 8 * i) for i in range(struct.unpack_from('>H', data, cmap + 2)[0])]
    preferred = ((3, 10), (0, 4), (3, 1), (0, 3))
    for platform, encoding in preferred:
        for candidate_platform, candidate_encoding, offset in subtables:
            if (candidate_platform, candidate_encoding) == (platform, encoding):
                chosen = cmap + offset
                break
        if chosen is not None:
            break
    if chosen is None:
        raise SystemExit('No unicode cmap subtable')
    glyph_index = cmap_lookup(data, chosen, GLYPH_CODEPOINT)
    if glyph_index == 0:
        raise SystemExit('U+E900 missing from font')
    contours = glyph_outline(data, tables, glyph_index)
    path = svg_path(contours, units_per_em)
    print(path)
    if args.record:
        record = {
            'schema_version': 1,
            'source': {
                'repository': 'https://github.com/omacom/omarchy',
                'commit': '03ff1eff3812933f7088484533784d2f63eaf19a',
                'path': 'default/fonts/omarchy/omarchy.ttf',
                'sha256': hashlib.sha256(data).hexdigest(),
                'bytes': len(data),
                'license': 'MIT',
            },
            'glyph': {
                'codepoint': 'U+E900',
                'name': 'Omarchy mark',
                'units_per_em': units_per_em,
                'contours': len(contours),
                'svg_path': path,
            },
            'extraction': 'tools/extract_menu_mark.py (stdlib TrueType glyf reader; y flipped; only U+E900 recorded)',
            'limits': 'The binary font is not imported or redistributed; it also contains third-party agent marks that are not extracted.',
        }
        args.record.write_text(json.dumps(record, indent=2) + '\n')


if __name__ == '__main__':
    main()
