"""Build v006 CMAP repair kits from a hash-verified v005 font and kits.

python build_v006.py --font-bin /path/to/v005/font.bin --repository /workspace/translation
Original game inputs are never overwritten or distributed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
import zipfile

from font_map_fix import intended_mapping, map_blocks, repair_font

TOOLS = Path(__file__).resolve().parents[1] / 'v005'
if not TOOLS.is_dir():
    TOOLS = Path(__file__).resolve().parents[1]  # kit's flat legacy source directory
sys.path.insert(0, str(TOOLS))
from archive import read_archive, rebuild
from build_v005 import apply_ips, compose_ips

sha = lambda value: hashlib.sha256(value).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--font-bin', required=True, type=Path)
    parser.add_argument('--repository', required=True, type=Path)
    args = parser.parse_args()
    root = args.repository / 'calling'
    old_font = args.font_bin.read_bytes()
    old_prefix = 'Calling-Korean-v0.0.5/'
    new_prefix = 'Calling-Korean-v0.0.6/'
    with zipfile.ZipFile(root / 'Calling-Korean-Partial-v0.0.5-Installer-Fix.zip') as base:
        manifest = json.loads(base.read(old_prefix + 'manifest.json'))
        assert sha(old_font) == manifest['files']['font.bin']['patched_sha256']
        old_patch = base.read(old_prefix + 'font.bin.ips')
        translations = json.loads(base.read(old_prefix + 'source/korean-v005.json'))
    chars = {ord(c) for text in translations.values() for c in text if 0xAC00 <= ord(c) <= 0xD7A3}
    entries = read_archive(old_font)
    replacements = {}
    report = []
    for i, (_, data, _) in enumerate(entries):
        assert data[:4] == b'RFNT'
        mapping = intended_mapping(data)
        blocks = list(map_blocks(data))
        def engine_lookup(code):
            for first, last, pairs in blocks:
                if first <= code <= last:
                    return pairs.get(code, 65535)
            return 65535
        failed = [c for c, g in mapping.items() if engine_lookup(c) != g]
        fixed = repair_font(data)
        fixed_blocks = list(map_blocks(fixed))
        assert len(fixed_blocks) == 1
        first, last, fixed_map = fixed_blocks[0]
        assert fixed_map == mapping
        # Exhaustive BMP comparison covers mapped and intentionally missing codes.
        for code in range(65536):
            actual = fixed_map.get(code, 65535) if first <= code <= last else 65535
            assert actual == mapping.get(code, 65535)
        assert chars <= mapping.keys()
        # Repair only modifies size, block count and root CMAP pointer in old data.
        restored = bytearray(fixed[:len(data)])
        for start, end in [(8, 12), (14, 16), (40, 44)]:
            restored[start:end] = data[start:end]
        assert bytes(restored) == data
        replacements[i] = fixed
        report.append({'font_index': i, 'mappings': len(mapping), 'hangul_tested': len(chars),
                       'previously_shadowed_mappings': len(failed),
                       'previously_shadowed_hangul': sum(0xAC00 <= c <= 0xD7A3 for c in failed),
                       'bmp_codes_checked': 65536, 'glyphs_and_widths_unchanged': True})
    new_font = rebuild(entries, replacements)
    checked = read_archive(new_font)
    assert all(data == replacements[i] for i, (_, data, _) in enumerate(checked))
    patch = compose_ips(old_patch, old_font, new_font)
    # Verify original-dependent bytes remain equivalent for multiple input fills.
    for fill in [0, 0x55, 0xFF]:
        source = bytes([fill]) * manifest['files']['font.bin']['original_size']
        old_output = apply_ips(source, old_patch)
        new_output = apply_ips(source, patch)
        # Only the tiny original-dependent prefix differs from the verified input;
        # all bytes changed by this repair must be exact under both compositions.
        for pos, (old_byte, fixed_byte) in enumerate(zip(old_font, new_font)):
            if old_byte != fixed_byte:
                assert new_output[pos] == fixed_byte
        assert len(new_output) == len(new_font)
    assert apply_ips(old_font[:manifest['files']['font.bin']['original_size']], patch) == new_font
    validation = {'version': '0.0.6-font-map-fix', 'fonts': report,
                  'old_font_sha256': sha(old_font), 'new_font_sha256': sha(new_font),
                  'patch_sha256': sha(patch), 'archive_roundtrip': True,
                  'in_game_tested': False, 'windows_tested': False,
                  'unchanged_translation_slots': 2017,
                  'lookup_reference': 'https://github.com/doldecomp/ogws/blob/master/src/nw4r/ut/ut_ResFontBase.cpp'}
    note = '''CALLING 0.0.6 한글 물음표 표시 수정\n\n0.0.5에서 새 한글 문자표가 이전 문자표를 가려 대사가 ?로 표시되는 오류를 수정했습니다.\n14개 글꼴의 문자표를 하나로 합쳤으며 번역 내용, 글리프 이미지와 폭은 유지합니다.\n\n새 폴더에 이 ZIP 전체를 푸세요. ISO 도구는 make-iso.cmd를 실행하여 보관한 원본 일본판 SCAJ18 ISO에서 별도 새 ISO를 만드세요. 기존 한글 ISO에 겹쳐 적용하지 마세요.\nWIT 전체 폴더를 유지하고 WIT·입력·출력 경로는 영문을 사용하세요.\nDolphin에서 새 ISO를 새로 부팅하고, 예전 세이브스테이트를 불러오지 마세요. 일반 저장 데이터는 보존하세요.\n\n리소스 패치는 install.cmd에 원본 일본판 리소스 3개를 입력한 뒤 새 0.0.6 XML을 사용합니다.\n\n게임과 같은 첫 범위 일치 검색으로 14개 글꼴 각각 BMP 65,536개 코드와 한글 844자를 검사했습니다. 압축 왕복·IPS 범위·ZIP 무결성을 검사했습니다. 실제 Windows 설치와 원본 ISO 제작, Dolphin 화면은 제작 환경에서 검증하지 못했습니다.\n'''
    for suffix in ['Partial', 'ISO-Kit']:
        src_name = ('Calling-Korean-Partial-v0.0.5-Installer-Fix.zip' if suffix == 'Partial'
                    else 'Calling-Korean-v0.0.5-ISO-Kit-Installer-Fix.zip')
        dst_name = ('Calling-Korean-Partial-v0.0.6-Font-Fix.zip' if suffix == 'Partial'
                    else 'Calling-Korean-v0.0.6-ISO-Kit-Font-Fix.zip')
        dst = root / dst_name
        if dst.exists():
            raise FileExistsError(dst)
        with zipfile.ZipFile(root / src_name) as zin, zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zout:
            for name in zin.namelist():
                relative = name[len(old_prefix):]
                if relative in ['validation.json', 'installer-validation.json', '설치 오류 수정 안내.txt', '사용방법.txt']:
                    continue
                data = zin.read(name)
                relative = relative.replace('v0.0.5', 'v0.0.6')
                if relative == 'font.bin.ips':
                    data = patch
                elif relative == 'source/rfnt.py':
                    data = (TOOLS / 'rfnt.py').read_bytes()
                elif relative == 'manifest.json':
                    meta = json.loads(data)
                    meta['version'] = '0.0.6-font-map-fix'
                    meta['files']['font.bin']['patched_sha256'] = sha(new_font)
                    meta['files']['font.bin']['patched_size'] = len(new_font)
                    meta['in_game_tested'] = False
                    data = json.dumps(meta, ensure_ascii=True, indent=2).replace('v0.0.5', 'v0.0.6').encode()
                elif relative.endswith(('.ps1', '.cmd', '.xml', '.txt')):
                    data = data.replace(b'v0.0.5', b'v0.0.6')
                zout.writestr(new_prefix + relative, data)
            zout.writestr(new_prefix + '사용방법.txt', note.encode('utf-8-sig'))
            zout.writestr(new_prefix + 'validation.json', json.dumps(validation, ensure_ascii=False, indent=2).encode())
            for source in Path(__file__).parent.glob('*.py'):
                zout.writestr(new_prefix + 'source/v006/' + source.name, source.read_bytes())
        with zipfile.ZipFile(dst) as check:
            assert check.testzip() is None
            # All IPS writes respect the Windows installer's fixed allocation.
            for name in check.namelist():
                if not name.endswith('.ips'):
                    continue
                ips = check.read(name)
                target = int.from_bytes(ips[-3:], 'big')
                pos = 5
                while ips[pos:pos + 3] != b'EOF':
                    off = int.from_bytes(ips[pos:pos + 3], 'big')
                    size = int.from_bytes(ips[pos + 3:pos + 5], 'big')
                    assert size and off + size <= target
                    pos += 5 + size
                assert pos + 6 == len(ips)
        print(dst.name, sha(dst.read_bytes()))
    (Path(__file__).parent / 'validation.json').write_text(json.dumps(validation, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
