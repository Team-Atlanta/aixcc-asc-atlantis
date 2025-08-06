#!/usr/bin/env python3

from pathlib import Path
import glob
import os

class ConcolicHelper(object):
    def __init__(self):
        pass

    def get_harness_src_path(self, class_name):
        p = os.environ['JAVA_CRS_SRC']
        path = Path(p)
        new_path = (((path /'fuzzer') / 'SWAT') / 'all-harnesses') / 'harnesses'
        g = list(glob.glob(f"{new_path}/*.java"))
        for entry in g:
            if class_name in entry:
                return entry
        return None
