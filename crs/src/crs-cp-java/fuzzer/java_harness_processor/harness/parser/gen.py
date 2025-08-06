import re

prompt = '''Analyze the structure of {parameters} of "{method_name}" in the following target code. 
Refer given invocation examples to generate Java code.

# Target Code

```java
{target_code}
```
{dep_invocation}
# Expected Output:

If you understand the structure of {parameters}, make an example to invoke the method.
Each parameter has a specific type and you need to provide the correct type of data to invoke the method.

"com.code_intelligence.jazzer.api.FuzzedDataProvider" class has only the following methods:
- consumeBoolean()
- consumeInt(int min, int max)
- consumeString(int size)
- consumeByte()
- consumeBytes(int size)


```java 
import com.code_intelligence.jazzer.api.FuzzedDataProvider;

public class FuzzerHarness {{
    public static void fuzzerTestOneInput(FuzzedDataProvider provider) throw Exception, Throwable {{
        
        <** YOUR CODE HERE **>
        
        {class_name}.{method_name}(...);
    }}
}}
```
'''


example_template = '''
## Example to Invoke "{method_name}" of "{class_name}"

```java
{code}
```
'''

dep_invocation_prompt = '''
Refer invocation examples of each dependent method that you need to generate a harness for.

# Invocation Examples of Dependent Methods

'''

def extract_codeblock(code: str):
    code_candidate = re.findall(r"```.*?\n(.*?)```", code, re.DOTALL)
    if len(code_candidate) > 0:
        code = code_candidate[0]
    
    return code


def extract_body(code: str, method_signature: str):
    # escape {method_signature} from regex special char
    method_signature = re.escape(method_signature)
    
    # extract body of the method
    body = re.findall(r"(\s*"+method_signature+r"\s*\{)(.*?)(\})", code, re.DOTALL)

def extract_body_force(code):
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


def generate_example_body(chatbot, code: str, class_name: str, method_name: str, parameters: list = [], dependencies = [] ):
    examples = []
    for dep_class_name, dep_method_name, invocation_code in dependencies:
        if invocation_code is None:
            continue
        method_idx = invocation_code.find("fuzzerTestOneInput(FuzzedDataProvider provider)")
        invocation_code = extract_body_force(invocation_code[method_idx:])[0]
        examples.append(example_template.format(class_name=dep_class_name, method_name=dep_method_name, code=invocation_code))

    dep_invocation_prompt = ""
    if len(examples) != 0:
        dep_invocation_prompt = dep_invocation_prompt + "\n".join(examples)
    
    chatbot.add_system_message("You are a Java code generator.\nYou make an sample code to invoke the method. Print ONLY the class code with imports.")
    chatbot.add_user_message(prompt.format( class_name=class_name, 
                                            method_name=method_name, 
                                            parameters=", ".join([f'"{p}"' for p in parameters]),
                                            target_code=code, dep_invocation=dep_invocation_prompt) )
    responses = chatbot.run()
    
    code = extract_codeblock(responses[0])
    return code
