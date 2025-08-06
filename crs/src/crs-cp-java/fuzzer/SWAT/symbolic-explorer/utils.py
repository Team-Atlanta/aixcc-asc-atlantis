#!/usr/bin/env python3

import mutf8

def transform_mutf8_string_to_binstr(s: str) -> str:
    if s == None:
        return s
    ret_str = ''
    temp_array = []
    for c in s:
        v = ord(c)
        if (v >= 0 and v <=127) or (v >= 256):
            if len(temp_array) != 0:
                ret_str += mutf8.decode_modified_utf8(bytes(temp_array))
                temp_array = []
            ret_str += c
        else:
            temp_array.append(v)

    return ret_str

def main():
    a = 'asdf\xc0\x80가나다라'
    print(repr(a))
    print(repr(transform_mutf8_string_to_binstr(a)))

if __name__ == '__main__':
    main()
