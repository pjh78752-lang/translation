"""Build v0.0.5 from verified v0.0.2 or v0.0.4 resources and the v0.0.4 kit.

python build_v005.py --assets /path/to/assets --base-kit /path/to/Calling-Korean-v0.0.4-ISO-Kit.zip --output /path/to/output
Requires Python 3, Pillow and NotoSansCJK-Regular.ttc. Inputs remain unchanged.
"""
from pathlib import Path
import argparse,hashlib,json,re,struct,zipfile,xml.etree.ElementTree as ET
from archive import read_archive,rebuild
from rfnt import mappings,add_hangul,render_text

sha=lambda b:hashlib.sha256(b).hexdigest()

def apply_ips(original,patch):
    assert patch[:5]==b'PATCH';out=bytearray(original);pos=5
    while patch[pos:pos+3]!=b'EOF':
        off=int.from_bytes(patch[pos:pos+3],'big');size=int.from_bytes(patch[pos+3:pos+5],'big');pos+=5
        assert size and off!=0x454f46
        assert pos+size<=len(patch)
        if len(out)<off+size:out.extend(b'\0'*(off+size-len(out)))
        out[off:off+size]=patch[pos:pos+size];pos+=size
    assert len(patch)==pos+6
    size=int.from_bytes(patch[pos+3:],'big')
    return bytes(out[:size]).ljust(size,b'\0')

def normalize_ips(patch):
    """Flatten overlapping writes and remove writes past the declared final size.

    IPS may truncate after applying records, but the Windows installer allocates
    exactly the final size. Keep every record inside that allocation.
    """
    assert patch[:5]==b'PATCH' and patch[-6:-3]==b'EOF'
    target=int.from_bytes(patch[-3:],'big')
    data=bytearray(target);mask=bytearray(target);pos=5
    while patch[pos:pos+3]!=b'EOF':
        offset=int.from_bytes(patch[pos:pos+3],'big')
        size=int.from_bytes(patch[pos+3:pos+5],'big');pos+=5
        assert size and pos+size<=len(patch)-6
        end=min(target,offset+size)
        if offset<end:
            data[offset:end]=patch[pos:pos+end-offset]
            mask[offset:end]=b'\1'*(end-offset)
        pos+=size
    assert len(patch)==pos+6
    out=bytearray(b'PATCH');pos=0
    while pos<target:
        if not mask[pos]:pos+=1;continue
        start=pos;pos+=1
        while pos<target and mask[pos] and pos-start<65535:pos+=1
        assert start!=0x454f46
        out+=start.to_bytes(3,'big')+(pos-start).to_bytes(2,'big')+data[start:pos]
    return bytes(out+b'EOF'+target.to_bytes(3,'big'))

def compose_ips(base_patch,before,after):
    assert base_patch[-6:-3]==b'EOF';out=bytearray(base_patch[:-6]);pos=0
    while pos<len(after):
        if pos<len(before) and before[pos]==after[pos]:pos+=1;continue
        start=pos;pos+=1
        while pos<len(after) and pos-start<65535 and (pos>=len(before) or before[pos]!=after[pos]):pos+=1
        assert start!=0x454f46
        out+=start.to_bytes(3,'big')+(pos-start).to_bytes(2,'big')+after[start:pos]
    out+=b'EOF'+len(after).to_bytes(3,'big')
    out=normalize_ips(out)
    assert apply_ips(before,out)==after
    return out

