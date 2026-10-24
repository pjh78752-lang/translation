"""Extend Wii RFNT I4 fonts without changing any existing character mapping."""
import math, struct
from PIL import Image, ImageDraw, ImageFont

def sections(data):
    pos=16;result=[]
    while pos<len(data):
        tag=data[pos:pos+4];size=struct.unpack_from('>I',data,pos+4)[0]
        assert size>=8 and pos+size<=len(data)
        result.append((tag,pos,size));pos+=size
    assert pos==len(data)
    return result

def mappings(data):
    result={};pos=struct.unpack_from('>I',data,0x28)[0]-8;seen=set()
    while pos!=-8:
        assert pos not in seen;seen.add(pos);assert data[pos:pos+4]==b'CMAP'
        first,last,method=struct.unpack_from('>HHH',data,pos+8)
        if method==0:
            start=struct.unpack_from('>H',data,pos+20)[0]
            for c in range(first,last+1):result.setdefault(c,start+c-first)
        elif method==1:
            for n in range(last-first+1):
                glyph=struct.unpack_from('>H',data,pos+20+n*2)[0]
                if glyph!=65535:result.setdefault(first+n,glyph)
        elif method==2:
            count=struct.unpack_from('>H',data,pos+20)[0]
            for n in range(count):
                c,glyph=struct.unpack_from('>HH',data,pos+22+n*4)
                if glyph!=65535:result.setdefault(c,glyph)
        else:raise ValueError('Unknown CMAP method')
        pos=struct.unpack_from('>I',data,pos+16)[0]-8
    return result

