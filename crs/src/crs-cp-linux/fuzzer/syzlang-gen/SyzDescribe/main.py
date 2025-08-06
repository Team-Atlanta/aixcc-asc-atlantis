import openai

import subprocess
import os, sys
import re
import glob
import json
import shutil
import argparse

from tree_sitter import Language, Parser
import tree_sitter_c as ts_c

import instructor
from pydantic import BaseModel, field_validator

from llm_util import MODEL

import time

C_LANGUAGE = Language(ts_c.language())
tree_parser = Parser(C_LANGUAGE)

# Function to find a node by its type and name
def find_function_node(node, function_name, source_code):
    if node.type == 'function_definition':
        # Get the function name identifier node
        identifier_node = node.child_by_field_name('declarator').child_by_field_name('declarator')
        if identifier_node and source_code[identifier_node.start_byte:identifier_node.end_byte] == function_name:
            return node
    for child in node.children:
        result = find_function_node(child, function_name, source_code)
        if result:
            return result
    return None


def replace_function_code(source_code, tree, function_node, new_code):
    # Split the source code into lines
    lines = source_code.splitlines()

    # Get the start and end points of the function node
    start_line, start_col = function_node.start_point
    end_line, end_col = function_node.end_point

    # Replace the lines in the range with the new code
    new_lines = new_code.strip().splitlines()
    modified_lines = lines[:start_line] + new_lines + lines[end_line + 1:]

    # Join the modified lines back into a single string
    modified_code = "\n".join(modified_lines).encode('utf8')

    # Compute the start and end byte positions
    start_byte = function_node.start_byte
    end_byte = function_node.end_byte

    # Update the tree with the edits
    tree.edit(
        start_byte=start_byte,
        old_end_byte=end_byte,
        new_end_byte=start_byte + len(modified_code) - len(source_code.encode('utf8')),
        start_point=function_node.start_point,
        old_end_point=function_node.end_point,
        new_end_point=(start_line + len(new_lines) - 1, len(new_lines[-1]))
    )

    # Reparse the modified code to update the tree
    new_tree = tree_parser.parse(modified_code)

    # Return the modified code and the updated tree
    return modified_code.decode('utf8'), new_tree


def get_existing_functions(tree):
    query = C_LANGUAGE.query("""
    (
        function_definition
        declarator: (function_declarator declarator: (identifier) @function.name)
    )
    """)
    captures = query.captures(tree.root_node)
    
    function_names = [c[0].text.decode('utf8') for c in captures]

    return function_names


def compile_code_with_retry(retries=5, command=None):
    if not command:
        command = f"bash {buildscript_path}"

    result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=source_base)
    
    # Get the stdout
    stdout = result.stdout
    stderr = result.stderr

    while "error" in stderr and retries > 0:
        syntax_prompt = f"""You will be given some source code, as well as the errors
        which occur when the source code is compiled. Your job is to fix the errors which exist.

        The compilation log is:

        ```
        {stderr}
        ```
        """

        llm_restructure(syntax_prompt)

        result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=source_base)
        
        stdout = result.stdout
        stderr = result.stderr

        retries -= 1

    if stderr.strip():
        print("still got an error: ", stderr)


def llm_restructure(system_prompt):
    related_files = glob.glob(os.path.join(driver_realpath, "**", "*.c"), recursive=True)

    sources = {fname: open(fname).read().strip() for fname in related_files}

    source_listing = ""

    for path, code in sources.items():
        source_listing += f"Here is the source code of {path}:\n{code}\n```\n"

    user_prompt = f"""{source_listing}

    Please output the name of the file you want to change, the name of the function you want to change, and the new proposed source code for any functions that you believe should be changed. You may output multiple of these triples.
    """

    source_trees = {
        path: tree_parser.parse(bytes(open(path).read(), "utf-8")) for path in sources
    }

    class FunctionInfo(BaseModel):
        #todo: this is currently full path. maybe change just relative inside driver?
        source_filename: str
        function_name: str
        source_code: str
        
        @field_validator('source_filename')
        def source_filepath_exists(cls, value):
            if value not in sources:
                raise ValueError(f"{value} is not a valid file that was given to you. The choices are {', '.join([i for i in sources])}")
            return value

        @field_validator('function_name', mode='after')
        def validate_function_name(cls, value, values):
            if "source_filename" not in values.data.keys():
                raise ValueError(f"You have not specified a source filename for the function named {value}.")

            source_fname = values.data["source_filename"]
            if value not in get_existing_functions(source_trees[source_fname]):

                test_node = find_function_node(source_trees[source_fname].root_node, value, sources[source_fname])
                if not test_node:
                    raise ValueError(f"{value} is not a valid function in that file. Think through your steps.")

            return value

    class ChangeInfo(BaseModel):
        changes: list[FunctionInfo]

    answer = ChangeInfo(changes=[])

    while True:
        try:
            answer = client.chat.completions.create(
                model = MODEL,
                response_model=ChangeInfo,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature = 0.1,
                max_retries=10
            )

            break
        except openai.RateLimitError:
            time.sleep(10)
        except openai.OpenAIError:
            time.sleep(5)
        except Exception as e:
            print(f"Had an unhandled exception: {e}")
            break

    for function in answer.changes:
        print(f"changing {function.source_filename}: {function.function_name}")
        function_node = find_function_node(
            source_trees[function.source_filename].root_node,
            function.function_name,
            sources[function.source_filename]
        )

        if not function_node:
            print("LLM returned a nonexistent function node, skipping..")
            continue

        new_source, new_tree = replace_function_code(
            sources[function.source_filename],
            source_trees[function.source_filename],
            function_node,
            function.source_code
        )

        
        sources[function.source_filename] = new_source
        source_trees[function.source_filename] = new_tree

    for source_path, source_content in sources.items():
        with open(source_path, "w") as f:
            f.write(source_content)



