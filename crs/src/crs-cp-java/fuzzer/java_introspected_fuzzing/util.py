import os
import json
import time
import http.client

from log import info, error

import constants


def send_get_request(path):
    try:
        conn = http.client.HTTPConnection(
            constants.STATIC_ANALYZER_WEB_URL, constants.STATIC_ANALYZER_WEB_PORT
        )
        conn.request("GET", f"/{path}")
        resp = conn.getresponse()
        data = resp.read().decode("utf-8")
        return json.loads(data)
    except Exception as e:
        error(f"Error: {e}")
        return None


def send_post_request(path, data):
    params = json.dumps(data)

    headers = {
        "Content-type": "application/json",
        "Accept": "text/plain",
    }

    try:
        conn = http.client.HTTPConnection(
            constants.STATIC_ANALYZER_WEB_URL, constants.STATIC_ANALYZER_WEB_PORT
        )
        conn.request("POST", f"/{path}", params, headers)
        resp = conn.getresponse()
        data = resp.read().decode("utf-8")
        return json.loads(data)
    except Exception as e:
        error(f"Error: {e}")
        return None


def get_issootinited():
    return send_get_request("issootinited")


def check_issootinited(resp):
    # expected result: {'getLock': True, 'isSootInited': True}
    if resp is not None and resp["getLock"] and resp["isSootInited"]:
        return True
    return False


def wait_until_service_alive():
    while True:
        ret = check_issootinited(get_issootinited())
        if ret:
            info("Soot server is inited.")
            break
        info("Soot server has not been inited, wait a while.")
        time.sleep(10)


def post_gendict(targetClass, targetMethod, outputDict, focused=False):
    if focused:
        return send_post_request(
            "gendict",
            {
                "targetClass": targetClass,
                "targetMethod": targetMethod,
                "outputDict": outputDict,
                "focused": "true",
            },
        )
    else:
        return send_post_request(
            "gendict",
            {
                "targetClass": targetClass,
                "targetMethod": targetMethod,
                "outputDict": outputDict,
            },
        )


def check_gendict(resp):
    # expected result: {'getLock': True, 'success': True}
    if resp is not None and resp["getLock"] and resp["success"]:
        return True
    return False


def post_rankbranch(stuckBranchFile, rankedBranchFile):
    return send_post_request(
        "rankbranch",
        {
            "stuckBranchFile": stuckBranchFile,
            "rankedBranchFile": rankedBranchFile,
        },
    )


def check_rankbranch(resp):
    # expected result: {'getLock': True, 'success': True}
    if resp is not None and resp["getLock"] and resp["success"]:
        return True
    return False


def is_get_lock_failed(resp):
    # expected result: {'getLock': False, 'success': False}
    if resp is not None and not resp["getLock"]:
        return True
    return False


def query_until_get_lock(f, tries=20):
    count = 0
    while count < tries:
        resp = f()
        if resp is not None and resp["getLock"]:
            info("Get lock success.")
            return resp
        info(f"Get lock failed with resp {resp}, retry {count}.")
        time.sleep(1)
        count += 1
    info("Get lock failed, give up.")
    return None

def escape_non_ascii(s):
    escaped_str = []
    for char in s:
        c = ord(char)
        if 32 <= c <= 126:
            escaped_str.append(char)
        elif c == 92:
            escaped_str.append("\\\\")
        else:
            escaped_str.append('\\x{:02x}'.format(c))
    return ''.join(escaped_str)
