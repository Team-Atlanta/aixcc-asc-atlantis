from __future__ import annotations

import argparse
from base64 import b64encode
import os
from pathlib import Path
import re
import sys
import traceback
from typing import Any

import requests
from tabulate import tabulate


VAPI_USERNAME = '00000000-0000-0000-0000-000000000000'
VAPI_PASSWORD = 'secret'

DEFAULT_COMMIT = '0000000000000000000000000000000000000000'
DEFAULT_SANITIZER = 'id_1'

SHA1_HASH_REGEX = re.compile('[0-9a-fA-F]{40}', flags=re.IGNORECASE)


def eprint(*args, **kwargs) -> None:
    print(*args, file=sys.stderr, **kwargs)


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


def get_commit_hints_from_file(path: Path) -> list[str]:
    commit_hints = []
    try:  # just in case the file is somehow invalid (e.g., not UTF-8)
        with path.open('r', encoding='utf-8') as f:
            for line in f:
                for match in SHA1_HASH_REGEX.finditer(line):
                    commit_hints.append(match[0])
    except Exception:
        eprint("WARNING: couldn't read commit hints file:")
        eprint(traceback.format_exc())

    return commit_hints


def main_precompile(args: argparse.Namespace) -> None:
    body = {'cp_name': args.project}

    if args.commit_hints_file:
        body['commit_hints'] = get_commit_hints_from_file(args.commit_hints_file)

    result = requests_json_safe(requests.post(
        f'{get_vapi_hostname()}/precompile/',
        json=body,
        auth=(VAPI_USERNAME, VAPI_PASSWORD),
    ))

    if result.get('status', '') != 'ok':
        raise RuntimeError(f'Unexpected response from VAPI: {result}')
    else:
        print(result['status'])


def main_submit_vd(args: argparse.Namespace) -> None:
    body = {
        'cp_name': args.project,
        'pou': {
            'commit_sha1': args.commit.lower(),
            'sanitizer': args.sanitizer,
        },
        'pov': {
            'harness': args.harness,
            'data': b64encode(args.pov.read_bytes()).decode('ascii'),
        },
    }

    if args.commit_hints_file:
        body['pou_commit_hints'] = get_commit_hints_from_file(args.commit_hints_file)

    result = requests_json_safe(requests.post(
        f'{get_vapi_hostname()}/submission/vds/',
        json=body,
        auth=(VAPI_USERNAME, VAPI_PASSWORD),
    ))

    if result.get('status', '') != 'pending' or 'vd_uuid' not in result:
        raise RuntimeError(f'Unexpected response from VAPI: {result}')
    else:
        print(result['vd_uuid'])


def main_check_vd(args: argparse.Namespace) -> None:
    result = requests_json_safe(requests.get(
        f'{get_vapi_hostname()}/submission/vds/{args.vd_uuid}',
        auth=(VAPI_USERNAME, VAPI_PASSWORD),
    ))

    status = result.get('status', '')
    fail_reason = result.get('fail_reason', 'unknown')

    if status in {'accepted', 'pending'}:
        print(status)
    elif status == 'rejected':
        print(f'{status} | {fail_reason}')
    else:
        raise RuntimeError(f'Unexpected response from VAPI: {result}')


def main_submit_gp(args: argparse.Namespace) -> None:
    result = requests_json_safe(requests.post(
        f'{get_vapi_hostname()}/submission/gp/',
        json={
            'cpv_uuid': args.cpv_uuid,
            'data': b64encode(args.patch.read_bytes()).decode('ascii'),
        },
        auth=(VAPI_USERNAME, VAPI_PASSWORD),
    ))

    if result.get('status', '') != 'pending' or 'gp_uuid' not in result:
        raise RuntimeError(f'Unexpected response from VAPI: {result}')
    else:
        print(result['gp_uuid'])


def main_check_gp(args: argparse.Namespace) -> None:
    result = requests_json_safe(requests.get(
        f'{get_vapi_hostname()}/submission/gp/{args.gp_uuid}',
        auth=(VAPI_USERNAME, VAPI_PASSWORD),
    ))

    status = result.get('status', '')

    if status in {'accepted', 'pending', 'rejected'}:
        print(status)
    else:
        raise RuntimeError(f'Unexpected response from VAPI: {result}')