def lengths(entries):
    raw=entries[3][1];return struct.unpack('>'+str(len(raw)//2)+'H',raw)

def messages(entries):
    ls=lengths(entries);out=[]
    for bank in range(3):
        off=0
        for i in range(bank*1000,min((bank+1)*1000,len(ls))):
            out.append(entries[bank][1][off:off+ls[i]].decode('utf-16-be'));off+=ls[i]
        assert off==len(entries[bank][1])
    return out

def verify_existing_glyph_pixels(before,after,oldmap):
    # Compare packed atlas bytes for every old glyph, without expanding RGB images.
    # Cells have a one-pixel gutter, so boundary nibbles never include a new glyph.
    def geometry(data):
        t=struct.unpack_from('>I',data,0x20)[0]-8
        cw,ch=struct.unpack_from('>2B',data,t+8)
        size=struct.unpack_from('>I',data,t+12)[0]
        cols,rows,sw,sh=struct.unpack_from('>4H',data,t+20)
        off=struct.unpack_from('>I',data,t+28)[0]
        return cw,ch,size,cols,rows,sw,sh,off
    geo=geometry(before);assert geometry(after)==geo
    cw,ch,size,cols,rows,sw,sh,off=geo
    for glyph in set(oldmap.values()):
        sheet,cell=divmod(glyph,cols*rows)
        x0=(cell%cols)*(cw+1)+1;y0=(cell//cols)*(ch+1)+1
        for y in range(y0,y0+ch):
            x=x0
            while x<x0+cw:
                end=min(x0+cw,(x//8+1)*8)
                start=off+sheet*size+((y//8)*(sw//8)+x//8)*32+(y%8)*4+(x%8)//2
                count=((end-1)%8)//2-(x%8)//2+1
                assert before[start:start+count]==after[start:start+count],glyph
                x=end

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets',type=Path,required=True)
    parser.add_argument('--base-kit',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--font',default='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
    args=parser.parse_args();root=Path(__file__).resolve().parent
    out=args.output;out.mkdir(parents=True,exist_ok=True)
    sources={}
    with zipfile.ZipFile(args.base_kit) as base:
        prefix='Calling-Korean-v0.0.4/'
        manifest=json.loads(base.read(prefix+'manifest.json'))
        for name,meta in manifest['files'].items():
            found=list(args.assets.rglob(name));assert len(found)==1,(name,'ambiguous/missing input')
            sources[name]=found[0].read_bytes()
            if sha(sources[name])!=meta['patched_sha256']:
                v002_hashes={'font.bin':'6f2619e6d42d769d8659c685ed1ee8fbee37a18d4cf2f180d2127d848d43a14a','win_mess_jp_jp.bin':'f80483d4fce61b8950de86c74f5413dd7e6e1962ee519f5372789321b67f0db4','SubTitle.bin':'c6539db664bd16d0b34de3e8b6c4267784c9fa27caad528663ea0db43cb0045d'}
                assert sha(sources[name])==v002_hashes[name],(name,'requires v002 or v004 input')
                sources[name]=apply_ips(sources[name],base.read(prefix+name+'.ips'))
            assert sha(sources[name])==meta['patched_sha256'],(name,'v004 baseline hash mismatch')
        original_messages=read_archive(sources['win_mess_jp_jp.bin']);old=messages(original_messages)
        additions={int(k):v for k,v in json.loads((root/'korean-v005-additions.json').read_text()).items()}
        old_translations=json.loads(base.read(prefix+'source/korean-v004.json'))
        assert not set(map(int,old_translations))&set(additions),'Do not overwrite earlier translations'
        new=old.copy()
        for key,value in additions.items():
            assert 0<=key<len(old)
            assert [c for c in old[key] if 0xe000<=ord(c)<=0xf8ff]==[c for c in value if 0xe000<=ord(c)<=0xf8ff]
            assert not re.search('[ぁ-ヿ一-鿿]',value)
            assert re.findall(r'<(?:X|N)>',old[key])==re.findall(r'<(?:X|N)>',value)
            if 1039<=key<=1123:
                blocks=lambda text:[re.sub(r'\s','',v) for v in re.findall('\uf814(.*?)\uf820',text,re.S)]
                assert blocks(old[key])==blocks(value),(key,'phone/puzzle data changed')
            new[key]=value
        assert all(a==b for i,(a,b) in enumerate(zip(old,new)) if i not in additions)
        ls=[len(s.encode('utf-16-be')) for s in new];assert max(ls)<65536
        replacement={i:''.join(new[i*1000:(i+1)*1000]).encode('utf-16-be') for i in range(3)}
        replacement[3]=struct.pack('>'+str(len(ls))+'H',*ls)
        result={'win_mess_jp_jp.bin':rebuild(original_messages,replacement),'SubTitle.bin':sources['SubTitle.bin']}
        assert messages(read_archive(result['win_mess_jp_jp.bin']))==new
        # Verify every unchanged auxiliary archive entry, not only text banks.
        decoded=read_archive(result['win_mess_jp_jp.bin'])
        assert len(decoded)==len(original_messages)
        assert all(decoded[i][1]==original_messages[i][1] for i in range(4,len(decoded)))
        hangul={c for c in ''.join(new) if 0xac00<=ord(c)<=0xd7a3}
        fonts=read_archive(sources['font.bin']);fontdata={};reports=[]
        for i,(_,font,_) in enumerate(fonts):
            oldmap=mappings(font);missing={c for c in hangul if ord(c) not in oldmap}
            if missing:patched,report=add_hangul(font,missing,args.font)
            else:patched,report=font,{'glyphs_added':0}
            newmap=mappings(patched)
            assert all(newmap[k]==v for k,v in oldmap.items())
            assert all(ord(c) in newmap for c in hangul)
            # Compare all old mapped glyph pixels, including pre-existing Hangul.
            verify_existing_glyph_pixels(font,patched,oldmap)
            fontdata[i]=patched;reports.append({'index':i,**report})
            print('Font',i,'added',len(missing),'glyphs; existing glyphs preserved',flush=True)
        result['font.bin']=rebuild(fonts,fontdata)
        assert all(read_archive(result['font.bin'])[i][1]==f for i,f in fontdata.items())
        # All added text must have drawable characters in the dialogue fonts.
        screenshots=[2407,2408,2409,2413]
        for i in [0,2,3]:
            lookup=mappings(fontdata[i])
            for key,value in additions.items():
                assert all(ord(c) in lookup for c in value if c!='\n' and not 0xe000<=ord(c)<=0xf8ff),(i,key,'missing character')
        # Check layout against the widest original line in the active dialogue bank.
        # These are resource previews, not in-game screenshots.
        preview_text='\n\n'.join(new[i] for i in screenshots)
        preview=render_text(fontdata[2],preview_text)
        preview.save(out/'dialogue-previews.png')
        doc_preview=new[425].split('\n\n')[0]+'\n\n'+new[1047]+'\n\n'+new[1046]
        doc_preview=re.sub('[\ue000-\uf8ff]','',doc_preview)
        render_text(fontdata[2],doc_preview).save(out/'document-previews.png')
        patches={}
        for name,data in result.items():
            p=base.read(prefix+name+'.ips')
            patches[name]=compose_ips(p,sources[name],data) if data!=sources[name] else p
            assert apply_ips(sources[name],patches[name])==data
            pos=5
            while patches[name][pos:pos+3]!=b'EOF':
                off=int.from_bytes(patches[name][pos:pos+3],'big');size=int.from_bytes(patches[name][pos+3:pos+5],'big')
                assert size and off+size<=len(data),(name,'installer bounds')
                pos+=5+size
            assert len(patches[name])==pos+6
            # Bytes not written by the old patch retain input dependence exactly.
            for fill in [0,255]:
                surrogate=bytes([fill])*manifest['files'][name]['original_size']
                assert apply_ips(surrogate,patches[name])==apply_ips(apply_ips(surrogate,p),patches[name])
            meta=manifest['files'][name];meta['patched_sha256']=sha(data);meta['patched_size']=len(data)
        merged={**old_translations,**{str(k):v for k,v in additions.items()}}
        manifest.update(version='0.0.5-text-completion',translated_message_entries=len(merged),hangul_syllables=len(hangul),in_game_tested=False,font_validation=reports)
        remaining=[i for i,s in enumerate(new) if re.search('[ぁ-ヿ一-鿿]',s) and s!='欠番']
        preserved=json.loads((root/'preserved-credits.json').read_text())
        assert remaining==[row['id'] for row in preserved]
        assert all(new[row['id']]==row['original'] for row in preserved)
        batches=json.loads((root/'korean-v005-additions.json').read_text())
        report={'total_slots':len(new),'new_slots_since_v002':len(merged)-1027,'new_slots_since_v004':len(batches),'total_translated_slots':len(merged),'preserved_credit_person_names':len(remaining),'untranslated_japanese_gameplay_text_slots':0,'unused_japanese_placeholders':sum(s=='欠番' for s in new),'all_other_slots_preserved':True,'private_control_tokens_preserved':True,'all_old_font_mappings_and_pixels_preserved':True,'all_14_fonts_cover_translation_hangul':True,'all_added_characters_in_dialogue_fonts':True,'screenshot_ids':screenshots,'no_japanese_text_outside_preserved_credit_names':all(516<=i<=726 for i in remaining),'document_phone_puzzle_blocks_preserved':True,'format_placeholders_preserved':True,'composed_ips_checked':True,'ips_records_within_final_size':True,'windows_manifest_cp949_and_utf8_parsed':True,'windows_powershell_tested':False,'actual_original_resource_install_tested':False,'full_game_iso_rebuild_tested':False,'dolphin_in_game_tested':False}
        assert report['no_japanese_text_outside_preserved_credit_names']
        manifest['validation']=report
        metadata=json.dumps(manifest,ensure_ascii=True,indent=2).encode('ascii')
        assert json.loads(metadata.decode('cp949'))==json.loads(metadata.decode('utf-8'))
        (out/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
        (out/'remaining-japanese-ids.json').write_text(json.dumps(remaining))
        (out/'manifest.json').write_bytes(metadata)
        notes=f'''CALLING 한국어 텍스트 확장 0.0.5\n\n전체 {len(new)}개 슬롯 중 {len(merged)}개 번역. 0.0.4에서 {len(batches)}개 추가.\n이번에는 나머지 수집 문서, 일기, 취재 노트, 인물 소개, 영상 제목, 시스템 안내, 제작진 직책/회사명/곡명을 번역했습니다.\n제공된 텍스트 리소스에는 제작진 실명 {len(remaining)}개와 미사용 결번을 제외한 일본어 문장이 남지 않습니다. 제작진 실명은 읽는 법을 임의로 추정하지 않고 원문 표기를 보존합니다.\n이미지 번역 25개는 유지합니다. 다른 이미지 리소스와 게임 전체 화면의 완역은 확인하지 못했습니다.\n\n새 폴더에 전체 압축을 풀어 make-iso.cmd를 실행하세요. WIT 전체 폴더의 wit.exe, 원본 일본판 SCAJ18 ISO, 새 ISO 저장 위치 순으로 선택하세요.\n구형 WIT의 한글 경로 문제를 피하려면 원본을 E:\\Calling\\original.iso 같은 영문 경로에 두세요. WIT와 출력 경로도 영문을 사용하세요.\n기존 한글 ISO에 겹쳐 적용하지 마세요. 원본 ISO는 보존됩니다.\n\ninstall.cmd는 원본 리소스 3개를 입력받습니다. 제작 소스 build_v005.py는 0.0.4 ISO 도구 ZIP과 0.0.2 또는 0.0.4 리소스 3개를 입력받고 해시를 확인합니다.\nWindows JSON 인코딩 수정은 유지합니다.\n대사 슬롯, 전화번호/퍼즐 숫자 블록, 제어 문자, 형식 지정자, 기존 모든 글리프 픽셀/매핑, 새 한글 지원, 압축 왕복과 IPS 합성을 검사했습니다.\n제작 환경에는 전체 원본 ISO와 Windows/Dolphin이 없어 실제 ISO 제작, Windows 실행, 게임 내 줄바꿈과 배치는 검증하지 못했습니다. 미리보기는 리소스 렌더링입니다.\n'''
        for iso in [False,True]:
            target=out/('Calling-Korean-v0.0.5-ISO-Kit.zip' if iso else 'Calling-Korean-Partial-v0.0.5.zip')
            with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as bundle:
                prefix4='Calling-Korean-v0.0.5/'
                for info in base.infolist():
                    rel=info.filename.split('/',1)[1]
                    if rel.startswith('source/') or rel in ['validation.json','remaining-japanese-ids.json','previews/dialogue-previews.png','previews/document-previews.png']:continue
                    if not iso and rel in ['make-iso.cmd','make-iso.ps1','ISO 만들기 사용방법.txt']:continue
                    data=base.read(info.filename)
                    if rel=='manifest.json':data=metadata
                    elif rel.endswith('.bin.ips'):data=patches[rel[:-4]]
                    elif rel=='사용방법.txt' or rel=='ISO 만들기 사용방법.txt':data=notes.encode('utf-8-sig')
                    elif rel.endswith(('.ps1','.cmd','.xml')):
                        s=data.decode('utf-8-sig').replace('0.0.4','0.0.5').replace('v004','v005').replace('1663',str(len(merged)))
                        if rel.endswith('.ps1'):
                            s=s.replace('-Raw | ConvertFrom-Json','-Raw -Encoding UTF8 | ConvertFrom-Json')
                        if rel=='make-iso.ps1':
                            s=s.replace('This packages the expanded partial v0.0.5 translation.','This packages the expanded partial v0.0.5 translation.')
                        data=s.encode('utf-8-sig' if rel.endswith('.ps1') else 'utf-8')
                    rel=rel.replace('0.0.4','0.0.5');bundle.writestr(prefix4+rel,data)
                for n in ['build_v005.py','archive.py','rfnt.py','korean-v005-additions.json','preserved-credits.json','test_ips_bounds.py']:
                    bundle.writestr(prefix4+'source/'+n,(root/n).read_bytes())
                bundle.writestr(prefix4+'source/korean-v005.json',json.dumps(merged,ensure_ascii=False,indent=2).encode())
                for n in ['validation.json','remaining-japanese-ids.json']:
                    bundle.writestr(prefix4+n,(out/n).read_bytes())
                bundle.writestr(prefix4+'previews/dialogue-previews.png',(out/'dialogue-previews.png').read_bytes())
                bundle.writestr(prefix4+'previews/document-previews.png',(out/'document-previews.png').read_bytes())
            with zipfile.ZipFile(target) as check:
                assert check.testzip() is None
                xml=ET.fromstring(check.read('Calling-Korean-v0.0.5/Calling-Korean-v0.0.5.xml'))
                assert all('calling-ko-v005/' in e.attrib['external'] for e in xml.findall('.//file'))
                for name in result:assert apply_ips(sources[name],check.read(prefix4+name+'.ips'))==result[name]
            print('Wrote',target,sha(target.read_bytes()),flush=True)
        print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':main()
