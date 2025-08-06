from ..common.project import Project
from ..common.harness import Harness
from ..parser import DumbJavaProjectParser, LLMHarnessParser
from ..generator import *
from ..utils.logger import Log

import os

def throw_error(msg: str):
    Log.e(msg)
    exit(1)

def create_jazzer_harness(output_dir: str, harness: Harness):
    class_name = f'{harness.target_class}_Fuzz'
    generator = FakeFileStreamGenerator()
    generator.imports.append('com.code_intelligence.jazzer.api.FuzzedDataProvider')
    generator.main_class_name = class_name
    generator.main_method_signature =  f'void fuzzerTestOneInput(FuzzedDataProvider provider)'
    generator.target_code = harness.source_code
    generator.target_arguments = ["provider.consumeString(100)" for _ in harness.arguments]
    generator.target_invocations.append(f'{harness.target_class}.fuzzerTestOneInput(null)')
    
    Log.d(f'Generating harness: {class_name}.java')
    with open(os.path.join(output_dir, f'{class_name}.java'), 'w') as f:
        f.write(generator.generate())
    
    Log.i(f'Generated harness: {class_name}.java')
    
def create_probuf_harness(output_dir: str, harness: Harness):
    class_name = f'{harness.target_class}_Fuzz'
    generator = FakeFileStreamGenerator()
    generator.imports.append('com.code_intelligence.jazzer.mutation.annotation.NotNull')
    generator.imports.append('ourfuzzdriver.HarnessInputOuterClass')
    generator.main_class_name = class_name
    generator.main_method_signature =  f'void fuzzerTestOneInput(@NotNull HarnessInputOuterClass.HarnessInput input)'
    generator.target_code = harness.source_code
    
    generator.target_arguments = [f'new String(input.getField{i + 1}().toByteArray())' for i in range(len(harness.arguments))]
    generator.target_invocations.append(f'{harness.target_class}.fuzzerTestOneInput(null)')
    generator.transform_input_code = f'{class_name}.fuzzerTestOneInput(HarnessInputOuterClass.HarnessInput.parseFrom(data));'
    
    Log.d(f'Generating harness: {class_name}.java')
    with open(os.path.join(output_dir, f'{class_name}.java'), 'w') as f:
        f.write(generator.generate())
    Log.i(f'Generated harness: {class_name}.java')
    
    Log.d(f'Generating protobuf: {class_name}.proto')
    generator = ProtoBufByteGenerator()
    generator.target_arguments = harness.arguments
    with open(os.path.join(output_dir, f'{class_name}.proto'), 'w') as f:
        f.write(generator.generate())
    Log.i(f'Generated protobuf: {class_name}.proto')

def create_blob_harness(output_dir, harness: Harness):
    class_name = harness.target_class
    generator = BlobGenerator()
    generator.main_class_name = f'{class_name}_Fuzz'
    generator.target_class = class_name
    generator.generate()
    with open(os.path.join(output_dir, f'{class_name}_Fuzz.java'), 'w') as f:
        f.write(generator.generate())
    Log.i(f'Generated blob harness: {class_name}_Fuzz.java')

def java_processing(args):
    project_path = args.project
    harness_id = args.harnessid
    harness_format = args.format
    output_dir = args.output_dir
    
    Log.d(f'Parsing project: {project_path}')
    Log.d(f'Harness ID: {harness_id}')
    Log.d(f'Output Format: {harness_format}')
    Log.d(f'Output Directory: {output_dir}')
    
    project = Project(project_path)
    
    # Parser: 'java'
    # if parser_type == 'java':
    parser = DumbJavaProjectParser(project)
    
    try:
        harness = parser.get_harness(harness_id)
    except Exception as e:
        throw_error(f'Failed to parse:\n{e}')

    Log.d(f'Generated harness.')
    Log.d(f'File path: {harness.file_path}')
    Log.d(f'Target class: {harness.target_class}')
    Log.d(f'Arguments count: {len(harness.arguments)}')
            
    # Output Format: 'jazzer', 'protobuf', blob
    Log.d(f'Creating harness in {harness_format} format.')
    if harness_format == 'jazzer':
        create_jazzer_harness(output_dir, harness)
    elif harness_format == 'protobuf':
        create_probuf_harness(output_dir, harness)
    elif harness_format == 'blob': # deprecated
        create_blob_harness(output_dir, harness)
    else:
        Log.e('Invalid format.')
        exit(1)
