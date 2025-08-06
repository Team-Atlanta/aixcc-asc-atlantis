from ..llm_proxy import ChatBot

class JavaStaticConverterChatter:
    def convert_class_name(chatbot: ChatBot, code: str, from_class_name: str, to_class_name: str):
        options = ""
        prompt = '''Convert the class name "{from_class_name}" to "{to_class_name}" in the following target code.

{options}
# Target Code:  

```java
{code}
```

Print just a java code and imports
Do not skip code.
'''
        chatbot.add_system_message('You are a java code generator. Print only a java code')
        chatbot.add_user_message( prompt.format(
                from_class_name = from_class_name,
                to_class_name   = to_class_name,
                code            = code, 
                options         = options)) 
        
        responses = chatbot.run()
            



    def convert_byte_parameter(chatbot: ChatBot, code: str, class_name: str=""):
        options = ""
        if class_name != "":
            options = f'Then, change the class name to "{class_name}"'
            
        prompt = '''"fuzzerTestOneInput(...)" in the follow code gets data from a file. Convert it to get from `byte[] data` parameter`.
{options}

```java
{code}
```

Print just a java code.
Do not skip code.
'''
        chatbot.add_user_message(prompt.format(code=code, options=options)) 
        responses = chatbot.run()
            
        return responses

    def convert_string_parameter(chatbot: ChatBot, code: str, class_name: str=""):
        options = ""
        if class_name != "":
            options = f'Then, change the class name to "{class_name}"'
            
        prompt = '''"fuzzerTestOneInput(...)" gets byte[] in the follow target code. Convert it to get from `String data` parameter`.
{options}

# target code

```java
{code}
```

Add the following main method to the class:

```java
public static void main(String[] args) throw Throwable, Exception {{
    fuzzerTestOneInput(new String(new java.io.FileInputStream(args[0]).readAllBytes()));
}}
```
Print just a java code.
Do not skip code.
'''
        chatbot.add_system_message('You are a java code generator. Print only a java code')
        chatbot.add_user_message(prompt.format(code=code, options=options)) 
        responses = chatbot.run()
            
        return responses

    def convert_method_signature(chatbot: ChatBot, code: str, from_method_signature: str, to_method_signature: str, imports: list = None):
        options = ""
        if imports is not None:
            options += "Add the following imports: \n"
            for imp in imports:
                options += f" - `import {imp};`\n"    
        
        prompt = '''Convert the method signature "{from_method_signature}" to "{to_method_signature}" in the following target code.

{options}
# Target Code:  

```java
{code}
```

Print just a java code and imports
Do not skip code.
'''
        chatbot.add_system_message('You are a java code generator. Print only a java code')
        chatbot.add_user_message( prompt.format(
                from_method_signature   = from_method_signature,
                to_method_signature     = to_method_signature,
                code                    = code, 
                options                 = options)) 
        
        responses = chatbot.run()
            
        return responses



class CodeHarnessGeneratorChatter:
    def harness_generate(chatbot: ChatBot, code: str):
        msg = '''the follow code is harness code. if you understand the structure of 'byte[] data', make an example to invoke 'fuzzerTestOneInput()'\n'''
        chatbot.add_user_message(msg + code)
        chatbot.run()
        
        chatbot.add_user_message('''You are a java code generator. I'm creating harness for fuzzing. Fill the blank I have marked. Print ONLY the class code with imports.\n

```java
import com.code_intelligence.jazzer.api.FuzzedDataProvider;

public class FuzzerHarness {
    public static void fuzzerTestOneInput(FuzzedDataProvider provider) {
        String data;
        
        // BLANK: Fill with your code here
            
        TargetClass.fuzzerTestOneInput(data.getBytes());
    }
}
```
''')
        responses = chatbot.run()
        
        return responses

    def harness_generate2(chatbot: ChatBot, code: str):
        msg = '''You are a java code generator. So, you do print only code. I'm creating harness for fuzzing. The follow code is a test code: \n'''

        sample_code = '''\nIf you understand the structure of 'byte[] data', make an example to invoke 'fuzzerTestOneInput()'
Fill the blank I’ve marked with your code. Print ONLY the class code with imports.

```java
import com.code_intelligence.jazzer.api.FuzzedDataProvider;

public class FuzzerHarness {
    public static void fuzzerTestOneInput(FuzzedDataProvider provider) {
        String data;
        
        // BLANK: Fill with your code here
            
        TargetClass.fuzzerTestOneInput(data.getBytes());
    }
}
```
'''
        chatbot.add_user_message(msg + code + sample_code)
        responses = chatbot.run()
        
        return responses

    def harness_generate3(chatbot: ChatBot, code: str, class_name: str = None):
        chatbot.add_system_message('You are a java code generator. So, you do print only code.')
        prompt = '''I'm creating harness for fuzzing. Analyze the structure of 'byte[] data' in the follow test code. 

Code:

```java        
{code}
```

If you understand the structure of 'byte[] data', change it into 'fuzzerTestOneInput(FuzzedDataProvider provider)'

"com.code_intelligence.jazzer.api.FuzzedDataProvider" class has only the following methods:
- consumeBoolean()
- consumeInt(int min, int max)
- consumeString(int size)
- consumeBytes(int size)

Print ONLY the class code with imports.
{options}

```java 
** Your code here **
```
'''

        options = ""
        if class_name:
            options = f'The class name must be "{class_name}".'
            
        chatbot.add_user_message(prompt.format(code=code, options=options))
        responses = chatbot.run()
        
        return responses

    def harness_generate4(chatbot: ChatBot, code: str, class_name: str = "FuzzerHarness"):
        
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
- consumeString(int largeSize)
- consumeByte()
- consumeBytes(int largeSize)

