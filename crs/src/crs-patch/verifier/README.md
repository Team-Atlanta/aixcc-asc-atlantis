# AIxCC Team-Atlanta Verifier Script

This is a simple Python script that relays vulnerability-discovery and generated-patch submissions to the [Verifier API](https://github.com/Team-Atlanta/capi/tree/vapi).

Before using this, VAPI must be running, and its hostname (e.g., `http://localhost:8083`) must be configured using the `VAPI_HOSTNAME` environment variable.

## Example usage

```sh
$ export VAPI_HOSTNAME=http://localhost:8083

$ # Submitting a VD:
$ python3 verifier.py submit_vd '--project=Mock CP' --harness=id_1 --pov=../mock-cp/exemplar_only/cpv_1/blobs/sample_solve.bin
ca605d5e-69fa-4307-9bf4-846c50a2bf56

$ # Checking the VD result:
$ python3 verifier.py check_vd --vd-uuid=ca605d5e-69fa-4307-9bf4-846c50a2bf56
pending
$ # ...wait a little bit for VAPI and CAPI to check the submission...
$ python3 verifier.py check_vd --vd-uuid=ca605d5e-69fa-4307-9bf4-846c50a2bf56
accepted

$ # Getting the CPV_UUID:
$ python3 verifier.py check_status
###################################### Vulnerability Discoveries #######################################
VD_UUID                               CP       Harness    Status    CPV_UUID
------------------------------------  -------  ---------  --------  ------------------------------------
ca605d5e-69fa-4307-9bf4-846c50a2bf56  Mock CP  id_1       accepted  9e1232a3-1a2a-4e25-9b30-20285ecae0ae


###### Generated Patches ######
GP_UUID    CPV_UUID    Status
---------  ----------  --------

$ # Submitting a GP:
$ python3 verifier.py submit_gp --patch=../mock-cp/exemplar_only/cpv_1/patches/samples/good_patch.diff --cpv-uuid=9e1232a3-1a2a-4e25-9b30-20285ecae0ae
5706f491-2750-4e8e-b6cd-dcc353487dc6

$ # Checking the GP result:
$ python3 verifier.py check_gp --gp-uuid=5706f491-2750-4e8e-b6cd-dcc353487dc6
pending
$ # ...wait a little bit for VAPI and CAPI to check the submission...
$ python3 verifier.py check_gp --gp-uuid=5706f491-2750-4e8e-b6cd-dcc353487dc6
accepted
```