def main_check_status(args: argparse.Namespace) -> None:
    result = requests_json_safe(requests.get(
        f'{get_vapi_hostname()}/status/',
        auth=(VAPI_USERNAME, VAPI_PASSWORD),
    ))

    vd_cols = [
        # key, header name, whether it's only printed with --full
        ('cp_name', 'CP', False),
        ('commit_sha1', 'Bug-Inducing Commit', True),
        ('harness', 'Harness', False),
        ('sanitizer', 'Sanitizer', True),
        ('status', 'Status', False),
        ('cpv_uuid', 'CPV_UUID', False),
    ]

    vd_table_rows = []
    for submission_key, submission in result['vd_submissions'].items():
        submission_row = [submission_key]
        for col_key, col_header, only_in_full in vd_cols:
            if only_in_full and not args.full: continue
            submission_row.append(submission[col_key])
        vd_table_rows.append(submission_row)

    vd_table_headers = ['VD_UUID']
    for col_key, col_header, only_in_full in vd_cols:
        if only_in_full and not args.full: continue
        vd_table_headers.append(col_header)

    vd_table_ascii = tabulate(vd_table_rows, headers=vd_table_headers)
    width = max(len(line) for line in vd_table_ascii.splitlines())
    header = ' Vulnerability Discoveries '.center(width, '#')

    print(header)
    print(vd_table_ascii)

    print('\n')

    gp_table = [
        [key, row['cpv_uuid'], row['status']]
        for key, row in result['gp_submissions'].items()]
    gp_table_ascii = tabulate(gp_table, headers=['GP_UUID', 'CPV_UUID', 'Status'])
    width = max(len(line) for line in gp_table_ascii.splitlines())
    header = ' Generated Patches '.center(width, '#')

    print(header)
    print(gp_table_ascii)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments"""
    parser = argparse.ArgumentParser(
        description='Script to submit vulnerability-discovery and'
        'generated-patch submissions to the verifier API proxy')

    subparsers = parser.add_subparsers(title='commands', required=True)

    parser_precompile = subparsers.add_parser('precompile',
        help='request the verifier API to begin pre-compiling CP commits')
    parser_precompile.set_defaults(func=main_precompile)
    parser_precompile.add_argument('--project', required=True,
        help='challenge project name (i.e., "cp_name" field from the CP\'s project.yaml)')
    parser_precompile.add_argument('--commit-hints-file', type=Path,
        help='same as --commit-hints-file from the "submit_vd" command')

    parser_vd = subparsers.add_parser('submit_vd',
        help='submit a vulnerability discovery to the verifier API'
        ' (which in turn submits it to the competition API if appropriate)')
    parser_vd.set_defaults(func=main_submit_vd)
    parser_vd.add_argument('--project', required=True,
        help='challenge project name (i.e., "cp_name" field from the CP\'s project.yaml)')
    parser_vd.add_argument('--harness', required=True,
        help='harness name ("harnesses" key from project.yaml, e.g., "id_1")')
    parser_vd.add_argument('--pov', type=Path, required=True,
        help='path to the proof-of-vulnerability blob, aka the input data to the harness')
    parser_vd.add_argument('--commit', default=DEFAULT_COMMIT,
        help='commit hash. Ignored by VAPI.')
    parser_vd.add_argument('--sanitizer', default=DEFAULT_SANITIZER,
        help='name of sanitizer expected to fire ("sanitizers" key from project.yaml, e.g., "id_1"). Ignored by VAPI.')
    parser_vd.add_argument('--commit-hints-file', type=Path,
        help='a UTF-8-encoded text file containing PoU commit hints.'
        ' Any other text in the file is ignored -- 40-character-long commit hashes are simply found and extracted using a regex.'
        ' In particular, the .json output file from commit-analyzer (actually CSV format) works here.')

    parser_vd_check = subparsers.add_parser('check_vd',
        help='check the status of a VD_UUID ("pending", "accepted: <CPV_UUID>", or "rejected")')
    parser_vd_check.set_defaults(func=main_check_vd)
    parser_vd_check.add_argument('--vd-uuid', required=True,
        help='the VD_UUID to check')

    parser_gp = subparsers.add_parser('submit_gp',
        help='submit a generated patch to the verifier API'
        ' (which in turn submits it to the competition API if appropriate)')
    parser_gp.set_defaults(func=main_submit_gp)
    parser_gp.add_argument('--cpv-uuid', required=True,
        help='the CPV_UUID this patch is for')
    parser_gp.add_argument('--patch', type=Path, required=True,
        help='path to the patch file')

    parser_gp_check = subparsers.add_parser('check_gp',
        help='check the status of a GP_UUID ("pending", "accepted", or "rejected")')
    parser_gp_check.set_defaults(func=main_check_gp)
    parser_gp_check.add_argument('--gp-uuid', required=True,
        help='the GP_UUID to check')

    parser_status = subparsers.add_parser('check_status',
        help='print a summary of the overall CAPI/VAPI status (uses a custom VAPI endpoint)')
    parser_status.set_defaults(func=main_check_status)
    parser_status.add_argument('--full', action='store_true',
        help='print *all* status-result output (table may be very wide)')

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    args.func(args)


if __name__ == '__main__':
    main()
