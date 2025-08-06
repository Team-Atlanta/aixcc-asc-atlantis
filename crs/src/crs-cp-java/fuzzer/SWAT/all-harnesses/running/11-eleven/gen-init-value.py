#!/usr/bin/env python3
import struct

INTS = []
BSTR = b'1\x002\x003\x004\x005\x006\x007'

with open("init.value", "wb") as f:
    for _int in INTS:
        f.write(struct.pack('>I', _int))
    f.write(BSTR)