String is unicode so size of byte[] instead of String.
If you allocate ByteBuffer with `ByteBuffer.allocate`, the size cannot be larger
than 2000000, so you should add corresponding size check.
If you alocate large ByteBuffer, you should use `ByteBuffer.position` accordingly to avoid
to maintain large buffer in memory.


# Output

Print ONLY the class code with imports.
Fill the blank I’ve marked in the following code. Print ONLY the class code with imports.
Use the same import statements as the target code.
Use no package and Import target package.
Do not skip code.
```java
## No package ##
## imports ##

public class {class_name} {{
    public static void fuzzerInitialize() {{
        // If you need to initialize the target class, 
        // <Target class>.fuzzerInitialize();
    }}
    
    public static void fuzzerTestOneInput(FuzzedDataProvider provider) throw Exception, Throwable {{
        String data;
        
        ** Fill with your code here **
            
        <Target class>.<Target method>(data.getBytes());
    }}
}}
```
'''
        chatbot.add_system_message('You are a java code generator. So, you do print only code.')
        chatbot.add_user_message(prompt.format(code=code, class_name=class_name))
        responses = chatbot.run()
        
        return responses


    def protobuf_generate(chatbot: ChatBot, code: str, target_class_name: str = None, class_name: str = "FuzzerHarness"):
        chatbot.add_system_message('You are a java code generator. So, you do print only code.')
        prompt = '''I'm creating a java harness for fuzzing. Analyze the structure of 'byte[] data' of 'fuzzerTestOneInput' in the following target code. 

# Target Code:

```java        
{code}
```


If you understand the structure of "byte[] data", make an example to invoke "fuzzerTestOneInput".
"com.code_intelligence.jazzer.api.FuzzedDataProvider" class has only the following methods.

- int consumeInt(0, 255)[FIXED SIZE]
- boolean consumeBoolean()
- byte[] consumeBytes(64)[FIXED SIZE]
- java.lang.String consumeString(64)[FIXED SIZE]

String is unicode so size of byte[] instead of String.
if you allocate ByteBuffer with `ByteBuffer.allocate`, the size cannot be larger
than 2000000, so you should add corresponding size check.
If you alocate large ByteBuffer, you should use `ByteBuffer.position` accordingly to avoid
to maintain large buffer in memory.

Print ONLY the class code with imports.
Do not skip code.

## Imports

Import the following classes and target package.
```java
import com.code_intelligence.jazzer.mutation.annotation.NotNull;
import com.code_intelligence.jazzer.api.FuzzedDataProvider;
import java.nio.ByteBuffer;
import <target package>.*;
```

Fill the blank I’ve marked in the following code. Print ONLY the class code with imports.
Use the same import statements as the target code.


```java
## No package ##
## Imports ##

public class {class_name} {{
    public static void fuzzerInitialize() {{
        // If you need to initialize the target class, 
        // {target_class_name}.fuzzerInitialize();
    }}
    
    public static void fuzzerTestOneInput(FuzzedDataProvider input) throw Exception, Throwable {{
        String data;
        
        ** Fill with your code here **
            
        {target_class_name}.fuzzerTestOneInput(data.getBytes());
    }}
}}
```
'''
        
        chatbot.add_user_message(prompt.format(code=code, class_name=class_name, target_class_name=target_class_name))
        responses = chatbot.run()
        
        return responses
