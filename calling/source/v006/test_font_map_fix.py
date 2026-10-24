import struct
import unittest
from font_map_fix import intended_mapping, repair_font, runtime_lookup


def fixture():
    data = bytearray(48)
    data[:4] = b'RFNT'
    # New sparse map spans both syllables, hiding the old syllable's map.
    for pairs, first, last, next_ptr in [({0xAC01: 20}, 0xAC00, 0xAC02, 84), ({0xAC00: 10}, 0xAC00, 0xAC00, 0)]:
        payload = struct.pack('>HHHHIH', first, last, 2, 0, next_ptr, len(pairs))
        payload += b''.join(struct.pack('>HH', c, g) for c, g in pairs.items())
        block = bytearray(b'CMAP' + struct.pack('>I', 8 + len(payload)) + payload)
        while len(block) % 4:
            block.append(0)
        struct.pack_into('>I', block, 4, len(block))
        data.extend(block)
    struct.pack_into('>I', data, 40, 56)
    struct.pack_into('>I', data, 8, len(data))
    struct.pack_into('>H', data, 14, 2)
    return bytes(data)


class MapFixTests(unittest.TestCase):
    def test_reproduces_question_mark_and_restores_old_syllable(self):
        old = fixture()
        self.assertEqual(runtime_lookup(old, 0xAC00), 65535)
        self.assertEqual(runtime_lookup(repair_font(old), 0xAC00), 10)

    def test_preserves_new_syllable_and_missing_character(self):
        fixed = repair_font(fixture())
        self.assertEqual(runtime_lookup(fixed, 0xAC01), 20)
        self.assertEqual(runtime_lookup(fixed, 0xAC02), 65535)

    def test_preserves_all_intended_mappings(self):
        old = fixture()
        self.assertEqual(intended_mapping(old), intended_mapping(repair_font(old)))

    def test_repeat_repair_preserves_lookup(self):
        once = repair_font(fixture())
        twice = repair_font(once)
        self.assertEqual(intended_mapping(once), intended_mapping(twice))
        for code, glyph in intended_mapping(once).items():
            self.assertEqual(runtime_lookup(twice, code), glyph)


if __name__ == '__main__':
    unittest.main()
