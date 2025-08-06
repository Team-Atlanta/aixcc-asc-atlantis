import json
import sys

log_file = 'log/report.json'
if len(sys.argv) > 1:
    log_file = sys.argv[1]

with open(log_file) as f:
    text = f.read()
res = json.loads(text)
for r in res:
    if not r['pass']:
        print('===================')
        print(r['name'])
        print('===================')
        print(r['generated'])
