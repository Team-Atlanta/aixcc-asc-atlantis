import os
import sys
from testbench import TestBench

DOC_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.realpath(os.path.join(DOC_DIR, "..", ".."))
TEST_DIR = os.path.realpath(os.path.join(ROOT_DIR, "tests"))
sys.path.append(ROOT_DIR)
sys.path.append(TEST_DIR)

if os.getenv("CP_DIR") is None:
    raise Exception("CP_DIR is not set")

if os.getenv("AIXCC_LITELLM_HOSTNAME") is None:
    raise Exception("AIXCC_LITELLM_HOSTNAME is not set")

if os.getenv("LITELLM_KEY") is None:
    raise Exception("LITELLM_KEY is not set")

CP_DIR = os.getenv("CP_DIR")
CP_DIR = os.path.realpath(CP_DIR)

BASE_URL = os.getenv("AIXCC_LITELLM_HOSTNAME")
API_KEY = os.getenv("LITELLM_KEY")

import harness.llm.llm_proxy as llm_proxy
llm_proxy.config.base_url = BASE_URL
llm_proxy.config.api_key = API_KEY

os.chdir(TEST_DIR)
TMP_DIR = os.path.realpath("./.tmp")


def build_test(builder, java_file):
    try:
        builder.javac(java_file)
        print(f'Success to compile: {java_file}')
        return True
    except:
        print(f'Failed to compile: {java_file}')
        return False
