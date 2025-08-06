"""
This client.py only uses python built-in libraries.
"""

import json
import time
import argparse
import http.client

WEB_URL = "0.0.0.0"
WEB_PORT = 9505


def send_get_request(path):
    try:
        conn = http.client.HTTPConnection(WEB_URL, WEB_PORT)
        conn.request("GET", f"/{path}")
        resp = conn.getresponse()
        data = resp.read().decode("utf-8")
        return json.loads(data)
    except Exception as e:
        print(f"Error: {e}")
        return None


def send_post_request(path, data):
    params = json.dumps(data)

    headers = {
        "Content-type": "application/json",
        "Accept": "text/plain",
    }

    try:
        conn = http.client.HTTPConnection(WEB_URL, WEB_PORT)
        conn.request("POST", f"/{path}", params, headers)
        resp = conn.getresponse()
        data = resp.read().decode("utf-8")
        return json.loads(data)
    except Exception as e:
        print(f"Error: {e}")
        return None


def get_issootinited(timeout=0):
    timeout = 9999999 if timeout < 0 else timeout
    if timeout == 0:
        return send_get_request("issootinited")

    while timeout > 0:
        resp = send_get_request("issootinited")
        if check_issootinited(resp):
            return resp
        time.sleep(1)
        timeout -= 1


def check_issootinited(resp):
    # expected result: {'getLock': True, 'isSootInited': True}
    if resp is not None and resp["getLock"] and resp["isSootInited"]:
        return True
    return False


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


def test():
    passed = False

    print("------ Testing ------")

    print("Testing GET on /issootinited")
    resp = get_issootinited()
    print(resp)
    if check_issootinited(resp):
        passed = True
        print("GET /isssotinited test success")
    else:
        print("GET /isssotinited test failed")

    print("Testing POST on /gendict")
    resp = post_gendict(
        "PipelineCommandUtilFuzzer",
        "fuzzerTestOneInput",
        "./test/id1/fuzz.dict",
    )
    print(resp)
    if check_gendict(resp):
        passed = True
        print("POST /gendict test success")
    else:
        print("POST /gendict test failed")

    print("Testing POST on /gendict focused")
    resp = post_gendict(
        "PipelineCommandUtilFuzzer",
        "fuzzerTestOneInput",
        "./test/id1/fuzz.dict",
        focused=True,
    )
    print(resp)
    if check_gendict(resp):
        passed = True
        print("POST /gendict focused test success")
    else:
        print("POST /gendict focused test failed")

    print("Testing POST on /rankbranch")
    resp = post_rankbranch("./test/stuck.json", "./test/ranked-branch.json")
    print(resp)
    # expected result: {'getLock': True, 'success': True}
    if check_rankbranch(resp):
        passed = True
        print("POST /rankbranch test success")
    else:
        print("POST /rankbranch test failed")

    print(f"------ Testing {'Success' if passed else 'Failed'} ------")
    if not passed:
        exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Client for interacting with the static analysis server."
    )
    subparsers = parser.add_subparsers(dest="command")

    get_issootinited_parser = subparsers.add_parser(
        "get_issootinited", aliases=["ping"], help="Send GET request to /issootinited"
    )
    get_issootinited_parser.add_argument(
        "--timeout", type=int, default=0, help="Timeout for the request"
    )

    post_gendict_parser = subparsers.add_parser(
        "post_gendict", aliases=["dict"], help="Send POST request to /gendict"
    )
    post_gendict_parser.add_argument(
        "--targetClass", required=True, help="Target class"
    )
    post_gendict_parser.add_argument(
        "--targetMethod", required=True, help="Target method"
    )
    post_gendict_parser.add_argument(
        "--outputDict", required=True, help="Output dictionary"
    )

    post_rankbranch_parser = subparsers.add_parser(
        "post_rankbranch", aliases=["rank"], help="Send POST request to /rankbranch"
    )
    post_rankbranch_parser.add_argument(
        "--stuckBranchFile", required=True, help="Stuck branch file"
    )
    post_rankbranch_parser.add_argument(
        "--rankedBranchFile", required=True, help="Ranked branch file"
    )

    subparsers.add_parser("test", help="Test the functions")

    args = parser.parse_args()

    if args.command in ["get_issootinited", "ping"]:
        resp = get_issootinited(args.timeout)
        print(resp)
        if not check_issootinited(resp):
            exit(1)
    elif args.command in ["post_gendict", "dict"]:
        resp = post_gendict(args.targetClass, args.targetMethod, args.outputDict)
        print(resp)
        if not check_gendict(resp):
            exit(1)
    elif args.command in ["post_rankbranch", "rank"]:
        resp = post_rankbranch(args.stuckBranchFile, args.rankedBranchFile)
        print(resp)
        if not check_rankbranch(resp):
            exit(1)
    elif args.command == "test":
        test()
    else:
        parser.print_help()
        exit(1)


if __name__ == "__main__":
    main()
