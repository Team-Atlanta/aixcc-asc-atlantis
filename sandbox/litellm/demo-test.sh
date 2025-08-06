#!/bin/bash
# Script to demonstrate basic LLM forwarding for the models we currently have API keys and configs for.
# Internal testing only

MODELS=("oai-gpt-3.5-turbo" "oai-gpt-4" "oai-gpt-4-turbo" "oai-gpt-4o" "claude-3-opus"
	"claude-3-sonnet" "claude-3.5-sonnet" "claude-3-haiku" "gemini-1.0-pro" "gemini-1.5-pro" "fake-openai-endpoint"
	"azure-gpt-3.5-turbo" "azure-gpt-4o" "azure-gpt-3.5-turbo-16k")
EMB_MODELS=("oai-text-embedding-3-large" "oai-text-embedding-3-small" "textembedding-gecko@003"
	"azure-text-embedding-3-small" "azure-text-embedding-3-large")

for model in "${MODELS[@]}"; do
	echo ""
	echo "Output for $model:"
	curl --location 'http://localhost:8081/chat/completions' \
		--header 'Content-Type: application/json' \
		--header 'Authorization: Bearer sk-1234' \
		--data '{
      "model": "'"$model"'",
      "messages": [
        {
       "role": "user",
              "content": "What is the result of adding two and two together?"
            }
          ]
        }' # | jq '.choices[0].message.content, .model'
	echo ""

done

for model in "${EMB_MODELS[@]}"; do
	echo ""
	echo "Output for $model:"
	curl --location 'http://localhost:8081/embeddings' \
		--header 'Content-Type: application/json' \
		--header 'Authorization: Bearer sk-1234' \
		--data '{
        "model": "'"$model"'",               
        "input": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA12345"
      }' #| jq '.choices[0].message.content, .model'
	echo ""
done
