"""Calling Wii archive reader/rebuilder. Python 3 standard library only.

Usage: python archive.py unpack INPUT.bin DIRECTORY
       python archive.py pack INPUT.bin DIRECTORY OUTPUT.bin
Unchanged entries retain their exact original compressed bytes.
"""
import json, struct, sys, zlib
from pathlib import Path

def compress_lzss(raw):
    """1024-byte window, 66-byte lookahead; emit the game's method-1 format."""
    history=b'\0'*1024+raw;pos=0;encoded=bytearray()
    while pos<len(raw):
        flagpos=len(encoded);encoded.append(0);flags=0
        for bit in range(8):
            if pos>=len(raw):break
            absolute=pos+1024;maximum=min(66,len(raw)-pos);bestlen=0;bestpos=0
            if maximum>=3:
                prefix=history[absolute:absolute+3];end=absolute+2
                for attempt in range(32):
                    candidate=history.rfind(prefix,absolute-1024,end)
                    if candidate<0:break
                    length=3
                    while length<maximum and history[candidate+length]==history[absolute+length]:length+=1
                    if length>bestlen:bestlen=length;bestpos=candidate
                    if bestlen==maximum:break
                    end=candidate+2
            if bestlen>=3:
                offset=(958+bestpos-1024)&1023
                encoded.extend(bytes([offset&255,((offset>>2)&192)|(bestlen-3)]));pos+=bestlen
            else:flags|=1<<bit;encoded.append(raw[pos]);pos+=1
        encoded[flagpos]=flags
    return bytes(encoded)

def read_archive(data):
    count=struct.unpack_from('>I',data)[0]
    if not 0<count<100000:raise ValueError('Invalid entry count')
    offsets=list(struct.unpack_from('>'+str(count)+'I',data,4))+[len(data)]
    if offsets[0]!=4+count*4 or any(a>=b for a,b in zip(offsets,offsets[1:])):
        raise ValueError('Invalid archive offsets')
    entries=[]
    for start,end in zip(offsets,offsets[1:]):
        block=data[start:end];size,method=struct.unpack_from('>II',block)
        if method==7:
            rawsize,packedsize=struct.unpack_from('>II',block,8)
            if rawsize!=size:raise ValueError('Multichunk zlib entry is not supported yet')
            decoder=zlib.decompressobj();raw=decoder.decompress(block[16:16+packedsize])+decoder.flush()
            if not decoder.eof or decoder.unused_data:raise ValueError('Invalid zlib stream')
        elif method==1:
            ring=bytearray(1024);write=958;raw=bytearray();pos=8
            while len(raw)<size:
                flags=block[pos];pos+=1
                for bit in range(8):
                    if len(raw)>=size:break
                    if flags&(1<<bit):
                        value=block[pos];pos+=1;raw.append(value);ring[write]=value;write=(write+1)&1023
                    else:
                        low,high=block[pos:pos+2];pos+=2
                        offset=low|((high&0xc0)<<2)
                        for i in range((high&63)+3):
                            value=ring[(offset+i)&1023];raw.append(value);ring[write]=value;write=(write+1)&1023
        else:raise ValueError(f'Unknown compression method {method}')
        if len(raw)!=size:raise ValueError('Decompressed size mismatch')
        entries.append((method,bytes(raw),block))
    return entries

def rebuild(entries, replacements):
    blocks=[]
    for i,(method,raw,original) in enumerate(entries):
        new=replacements.get(i,raw)
        if new==raw:block=original
        elif method==7:
            compressed=zlib.compress(new,9)
            block=struct.pack('>IIII',len(new),7,len(new),len(compressed))+compressed
        else:
            stream=compress_lzss(new)
            block=struct.pack('>II',len(new),1)+stream
        if len(block)&1:block+=b'\0'
        blocks.append(block)
    offset=4+len(blocks)*4;header=bytearray(struct.pack('>I',len(blocks)))
    for block in blocks:header.extend(struct.pack('>I',offset));offset+=len(block)
    return bytes(header)+b''.join(blocks)

if __name__=='__main__':
    mode,source,directory=sys.argv[1:4];source=Path(source);directory=Path(directory)
    original=source.read_bytes();entries=read_archive(original)
    if mode=='unpack':
        directory.mkdir(parents=True,exist_ok=True)
        for i,(_,raw,_) in enumerate(entries):(directory/f'{i:02}.raw').write_bytes(raw)
        (directory/'manifest.json').write_text(json.dumps([{'index':i,'compression':m,'size':len(r),'signature':r[:8].hex()} for i,(m,r,_) in enumerate(entries)],indent=2))
        print('Extracted',len(entries),'entries')
    elif mode=='pack':
        output=Path(sys.argv[4])
        if output.resolve()==source.resolve():raise SystemExit('Refusing to overwrite original')
        if output.exists():raise SystemExit('Output already exists')
        replacements={i:(directory/f'{i:02}.raw').read_bytes() for i in range(len(entries)) if (directory/f'{i:02}.raw').exists()}
        packed=rebuild(entries,replacements);check=read_archive(packed)
        assert all(r==replacements.get(i,entries[i][1]) for i,(_,r,_) in enumerate(check))
        output.write_bytes(packed);print('Wrote',output)
    else:raise SystemExit('Use unpack or pack')
