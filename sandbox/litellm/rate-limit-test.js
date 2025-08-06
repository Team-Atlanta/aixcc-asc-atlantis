import http from 'k6/http'
import { group, check } from 'k6'

const BASE_URL = 'http://localhost:8081'
// Global variables should be initialized.
const authorization = `Bearer ${__ENV.LITELLM_KEY}` // eslint-disable-line
const user = "crs-1";

export default function () {
  group('/chat/completions', () => {
    let model = 'fake-openai-endpoint-rate-limits';
        // Request No. 1: chat_completion_chat_completions_post
        {
            let url = BASE_URL + `/chat/completions?model=${model}`;
            let body = {"user": `${user}`, "messages": [{"role": "user", "content": "What is 2 + 2?"}]};
            let params = {headers: {"Content-Type": "application/json", "Accept": "application/json", "Authorization": `${authorization}`}};
            let request = http.post(url, JSON.stringify(body), params);

            check(request, {
                "Successful Response": (r) => r.status === 200
            });
        }
    });
  }
