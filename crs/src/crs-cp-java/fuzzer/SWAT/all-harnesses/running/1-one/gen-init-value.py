#!/usr/bin/env python3
import struct

INTS = [3]
#INTS = [0, 1]
#INTS = [13, 1]

BSTR = b'1\x000\x000'
#BSTR = b'1\x00:A'
#BSTR = b'x-evil-backdoor'
#BSTR = b'x-evil-backdoor\0breakin the law'

with open("init.value", "wb") as f:
    for _int in INTS:
        f.write(struct.pack('>I', _int))
    f.write(BSTR)
