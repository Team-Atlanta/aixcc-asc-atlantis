import os
import openai
import time

MODEL = 'oai-gpt-4o'
client = openai.OpenAI(
    api_key=os.environ["LITELLM_KEY"],
    base_url=os.environ["AIXCC_LITELLM_HOSTNAME"]
)

def prompt_llm(messages):
    while True:
        try:
            quote = client.chat.completions.create(
                model = MODEL,
                messages=messages,
                temperature = 0.1,
            )

            answer = quote.choices[0].message.content

            return answer
        except openai.RateLimitError:
            time.sleep(10)
        except openai.OpenAIError:
            time.sleep(5)
        except Exception as e:
            print(f"Had an unhandled exception: {e}")
            return ""
