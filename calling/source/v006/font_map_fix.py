"""Repair overlapping RFNT CMAPs without changing glyph images or widths.

NW4R stops at the first CMAP whose inclusive range contains the character.
A missing character in that map never falls through to a later CMAP.
Reference: doldecomp/ogws src/nw4r/ut/ut_ResFontBase.cpp, FindGlyphIndex.
"""
import struct


def map_blocks(data):
    pos = struct.unpack_from('>I', data, 0x28)[0] - 8
    seen = set()
    while pos != -8:
        if pos in seen or data[pos:pos + 4] != b'CMAP':
            raise ValueError('Invalid or cyclic CMAP chain')
        seen.add(pos)
        first, last, method = struct.unpack_from('>HHH', data, pos + 8)
        pairs = {}
        if method == 0:
            start = struct.unpack_from('>H', data, pos + 20)[0]
            pairs = {c: start + c - first for c in range(first, last + 1)}
        elif method == 1:
            for c in range(first, last + 1):
                glyph = struct.unpack_from('>H', data, pos + 20 + 2 * (c - first))[0]
                if glyph != 65535:
                    pairs[c] = glyph
        elif method == 2:
            count = struct.unpack_from('>H', data, pos + 20)[0]
            for n in range(count):
                code, glyph = struct.unpack_from('>HH', data, pos + 22 + 4 * n)
                if glyph != 65535:
                    pairs[code] = glyph
        else:
            raise ValueError('Unsupported CMAP method')
        yield first, last, pairs
        pos = struct.unpack_from('>I', data, pos + 16)[0] - 8


def runtime_lookup(data, code):
    """Match NW4R's first-containing-range lookup, including failed searches."""
    for first, last, pairs in map_blocks(data):
        if first <= code <= last:
            return pairs.get(code, 65535)
    return 65535


def intended_mapping(data):
    result = {}
    for first, last, pairs in map_blocks(data):
        for code, glyph in pairs.items():
            if not first <= code <= last:
                raise ValueError('CMAP entry outside declared range')
            result.setdefault(code, glyph)
    return result


def repair_font(data):
    mapping = intended_mapping(data)
    if not mapping or len(mapping) > 65535:
        raise ValueError('Invalid mapping size')
    # One sorted scan map has no overlapping range and preserves every mapping.
    result = bytearray(data)
    while len(result) % 4:
        result.append(0)
    pos = len(result)
    payload = struct.pack('>HHHHIH', min(mapping), max(mapping), 2, 0, 0, len(mapping))
    payload += b''.join(struct.pack('>HH', code, glyph) for code, glyph in sorted(mapping.items()))
    block = bytearray(b'CMAP' + struct.pack('>I', 8 + len(payload)) + payload)
    while len(block) % 4:
        block.append(0)
    struct.pack_into('>I', block, 4, len(block))
    result.extend(block)
    struct.pack_into('>I', result, 0x28, pos + 8)
    struct.pack_into('>I', result, 8, len(result))
    struct.pack_into('>H', result, 14, struct.unpack_from('>H', data, 14)[0] + 1)
    return bytes(result)
