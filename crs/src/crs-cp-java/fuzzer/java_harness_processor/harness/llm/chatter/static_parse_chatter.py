from ..llm_proxy import ChatBot


class StaticParseChatter:
    def convert_arg_input(chatbot: ChatBot, code: str):
        msg = f'''`fuzzerTestOneInput(...)` in the follow code gets data from a file. Convert it to get from `byte[] data` parameter`. Please print just java code: 
        
```java
{code}
```

'''
        chatbot.add_user_message(msg) 
        responses = chatbot.run()
        
        return responses
    
    def extract_invocations(chatbot: ChatBot, code: str, class_name, method_name: str):
        chatbot.add_system_message("You are a code static analyzer.")
        prompt = f'''Extract method invocations in the "{method_name}" method in the following "{class_name}" class code.\n

# Target code:

```java
{code}
```

Print only the invocations in the following format:

# Output Format 

- "class_name.method_name(Type1 arg1, Type2 arg2, ...)"


# The output examples are: 

- "com.code_intelligence.jazzer.api.FuzzedDataProvider.consumeInt(int min, int max)"
- "hudson.cli.ConsoleCommand.printUsageSummary(PrintStream stderr)"
- "aixcc.util.StaplerReplacer.setWebApp(WebApp webApp)"
- "jenkins.agents.WebSocketAgents.doIndex(StaplerRequest req, StaplerResponse rsp)"


'''
        chatbot.add_user_message(prompt)
        response = chatbot.run()
        return response
    
    def has_data_format(chatbot: ChatBot, code: str):
        msg = '''You are a code static analyzer.
Do you think 'byte[] data' has the specific structure? Answer with Only 'Yes' or 'No'\n\n'''
        chatbot.add_user_message(msg + f'```java\n{code}\n```')
        return chatbot.run()

        
    def infer_structured_format(chatbot: ChatBot, code: str, class_name, method_name):
        msg = f'''You are a java code generator. Analyze the structure of parameters of "{method_name}".
        
# code 

```java
{code}
```

'''

        sample_code = '''
If you understand the structure of parameters, make an example to invoke the method.'

"com.code_intelligence.jazzer.api.FuzzedDataProvider" class has only the following methods:
- consumeBoolean()
- consumeInt(int min, int max)
- consumeString(int size)
- consumeBytes(int size)

Print ONLY the class code with imports. 

```java 
import com.code_intelligence.jazzer.api.FuzzedDataProvider;

public class FuzzerHarness {
    public static void fuzzerTestOneInput(FuzzedDataProvider provider) throw Exception {
        ** Your code here **
        TargetClass.TargetMethod(...);
    }
}
```

'''
        chatbot.add_user_message(msg + sample_code)
        responses = chatbot.run()
        
        return responses

        
    def infer_structured_format2(chatbot: ChatBot, code: str, class_name, method_name):
        msg = f'''You are a Java harness code generator.

# Your task is:

1. Analyze the structure of parameters of "{method_name}"
2. Generate a Java harness code to invoke the method using "com.code_intelligence.jazzer.api.FuzzedDataProvider"
"com.code_intelligence.jazzer.api.FuzzedDataProvider" class has only the following methods:
- consumeBoolean()
- consumeInt(int min, int max)
- consumeString(int size)
- consumeBytes(int size)
3. Print ONLY the class code with imports. 

# Target code

```java
{code}
```

# Example of the output format:

* example 1

```java 
import com.code_intelligence.jazzer.api.FuzzedDataProvider;

public class FuzzerHarness {{
    public static void fuzzerTestOneInput(FuzzedDataProvider provider) throw Exception {{
        ** Your code here **
        {class_name}.{method_name}(...);
    }}
}}
```

* example 2

```java 
import com.code_intelligence.jazzer.api.FuzzedDataProvider;

public class FuzzerHarness {{
    public static void fuzzerTestOneInput(FuzzedDataProvider provider) throw Exception {{
        ** Your code here **
        {class_name} targetClass = new {class_name}(...);
        {class_name}.{method_name}(...);
    }}
}}
```
'''

        chatbot.add_user_message(msg)
        responses = chatbot.run()
        
        return responses

    def extract_method_body(chatbot, code: str, class_name: str, method_name: str):
        chatbot.add_system_message("You are a Java static analyzer.")
        prompt = f'''Extract the body of the "{method_name}" method in the {class_name} class.

# Target code:
```java
{code}
```

Only print the body of the method. 
'''
        chatbot.add_user_message(prompt)
        response = chatbot.run()
        return response