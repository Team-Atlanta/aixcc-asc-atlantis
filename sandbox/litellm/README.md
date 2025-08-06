# README for LiteLLM in CRS-Sandbox

## Verify rate-limits
To verify that rate limits for your current config of the LiteLLM proxy are correct, run:
`k6 run rate-limit-test.js -e LITELLM_KEY=sk-1234 --http-debug=full -i 10`

This requires installing the Grafana k6 package within your development environment.
The script hits the fake-openai-endpoint-rate-limits model deployment, which is a built-in
pseudo-endpoint that goes nowhere. If you exceed the rpm/tpm limits for this deployment,
you should see:
`{"error":{"message":"litellm.RateLimitError: Deployment over defined rpm limit=2. current usage=2","type":null,"param":null,"code":429}}`
followed by:
`{"error":{"message":"No deployments available for selected model, Try again in 60 seconds. Passed model=fake-openai-endpoint-rate-limits. pre-call-checks=False, allowed_model_region=n/a","type":"None","param":"None","code":429}}`
for subsequent attempts.

## Max Parallel Requests Errors

There is a known bug in LiteLLM where user or key-level rate-limits will trigger a
"max parallel requests reached" error instead of a more descriptive message. This
is [being tracked by LiteLLM](https://github.com/BerriAI/litellm/issues/4314)
Right now, please assume that a max-parallel-requests limit is a user-level TPM or RPM
violation and retry in 60s.