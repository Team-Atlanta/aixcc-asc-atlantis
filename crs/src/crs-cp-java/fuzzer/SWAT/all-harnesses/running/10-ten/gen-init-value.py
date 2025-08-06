#!/usr/bin/env python3
import struct

INTS = []
#BSTR = b'cmd\x009\x00msg\x00AAAAAA\x00lib\x00secretmessage.so'
#BSTR = b'cmd\x009\x00msg\x00AAAAAA\x00lib\x00A\x00freeload\x00True'
BSTR = b'cmd\x009\x00msg\x00AAAAAA\x00lib\x00..\x00freeload\x00False'

with open("init.value", "wb") as f:
    for _int in INTS:
        f.write(struct.pack('>I', _int))
    f.write(BSTR)
