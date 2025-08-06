#!/usr/bin/env python3
import struct

INTS = []
BSTR = b'http://a.com'
#BSTR = b'A\x00jazze'

with open("init.value", "wb") as f:
    for _int in INTS:
        f.write(struct.pack('>I', _int))
    f.write(BSTR)
