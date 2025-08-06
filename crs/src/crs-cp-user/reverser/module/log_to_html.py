import sys
import os
import json
import html

log_file = sys.argv[1]
out_file = sys.argv[2]

with open(log_file) as file:
  lines = file.readlines()

chunks = []

for i, line in enumerate(lines):
  data = json.loads(line)
  messages = [f'<h3>Prompt {i}</h3><div syle="padding-left: 2rem"><p>{message["role"]}</p><pre>{html.escape(message["content"])}</pre></div>' for i, message in enumerate(data['messages'])]
  messages += [f'<h3>Response</h3><div syle="padding-left: 2rem"><p>{data.get("role", "")}:</p><pre>{html.escape(data["response"])}</pre></div>']
  chunks.append(f'<h1>Prompt {i}</h1><div syle="padding-left: 2rem">' + f'<p>model: {data["model"]}</p>' + f'<p>cost: {data["cost"]}</p>' + ''.join(messages) + '</div>')

with open(out_file, 'w+') as file:
  file.write('<!DOCTYPE html><html><body>' + ''.join(chunks) + '</body></html>')