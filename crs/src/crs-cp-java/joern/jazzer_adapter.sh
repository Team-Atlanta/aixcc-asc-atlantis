#!/bin/bash

if [ "$#" -ne 3 ]; then
  echo "Usage: $0 <input_path> <output_path> <git_repo>"
  exit 1
fi

INPUT_PATH=$1
OUTPUT_PATH=$2
GIT_REPO=$3

DEPENDENT_JARS=$(echo "$GIT_REPO" | tr ':' ',')

URL='http://localhost:9000/llm_poc'

JSON_DATA=$(cat <<EOF
{
    "exclude": [],
    "dependent_jars": ["$DEPENDENT_JARS"],
    "input": "$INPUT_PATH",
    "queryPath": "/joern/joern-cli/autoScript/jazzer.sc",
    "output": "/joern/joern-cli/jazzer.cpg.bin",
    "param": {
        "git_dir": "$GIT_REPO",
        "output": "$OUTPUT_PATH"
    }
}
EOF
)

RETRY_COUNT=0
MAX_RETRIES=10

until [ "$RETRY_COUNT" -ge "$MAX_RETRIES" ]
do
  curl --location "$URL" \
       --header 'Content-Type: application/json' \
       --data "$JSON_DATA"

  if [ $? -eq 0 ]; then
    break
  fi

  RETRY_COUNT=$((RETRY_COUNT+1))
  echo "Curl request failed. Retrying in 5 seconds... ($RETRY_COUNT/$MAX_RETRIES)"
  sleep 5
done

if [ "$RETRY_COUNT" -eq "$MAX_RETRIES" ]; then
  echo "Curl request failed after $MAX_RETRIES attempts"
  exit 1
fi

# Check if the output file exists
if [ ! -f "$OUTPUT_PATH" ]; then
  echo "Output file does not exist"
  exit 1
fi

TEMP_FILE="${OUTPUT_PATH}.temp"
cp "$OUTPUT_PATH" "$TEMP_FILE"
awk '{
  if ($0 ~ /::/) {
    split($0, arr, "::");
    print arr[1];
  }
  else {
    print $0;
  }
}' "$TEMP_FILE" > "$OUTPUT_PATH"
