# GP-Requests Update Requester

This is a very simple Python script that periodically POSTS to VAPI's `/update_gp_requests/` endpoint. This triggers it to check for newly accepted VD submissions, and post new GP-request TOML files for them.

Before using this, VAPI must be running, and its hostname (e.g., `http://localhost:8083`) must be configured using the `VAPI_HOSTNAME` environment variable.

You can use the `--interval` argument to control how frequently the endpoint is requested.
