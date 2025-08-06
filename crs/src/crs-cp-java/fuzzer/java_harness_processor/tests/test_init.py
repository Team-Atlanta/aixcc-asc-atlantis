import os
import sys

CP_DIR = os.environ.get("CP_DIR")
COMPILE_TEST = os.environ.get("COMPILE_TEST")

DOC_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.realpath(os.path.join(DOC_DIR, ".."))
sys.path.append(ROOT_DIR)