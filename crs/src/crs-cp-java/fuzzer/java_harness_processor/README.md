# Harness processor

## Description

## Usage


### Requirements

- Python 3
- pyyaml
- javalang
- openai

```
python3 -m pip install -r requirements.txt
```

### Command Options

```bash
$ python main.py -h
usage: main.py [-h] [-p {java,llm}] [-f {composite,jazzer,protobuf,concolic}] [-o OUTPUT_DIR] [-v] project harnessid

Harness Processor

positional arguments:
  project               project directory
  harnessid             harnessid in project.yaml

options:
  -h, --help            show this help message and exit
  -p {java,llm}, --processor {java,llm}
                        processor to use
  -f {composite,jazzer,protobuf,concolic}, --format {composite,jazzer,protobuf,concolic}
                        output harness format
  -o OUTPUT_DIR, --output_dir OUTPUT_DIR
                        output directory
  -v, --verbose         verbose mode
```

#### LLM Environment variables

  - `AIXCC_LITELLM_HOSTNAME`: hostname of the LLM server
  - `LITELLM_KEY`: key for the LLM server
  - `LITELLM_MODEL`: model for the LLM server(default: oai-gpt-4o)
  - `LITELLM_TEMPERATURE`: default temperature for the LLM server(default: 0.0)
  - `LITELLM_TOP_P`: default top p for the LLM server(default: 1)
  - `LITELLM_MAX_TOKENS`: default max tokens for the LLM server(default: 4096)
    
<br />

**Example**

```
$ python main.py -p llm ../asc-challenge-002-jenkins-cp/ id_1
[INFO] Generated Concolic Harness: ./JenkinsTwo_Concolic.java
[INFO] Generated Fuzz Harness: ./JenkinsTwo_Fuzz.java
[INFO] Generated Protobuf: ./JenkinsTwo.proto
```



## Fuzz Test

for **\<Fuzzer Options\>**, refer to the [Fuzz.md](https://github.com/Team-Atlanta/asc-challenge-002-jenkins-cp/blob/main/Fuzz.md) for more information. Use the options as is.

`./run.sh fuzz <Fuzzer Options>`


```
./tests/fuzz.sh <CP_DIR> <Fuzzer Options>
```


**Example**

```
./tests/fuzz.sh ../asc-challenge-002-jenkins-cp/ 1 - --experimental_mutator=1 -use_value_profile=1
```


# Sample 

### Test harness

```java

    public static void fuzzerTestOneInput(byte[] data) throws Exception {
        new JenkinsTwo().fuzz(data);
    }
    ...
    private void fuzz(byte[] data) {
        if (data.length < expected_data_length) {
            return;
        }

        ByteBuffer buf = ByteBuffer.wrap(data);
        int picker = buf.getInt();
        int count = buf.getInt();

        if (count > 255) return;

        String whole = new String(Arrays.copyOfRange(data, 8, data.length));

        String[] parts = whole.split("\0");

        if (3 != parts.length) {
            return;
        }
```

### Generated harnesses

####  Protobuf

```protobuf 
syntax = "proto2";

package ourfuzzdriver;
option java_package = "ourfuzzdriver";

message HarnessInput {
  required int32 field1 = 1;
  required int32 field2 = 2;
  required string field3 = 3;
  required string field4 = 4;
  required string field5 = 5;
}
```

```java
public class JenkinsTwo_Fuzz {
    public static void fuzzerTestOneInput(@NotNull HarnessInputOuterClass.HarnessInput input) throws Exception, Throwable {
        ByteBuffer buffer = ByteBuffer.allocate(8);
        buffer.putInt(input.getField1());
        buffer.putInt(input.getField2());

        String headerName = input.getField3();
        String headerValue = input.getField4();
        String command = input.getField5();

        String data = new String(buffer.array()) + headerName + "\0" + headerValue + "\0" + command;

        JenkinsTwo.fuzzerTestOneInput(data.getBytes());
    }
}
```

#### Jazzer 

```java
public class JenkinsTwo_Fuzz {
    public static void fuzzerTestOneInput(FuzzedDataProvider provider) throws Exception, Throwable {
        int picker = provider.consumeInt(Integer.MIN_VALUE, Integer.MAX_VALUE);
        int count = provider.consumeInt(0, 255);
        String headerName = provider.consumeString(64);
        String headerValue = provider.consumeString(64);
        String command = provider.consumeString(64);

        ByteBuffer buffer = ByteBuffer.allocate(8 + headerName.length() + 1 + headerValue.length() + 1 + command.length() + 1);
        buffer.putInt(picker);
        buffer.putInt(count);
        buffer.put(headerName.getBytes());
        buffer.put((byte) 0);
        buffer.put(headerValue.getBytes());
        buffer.put((byte) 0);
        buffer.put(command.getBytes());
        buffer.put((byte) 0);

        byte[] data = buffer.array();
        
        JenkinsTwo.fuzzerTestOneInput(data);
    }
}
```

#### Concolic

```java
import org.team_atlanta.*;
...

public class JenkinsTwo_Concolic {

    public static void main(String[] args) throws Throwable, Exception {
        BinaryArgumentLoader bal = new BinaryArgumentLoader(args[0]);
        FuzzedDataProvider provider = new FuzzedDataProvider(bal.readAsBytes());
        fuzzerTestOneInput(provider);
    }

    public static void fuzzerTestOneInput(FuzzedDataProvider provider) throws Exception {
        new JenkinsTwo_Concolic().fuzz(provider);
    }

    private void fuzz(FuzzedDataProvider provider) {
        int picker = provider.consumeInt(0, Integer.MAX_VALUE);
        int count = provider.consumeInt(0, 255);

        String headerName = provider.consumeString(10);
        String headerValue = provider.consumeString(10);
        String command = provider.consumeString(20);

        setup_utilmain();
        try {
            setup_replacer();
        } catch (Exception e) {
            return; // eat it
        }

        set_header(headerName, headerValue);

        for (int i = 0; i < count; i++) {
            try {
                switch (picker) {
                    case 13:
                        nw.doexecCommandUtils(command, req, resp);
                        break;
                    default:
                        throw new Exception("unsupported method picker");
                }
            } catch (Exception e) {
                continue; // eat it
            }
        }
    }
    ...
}

```

#### Blob 

```java
public class JenkinsTwo_BlobGenerator {
    public static void fuzzerTestOneInput(@NotNull HarnessInputOuterClass.HarnessInput input) throws Exception, Throwable {
        ByteBuffer buffer = ByteBuffer.allocate(8);
        buffer.putInt(input.getField1());
        buffer.putInt(input.getField2());

        String headerName = input.getField3();
        String headerValue = input.getField4();
        String command = input.getField5();

        String data = new String(buffer.array()) + headerName + "\0" + headerValue + "\0" + command;

        LocalBlobGenerator.fuzzerTestOneInput(data.getBytes());
    }
}
```

# Result

<!-- | Harness ID | Generation | Fuzzing |
| --- | --- | --- |
| 1 | Y (argc: 3) | too slow |
| 2 | N | - |
| 3 | Y (argc: 5) | - |
| 4 | Y (argc: 2) | - |
| 5 | Y (argc: 4) | Y |
| 6 | Y (argc: 4) | - |
| 7 | Y (argc: 1) | Y |
| 8 | Y (argc: 4) | Y |
| 9 | Y (argc: 3) | Y |
| 10 | Y (argc: 8) | - |
| 11 | Y (argc: 4) | too slow |
| 12 | Y (argc: 1) | - | -->
