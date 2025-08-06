import { default as litellm } from './litellm/script.js'
import { default as iapi } from './iapi/script.js'
import { textSummary } from './index.js'

export const options = {
  thresholds: {
    http_req_duration: ['p(90)<300'],
    checks: ['rate==1.0']
  },
  scenarios: {
    liteLlmScenario: { // changed from liteLLMScenario
      exec: 'litellmRun',
      executor: 'per-vu-iterations',
      vus: 1,
      iterations: 10,
      maxDuration: '10s'
    },
    iapiScenario: {
      exec: 'iapiRun',
      executor: 'per-vu-iterations',
      vus: 1,
      iterations: 10,
      maxDuration: '10s'
    }
  }
}

export function litellmRun () {
  litellm()
}

export function iapiRun () {
  iapi()
}

export function handleSummary (data) {
  return {
    stdout: textSummary(data, { indent: ' ', enableColors: true })
  }
}