def add_hangul(original,characters,fontpath):
    assert original[:4]==b'RFNT' and original[31]==1
    blocks=sections(original);oldmaps=mappings(original)
    chars=sorted({ord(c) for c in characters if ord(c) not in oldmaps})
    assert chars and all(0xac00<=c<=0xd7a3 for c in chars)
    tglp=struct.unpack_from('>I',original,0x20)[0]-8
    assert original[tglp:tglp+4]==b'TGLP'
    cw,ch,baseline,maxwidth=struct.unpack_from('>4B',original,tglp+8)
    sheetsize=struct.unpack_from('>I',original,tglp+12)[0]
    nsheets,fmt,cols,rows,sw,sh=struct.unpack_from('>6H',original,tglp+16)
    assert fmt==0 and sheetsize==sw*sh//2 and sw%8==sh%8==0
    imageoffset=struct.unpack_from('>I',original,tglp+28)[0]
    oldend=tglp+struct.unpack_from('>I',original,tglp+4)[0]
    assert imageoffset+nsheets*sheetsize==oldend
    oldcount=max(struct.unpack_from('>H',original,p+10)[0] for tag,p,s in blocks if tag==b'CWDH')+1
    assert oldcount>max(oldmaps.values())
    capacity=cols*rows
    newnsheets=max(nsheets,math.ceil((oldcount+len(chars))/capacity))
    delta=(newnsheets-nsheets)*sheetsize
    result=bytearray(original[:oldend])+bytearray(delta)+bytearray(original[oldend:])
    struct.pack_into('>I',result,tglp+4,oldend-tglp+delta)
    struct.pack_into('>H',result,tglp+16,newnsheets)
    # Relocate pointers in existing blocks; TGLP's image pointer does not move.
    for tag,pos,size in blocks:
        newpos=pos+delta if pos>=oldend else pos
        pointer_offsets={b'FINF':[16,20,24],b'CWDH':[12],b'CMAP':[16]}.get(tag,[])
        for relative in pointer_offsets:
            old=struct.unpack_from('>I',original,pos+relative)[0]
            struct.pack_into('>I',result,newpos+relative,old+delta if old>=oldend else old)
    font=ImageFont.truetype(fontpath,cw,index=1)
    for n,code in enumerate(chars):
        glyph=oldcount+n;sheet,cell=divmod(glyph,capacity)
        x=(cell%cols)*(cw+1)+1;y=(cell//cols)*(ch+1)+1
        assert x+cw<=sw and y+ch<=sh
        im=Image.new('L',(cw,ch));draw=ImageDraw.Draw(im)
        # The original font's baseline controls placement inside its cell.
        draw.text((0,baseline),chr(code),font=font,anchor='ls',fill=255)
        for py in range(ch):
            for px in range(cw):
                dx,dy=x+px,y+py
                byte=imageoffset+sheet*sheetsize+((dy//8)*(sw//8)+dx//8)*32+(dy%8)*4+(dx%8)//2
                value=(im.getpixel((px,py))+8)//17
                if dx&1:result[byte]=(result[byte]&240)|value
                else:result[byte]=(result[byte]&15)|(value<<4)
    def append_block(tag,payload):
        while len(result)%4:result.append(0)
        pos=len(result);block=bytearray(tag+struct.pack('>I',8+len(payload))+payload)
        while len(block)%4:block.append(0)
        struct.pack_into('>I',block,4,len(block));result.extend(block);return pos
    widthnext=struct.unpack_from('>I',result,0x24)[0]
    payload=struct.pack('>HHI',oldcount,oldcount+len(chars)-1,widthnext)+bytes([0,cw,cw])*len(chars)
    widths=append_block(b'CWDH',payload);struct.pack_into('>I',result,0x24,widths+8)
    # NW4R stops at the first CMAP range containing the code. Prepending a
    # sparse Hangul range hides older syllables even when it lacks their entry.
    # Merge all existing mappings into one sorted, terminal scan map.
    merged=dict(oldmaps)
    merged.update({code:oldcount+n for n,code in enumerate(chars)})
    payload=struct.pack('>HHHHIH',min(merged),max(merged),2,0,0,len(merged))
    payload+=b''.join(struct.pack('>HH',code,glyph) for code,glyph in sorted(merged.items()))
    cmap=append_block(b'CMAP',payload);struct.pack_into('>I',result,0x28,cmap+8)
    struct.pack_into('>I',result,8,len(result))
    struct.pack_into('>H',result,14,len(blocks)+2)
    newmaps=mappings(result)
    assert all(newmaps[k]==v for k,v in oldmaps.items())
    assert all(c in newmaps for c in chars)
    assert len(sections(result))==len(blocks)+2
    return bytes(result),{'glyphs_added':len(chars),'original_glyphs':oldcount,'cell':[cw,ch],'sheets_before':nsheets,'sheets_after':newnsheets}

def render_text(data,text):
    lookup=mappings(data);tglp=struct.unpack_from('>I',data,0x20)[0]-8
    cw,ch=struct.unpack_from('>2B',data,tglp+8)
    sheetsize=struct.unpack_from('>I',data,tglp+12)[0]
    cols,rows,sw,sh=struct.unpack_from('>4H',data,tglp+20)
    imageoffset=struct.unpack_from('>I',data,tglp+28)[0]
    lines=text.split('\n');im=Image.new('RGB',(max(map(len,lines))*cw,len(lines)*(ch+4)),(20,20,20))
    for line_no,line in enumerate(lines):
        for column,c in enumerate(line):
            glyph=lookup[ord(c)];sheet,cell=divmod(glyph,cols*rows)
            sx=(cell%cols)*(cw+1)+1;sy=(cell//cols)*(ch+1)+1
            for y in range(ch):
                for x in range(cw):
                    dx,dy=sx+x,sy+y
                    off=imageoffset+sheet*sheetsize+((dy//8)*(sw//8)+dx//8)*32+(dy%8)*4+(dx%8)//2
                    alpha=(data[off]>>(0 if dx&1 else 4))&15
                    value=20+alpha*235//15
                    im.putpixel((column*cw+x,line_no*(ch+4)+y),(value,)*3)
    return im
