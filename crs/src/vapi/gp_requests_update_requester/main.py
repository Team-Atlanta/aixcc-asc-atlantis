from __future__ import annotations

import argparse
import datetime
import os
import time

import requests


DEFAULT_INTERVAL = 5.0


def requests_json_safe(response: requests.Response) -> Any:
    """
    Get json data from a requests Response if possible; otherwise, raise
    an exception with the text of the response
    """
    try:
        return response.json()
    except Exception:
        raise ValueError(response.text)


def get_vapi_hostname() -> str:
    if 'VAPI_HOSTNAME' in os.environ:
        return os.environ['VAPI_HOSTNAME']
    else:
        raise RuntimeError('VAPI_HOSTNAME environment variable is missing')


def print_with_ts(*args, **kwargs):
    ts = f'[{datetime.datetime.now().isoformat()}]'
    return print(ts, *args, **kwargs)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments"""
    parser = argparse.ArgumentParser(
        description='Script to periodically request for VAPI to update the set of GP request files')
    parser.add_argument('--interval', type=float, default=DEFAULT_INTERVAL,
        help='how often to send the POST request to VAPI (float, seconds) (default: %(default)s)')

    args = parser.parse_args(argv)

    print_with_ts('Running...')

    while True:
        try:
            requests_json_safe(requests.post(
                f'{get_vapi_hostname()}/update_gp_requests/',
            ))
        except Exception as e:
            print_with_ts(f'WARNING: {e}')

        time.sleep(args.interval)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    args.func(args)


if __name__ == '__main__':
    main()