def run_syzdescribe():
    # Run the command and capture the stdout
    command = f"{syzdescribe_path} --config={analysis_config_path} --name-script={name_script_path} --handler-script={handler_script_path} --kernel-src={source_base}"
    result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=tool_workdir)
    
    # Get the stdout
    stdout = result.stdout
    stderr = result.stderr

    if stderr:
        # handle error cases
        if "empty_structures" in stderr:
            retries = 5

            while retries >= 0 and stderr:
                llm_restructure(syzdescribe_restructure_prompt)
                compile_code_with_retry(retries=5)

                result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=tool_workdir)
    
                # Get the stdout
                stdout = result.stdout
                stderr = result.stderr

                retries -= 1

        else:
            print(stderr)

    return stdout.strip().splitlines(), stderr


def get_kernel_version():
    config_path = os.path.join(source_base, ".config")

    if os.path.exists(config_path):
        with open(config_path) as f:
            kernel_config = f.read().strip()
            pattern = r"Linux/x86 ([0-9\.]+) Kernel"
            match = re.search(pattern, kernel_config)

            return match.group(1)

    return ""


def extract_major_minor(version_str):
    # Split the version string by dots
    parts = version_str.split('.')
    
    # Handle cases with fewer than two parts
    if len(parts) == 1:
        major = int(parts[0])
        minor = 0
    else:
        major = int(parts[0])
        minor = int(parts[1])

    return major, minor


client = instructor.from_openai(
    openai.OpenAI(
    api_key=os.environ["LITELLM_KEY"],
    base_url=os.environ["AIXCC_LITELLM_HOSTNAME"]
))

argparser = argparse.ArgumentParser(description='Generate syzlang for a driver.')

argparser.add_argument('--source_base', required=True, help='Path to the source base directory')
argparser.add_argument('--driver_path', required=True, help='Path to the driver directory')
argparser.add_argument('--workdir', default='.', help='Path to the working directory (default: current directory)')
argparser.add_argument('--output_file', required=True, help='Path to the output file')
argparser.add_argument('--copy_source', action='store_true', help='Copy Linux source to local workdir')
argparser.add_argument('--num_cores', default=16, type=int, help='Number of cores to use while building')


args = argparser.parse_args()

source_base = os.path.realpath(args.source_base)
driver_path = args.driver_path
tool_workdir = os.path.realpath(args.workdir)
output_file = args.output_file
num_cores = args.num_cores

# copy linux kernel source to workdir

# first check if it already exists. delete if so
new_source_base = os.path.join(tool_workdir, "syzdescribe_kernel_base")

if not os.path.exists(new_source_base) or args.copy_source:
    if os.path.isdir(new_source_base):
        shutil.rmtree(new_source_base)
    shutil.copytree(source_base, new_source_base)

source_base = new_source_base


syzdescribe_path = "./build/tools/SyzDescribe/SyzDescribe"

kernel_version = get_kernel_version()

print(f"Found kernel version {kernel_version}")


if not kernel_version:
    kernel_version = "6.1.54"   # exemplar-src default


kernel_major, kernel_minor = extract_major_minor(kernel_version)

linux_version = "v6.1"

if kernel_major <= 5:
    linux_version = "v5.12"
else:
    if kernel_minor < 6:
        linux_version = "v6.1"
    else:
        linux_version = "v6.6"

