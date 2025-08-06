# Verifier API (VAPI)

This is a modified version of the Competition API, based on the [team-atlanta branch](https://github.com/Team-Atlanta/capi/tree/team-atlanta), with the following key changes:

- Requests are generally proxied to/from the actual Competition API (CAPI).
- However, functionality tests and duplicate-submission testing are preserved, to avoid losing points by sending incorrect submissions to CAPI.
- [Caches for challenge-project builds and PoV test runs have been added](competition_api/wrapped_cp_workspace.py), to avoid wasting time by repeatedly re-building and re-testing challenge projects at the same commits.
- Vulnerability discoveries (VD):
    - VD_UUIDs for interacting with VAPI _do not_ directly match those known to CAPI.
        - This is because VAPI needs to assign UUIDs immediately, before its own VD/GP testing is complete, which is before it submits (or chooses not to submit) to CAPI.
        - Note that CPV_UUIDs _do_ match CAPI's.
    - Proof-of-understanding fields (bug-inducing commit, triggered sanitizer) are ignored, and filled in automatically.
        - The fields do still need to be present, though. Recommended placeholder values: `0000000000000000000000000000000000000000`, `id_1`
- Generated patches (GPs):
    - As with VD_UUIDs, VAPI's GP_UUIDs don't match CAPI's.
    - Per the contest rules, CAPI "accepts" any GP that merely builds, and doesn't provide any feedback on whether or not it actually fixes the vulnerability. VAPI is more transparent, and does observably reject GPs that don't fix the vulnerabilities.

## Prerequisites and configuration

1. See the readme from the [team-atlanta branch](https://github.com/Team-Atlanta/capi/tree/team-atlanta) for most of the setup steps.
2. CAPI's hostname (e.g., `http://host.docker.internal:8082`) must be configured using the `AIXCC_CAPI_HOSTNAME` environment variable.
    - `localhost` and `127.0.0.1` would resolve to the container itself, whereas `host.docker.internal` resolves to the host machine, which is probably where you're running CAPI during development/testing. Some Docker environments don't provide that hostname, though -- [see here for some alternatives that may work for you](https://stackoverflow.com/q/48546124) (I've had success with `172.17.0.1`).
3. Login info for CAPI should be configured in compose.yaml (`AIXCC_CAPI_USERNAME` and `AIXCC_CAPI_PASSWORD` environment variables). The defaults are fine for development/testing.
4. Default port numbers changed (these are chosen to match the values in [the CRS sandbox](https://github.com/Team-Atlanta/asc-crs-team-atlanta/blob/main/sandbox/compose.yaml), plus 10000):
    - DinD: 2376 -> 12375
    - Postgres: *(N/A, replaced with SQLite)*
    - VAPI: 8082 -> 18080

## Additional options

These are environment variables defined in [compose.yaml](compose.yaml).

Only options specific to VAPI are listed here; the rest are the same as in [upstream CAPI](https://github.com/Team-Atlanta/capi/tree/main) or [the `team-atlanta` branch](https://github.com/Team-Atlanta/capi/tree/team-atlanta).

- `VAPI_CAPI_USERNAME`, `VAPI_CAPI_PASSWORD` (defaults: `00000000-0000-0000-0000-000000000000`, `secret`): credentials to use when connecting to CAPI.
    - In the CRS environment, VAPI connects to iAPI rather than CAPI, which does not require authentication, so these values shouldn't matter.
- `VAPI_TEST_GPS_BUILD` (default: `false`): if set to `true`, VAPI will test whether Generated Patches can be applied and built.
    - If `VAPI_TEST_GPS_WITH_POV` and/or `VAPI_TEST_GPS_FUNCTIONAL` are enabled (see below), this setting is ignored, since patches need to be built in order to run those tests.
- `VAPI_TEST_GPS_WITH_POV` (default: `false`): if set to `true`, VAPI will test Generated Patches against the PoV blob.
- `VAPI_TEST_GPS_FUNCTIONAL` (default: `false`): if set to `true`, VAPI will run functional tests on Generated Patches.

## TODO

- Periodically check for submissions in limbo (e.g., tried to submit while CAPI was down), and resolve them
- Smarter handling of submissions that are potential duplicates of ones that are still pending
