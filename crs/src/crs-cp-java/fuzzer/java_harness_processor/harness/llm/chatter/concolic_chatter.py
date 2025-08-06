from ..llm_proxy import ChatBot


class ConcolicGenerateChatter:
    def convert_byte_to_jazzer(chatbot: ChatBot, code: str):
        prompt = '''I'm creating a java harness for fuzzing. Analyze the structure of 'byte[] data' of 'fuzzerTestOneInput' in the following target code. 

# Target Code:

```java        
{code}
```


# Tip

If you understand the structure of "byte[] data", make an example to invoke "fuzzerTestOneInput".
"com.code_intelligence.jazzer.api.FuzzedDataProvider" class has only the following methods.

- consumeBoolean()
- consumeInt(int min, int max)
- consumeString(int size)
- consumeByte()
- consumeBytes(int size)

String and Byte size are larger.

# Output

Print ONLY the class code with imports.
Do not skip code.
Convert byte[] parameter into `FuzzedDataProvider provider` parameter.
    '''
        chatbot.add_system_message('You are a java code generator. So, you do print only code.')
        chatbot.add_user_message(prompt.format(code=code))
        responses = chatbot.run()
        
        return responses


    def add_main_method(chatbot: ChatBot, code):
        prompt = '''
# target code

```java
{code}
```

Add the following main method to the class: 

```java
    public static void main(String[] args) throw Throwable, Exception {{
        BinaryArgumentLoader bal = new BinaryArgumentLoader(args[0]);
        FuzzedDataProvider provider = new FuzzedDataProvider(bal.readAsBytes());
        {initialization}
        fuzzerTestOneInput(provider);
    }}
```
Print just a java code.
Do not skip code.
'''
    
        initialization = ''
        if 'void fuzzerInitialize' in code:
            initialization = 'fuzzerInitialize(); // only if `fuzzerInitialize()` exists in the code'
            
        chatbot.add_system_message('You are a java code generator. So, you do print only code.')
        chatbot.add_user_message(prompt.format(code=code, initialization=initialization))
        responses = chatbot.run()
        
        return responses

    def change_class_name(chatbot: ChatBot, code, class_name):
        prompt = '''Change public class name to {class_name} in the following code.

# target code

```java
{code}
```

Print just a java code.
Do not skip code.
'''

        chatbot.add_system_message('You are a java code generator. So, you do print only code.')
        chatbot.add_user_message(prompt.format(class_name=class_name, code=code))
        responses = chatbot.run()
        
        return responses
