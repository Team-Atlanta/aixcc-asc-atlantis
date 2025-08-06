#!/usr/bin/env python3
import struct

INTS = []
BSTR = b'1\x002\x003\x004\x005\x006\x007'
#BSTR = b'A\x00jazze'
#BSTR = b'password\x00A\x00name\x00A\x00'
#BSTR = b'name\x00admin\x00password\x00~\x00'
#BSTR = b'name\x00admin\x00password\x00~'
#BSTR = b'password\x00A\x00name\x00admin\x00'
#BSTR = b'name\x00admin\x00password\x00zzz'
#BSTR = b'name\x00\tor\x00password\x00m'
#BSTR = b'name\x00anme\x00password\x00gggg'
BSTR = b'name\x00admin\x00password\x00ADUTbc\x00'
with open("init.value", "wb") as f:
    for _int in INTS:
        f.write(struct.pack('>I', _int))
    f.write(BSTR)
