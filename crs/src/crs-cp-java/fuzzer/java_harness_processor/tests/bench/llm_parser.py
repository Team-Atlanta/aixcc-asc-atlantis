import re

from bench_init import *

from harness.utils.builder import CPBuilder
from harness.common.project import Project
from harness.parser.repository import JavaRepository
from harness.llm import ChatBot
from harness.utils.logger import Log

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

class LLMJavaStaticParser:
    def __init__(self):
        self.code = None
    
    def get_body(self, class_name: str, method_name: str):
        tcode = self.__remove_comments(self.__code)
        class_body = tcode[tcode.find(f"class {class_name}"):]
        class_body = self.__remove_brackets(class_body)[0]
        
        method_bodies = self.__remove_brackets(class_body)
        
        raw_class_body = class_body
        for method_body in method_bodies:
            method_header = raw_class_body[:raw_class_body.find(method_body)]
            if method_name in method_header:
                return method_body

            raw_class_body = raw_class_body[raw_class_body.find(method_body) + len(method_body) + 1:]
        
        return None

    def get_invocations(self, code: str, class_name: str, method_name: str):
        chatbot = ChatBot(temperature=0.0, n=1)
        res = StaticParseChatter.extract_invocations(chatbot, code, class_name, method_name)[0]
        res = self.__extract_codeblock(res)
        res = res.strip()
        
        targets = re.findall(r"- \"(.*?)\"", res)
        targets = list(set(targets))
        
        return targets

    def __remove_brackets(self, code):
        stack = []
        result = []
        for i, c in enumerate(code):
            if c == '{':
                stack.append(i)
            elif c == '}':
                if stack:
                    start = stack.pop()
                    if len(stack) == 0:
                        result.append(code[start + 1:i])
                        
        return result   
    
    def __remove_comments(self, code):
        code = re.sub(r'//.*', '', code)
        code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
        return code
    
    def __extract_codeblock(self, code: str):
        code_candidate = re.findall(r"```.*?\n(.*?)```", code, re.DOTALL)
        if len(code_candidate) > 0:
            code = code_candidate[0]
        
        return code
    

    # Deprecated
    def __get_body(self, code, class_name, method_name):
        chatbot = ChatBot(temperature=0.0, n=1)
        res = StaticParseChatter.extract_method_body(chatbot, code, class_name, method_name)[0]
        res = self.__extract_codeblock(res)
        res = res.strip()
        return res

    
    # def get_dependencies(self, code: str, class_name, method_name: str) -> list[str]:
    #     chatbot = ChatBot(temperature=0.0, n=1)
    #     res = StaticParseChatter.extract_invocations(chatbot, code, method_name)[0]
    #     res = self.__extract_codeblock(res)
    #     res = res.strip()
    #     invocations = re.findall(r"- \"(.*?)\"", res)
    
    #     invocations = list(set(invocations))
        
    #     dependencies = []
    #     for invocation in invocations:
    #         parsed_invocation = re.findall(r'(\w+)\.(\w+)\((.*?)\)', invocation)
    #         if len(parsed_invocation) == 1:
    #             classname, methodname, arguments = parsed_invocation[0]
                
    #             for target_file in self.repository.find_file_by_name(f'{classname}.java'):
    #                 dependencies.append((target_file, classname, methodname, arguments))
    #         else: 
    #             print("Not typical java method : ", invocation)
        
    #     return dependencies

