#!/bin/bash

set -e

# Set server address
SERVER_ADDRESS="http://localhost:9000"

# Run joern http server
run-joern.sh

# Test GET /
echo "Testing GET /"
curl -s -X GET "$SERVER_ADDRESS" -H "Content-Type: application/json" | jq .
echo ""

# Test POST /single_query
echo "Testing POST /single_query"
curl -s -X POST "$SERVER_ADDRESS/single_query" -H "Content-Type: application/json" -d '{
    "query": "cpg.method.name.l",
    "input": "/joern/joern-cli/autoScript/test"
}' | jq .
echo ""

# Test POST /script_query
echo "Testing POST /script_query"
curl -s -X POST "$SERVER_ADDRESS/script_query" -H "Content-Type: application/json" -d '{
    "input": "/joern/joern-cli/autoScript/test",
    "queryPath": "/joern/joern-cli/autoScript/test/test.sc",
    "param": {
  "output": "/joern/joern-cli/autoScript/output.txt"
   }   
}' | jq .
echo ""

# Test POST /graph_query
echo "Testing POST /graph_query"
curl -s -X POST "$SERVER_ADDRESS/graph_query" -H "Content-Type: application/json" -d '{
  "input": "/joern/joern-cli/autoScript/test"
}' | jq .
echo ""

# Test POST /llm_poc
echo "Testing POST /llm_poc"
curl -s -X POST "$SERVER_ADDRESS/llm_poc" -H "Content-Type: application/json" -d '{
    "exclude": [],
    "dependent_jars": [],
    "input": "/joern/joern-cli/autoScript/test/",
    "queryPath": "/joern/joern-cli/autoScript/test/test.sc",
    "output": "/joern/joern-cli/jenkins.cpg.bin",
    "param": {
        "output": "/joern/joern-cli/autoScript/output.txt"
    }
}' | jq .
echo ""

