#!/usr/bin/env python3
import struct

INTS = [2, 1, 1, 5, 6, 0, 8, 9]
BSTR = b''
#BSTR = b'12345\x0067890'

with open("init.value", "wb") as f:
    for _int in INTS:
        f.write(struct.pack('>I', _int))
    f.write(BSTR)
