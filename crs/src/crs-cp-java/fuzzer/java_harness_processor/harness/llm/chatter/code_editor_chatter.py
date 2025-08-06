from ..llm_proxy import ChatBot


prompt = '''Edit the following java code.

# Command
{command}

```java
{target_code}
```

Print only a java code.
Do not skip code.
'''

class JavaCodeEditChatter:
    def edit_code(chatbot: ChatBot, code: str, command: str):
        chatbot.add_system_message("You are a java code editor. Print only a java code")
        chatbot.add_user_message(prompt.format(target_code=code, command=command))
        return chatbot.run()