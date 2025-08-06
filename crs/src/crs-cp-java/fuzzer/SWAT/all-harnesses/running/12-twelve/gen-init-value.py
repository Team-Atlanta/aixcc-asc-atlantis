#!/usr/bin/env python3
import struct

INTS = []
BSTR = b'12345\x0067890'

with open("init.value", "wb") as f:
    for _int in INTS:
        f.write(struct.pack('>I', _int))
    f.write(BSTR)