print(f"Decided to use tool version {linux_version}")


bitcode_gen_path = f"./Generate_Linux_Kernel_Bitcode/v6.1/KernelBitcode.go"
knowledge_path = f"./config/knowledge-{linux_version}.json"

bitcode_gen_path = os.path.realpath(bitcode_gen_path)
syzdescribe_path = os.path.realpath(syzdescribe_path)
knowledge_path = os.path.realpath(knowledge_path)

name_script_path = os.path.realpath("./get_driver_name.py")
handler_script_path = os.path.realpath("./get_driver_handler.py")


# need trailing slash :joy:
driver_path = os.path.join(driver_path, '')

driver_realpath = os.path.join(source_base, driver_path)

os.system(f"cd {source_base} && make clean")
compile_code_with_retry(retries=5, command=f"make {driver_path} LLVM=1 -j{num_cores} 0<&-")

os.system(f"cd {driver_realpath} && go run {bitcode_gen_path}")

buildscript_path = os.path.join(driver_path, "build.sh")

compile_code_with_retry(retries=5)

analysis_config = {
  "bitcode": os.path.join(driver_realpath, "built-in.bc"),
  "knowledge": knowledge_path,
  "version": linux_version
}

analysis_config_path = os.path.join(tool_workdir, "syzdescribe_config.json")

with open(analysis_config_path, "w") as f:
    f.write(json.dumps(analysis_config))


syzdescribe_restructure_prompt = f"""
We would like to follow best coding practices. Please restructure any code I give you so that all the ioctl commands are directly dispatched
from that function, rather than calling other functions which handle the command
decisions. If there is no such dispatching, for example if there is only one command,
then wrap the relevant portion of the handler so that it still uses a case-switch
statement with case 0.

Finally, please make sure that when using a transfer function (copy_from_user or memdup_user)
on the third argument of the ioctl handler, that it occurs within each block. If it originally occurs
in a block preceding any handler logic please duplicate the call to also happen within the handler cases.
This may lead to duplicated calls of copy_from_user which do the same thing, but that's completely fine.

An example of this pattern is if I have
```
copy_from_user(object, userland pointer, offset);

switch(cmd){{
    case CASE_1:
        some_other_code

    ...
}}
```

It may also be the case that a function call results in a copy_from_user. You should also consider that.

When you see things like this, please also place a copy_from_user within the CASE_1 block in front of the some_other_code.

Moreover, please make sure that the logic for checking global state before dispatching a handler
occurs within each case block. I do not want to see a switch(cmd) inside an if statement, because it should be re-arranged in the opposite order.
Even though this means repeating a lot of code, it is best practice.

Pay attention that the value being used in any switch statements is not changed from what it
originally refers to. One possible mistake is replacing two similarly named variables with the other. Do not do this!

One more thing: make sure that your suggestions reference variables which are properly declared. Unless the variables they reference are defined in the scope of the file, you may not assume that the variable exists. So, you must reason about its type. Look for examples in other parts of the code which might aid in you declaring the variable correctly, and insert it where necessary in your changes. You may declare the variables to be on the stack or the heap, however necessary. 

You should start your analysis from the handler function which is exposed through some operation struct.
"""



generated_files, err = run_syzdescribe()

if err:
    print("failed after all retries!")
    configs = ["v5.12", "v6.1", "v6.6"]

    configs.remove(linux_version)

    for test_version in configs:
        linux_version = test_version
        print(f"trying version {linux_version} as a last ditch")
        knowledge_path = f"./config/knowledge-{linux_version}.json"

        syzdescribe_path = os.path.realpath(syzdescribe_path)
        knowledge_path = os.path.realpath(knowledge_path)

        os.system(f"cd {source_base} && make clean")
        compile_code_with_retry(retries=5, command=f"make {driver_path} LLVM=1 -j{num_cores} 0<&-")

        os.system(f"cd {driver_realpath} && go run {bitcode_gen_path}")

        buildscript_path = os.path.join(driver_path, "build.sh")

        compile_code_with_retry(retries=5)

        analysis_config = {
        "bitcode": os.path.join(driver_realpath, "built-in.bc"),
        "knowledge": knowledge_path,
        "version": linux_version
        }

        analysis_config_path = os.path.join(tool_workdir, "syzdescribe_config.json")

        with open(analysis_config_path, "w") as f:
            f.write(json.dumps(analysis_config))

        generated_files, err = run_syzdescribe()

        if not err:
            break

with open(output_file, "w") as of:
    for fname in generated_files:
        with open(fname) as f:
            of.write(f.read() + "\n")


