import os 
import re

from ..llm import config as LLMConfig
from ..parser import LLMHarnessParser
from ..generator import *
from ..utils.logger import Log
from ..common.harness import Harness
from ..common.project import Project

def generate_byte_code(class_name, harness: Harness):
    generator = LLMByteHarnessGenerator()
    generator.class_name = class_name
    generator.code = harness.source_code
    byte_harness_code = generator.generate()
    
    return byte_harness_code

def generate_concolic_code(class_name, harness: Harness):
    generator = LLMConcolicHarnessGenerator()
    generator.class_name = class_name
    generator.code = harness.source_code
    string_harness_code = generator.generate()
    
    return string_harness_code

def generate_jazzer_code(class_name: str, harness: Harness, is_include_origin):
    threashold = 5
    it = 0

    # Try to generate valid protobuf harness
    while it < threashold:
        generator = LLMJazzerHarnessGenerator(temperature=0.3)
        generator.class_name = class_name
        generator.code = harness.source_code
        generator.is_included_origin = is_include_origin
        harness_code = generator.generate()
        if generator.is_valid:
            return harness_code
        it += 1
    
    return None

def generate_jazzerblob_code(class_name: str, harness: Harness):
    converter = JazzerBlobConverter()
    converter.file_path = '/work/tmp_blob'
    converter.target_class = harness.target_class
    converter.from_class_name = harness.class_name
    converter.to_class_name = class_name
    converter.code = harness.source_code
    code = converter.generate()
    return code

def generate_protoblob_code(class_name: str, harness: Harness):
    converter = ProtobufBlobConverter()
    converter.file_path = '/work/tmp_blob'
    converter.target_class = harness.target_class
    converter.from_class_name = harness.class_name
    converter.to_class_name = class_name
    converter.code = harness.source_code
    code = converter.generate()
    return code


def create_concolic_harness_files(output_dir, harness: Harness):
    # Create Concolic Harness File
    concolic_class_name = f'{harness.target_class}_Concolic'
    concolic_harness_code = generate_concolic_code(concolic_class_name, harness)
    concolic_file_path = os.path.join(output_dir, f'{concolic_class_name}.java')
    with open(concolic_file_path, 'w') as f:
        f.write(concolic_harness_code)
    Log.i(f'Generated Concolic Harness: {concolic_file_path}')


def create_protobuf_harness_files(output_dir, harness: Harness, is_include_origin):
    # Create Protobuf Harness File
    fuzz_class_name = f'{harness.target_class}_Fuzz'
    output_proto_file = f'{output_dir}/{fuzz_class_name}.proto'
    output_file = f'{output_dir}/{fuzz_class_name}.java'
    
    generator = LLMProtobufHarnessGenerator()
    generator.jazzer_code = harness.source_code
    generator.target_class_name = harness.target_class
    generator.main_class_name = fuzz_class_name
    generator.is_included_origin = is_include_origin
    harness_code = generator.generate()
    
    proto_generator = ProtoBufMultiTypeGenerator()
    proto_generator.argument_types = generator.arguments
    protobuf_code = proto_generator.generate()
    
    # Create Blob Generator File
    blob_harness = Harness()
    blob_harness.class_name = fuzz_class_name
    blob_harness.source_code = generator.harness_code
    blob_harness.target_class = harness.target_class
    blob_class_name = f'{harness.target_class}_BlobGenerator'
    blob_harness_code = generate_protoblob_code(blob_class_name, blob_harness)
    blob_file_path = os.path.join(output_dir, f'{blob_class_name}.java')

    with open(output_file, "w") as f:
        f.write(harness_code)
    Log.i(f'Generated Fuzz Harness: {output_file}')
    
    with open(output_proto_file, "w") as f:
        f.write(protobuf_code)
    Log.i(f'Generated Protobuf: {output_proto_file}')
    
    with open(blob_file_path, 'w') as f:
        f.write(blob_harness_code)
    Log.i(f'Generated Blob Harness: {blob_file_path}')

def create_jazzer_harness_files(output_dir, harness: Harness, is_include_origin, from_composite=False):
    # Create Jazzer Harness File
    if from_composite:
        fuzz_class_name = f'{harness.target_class}_CJazzerFuzz'
    else:
        fuzz_class_name = f'{harness.target_class}_JazzerFuzz'
    
    # Try to generate valid protobuf harness
    threashold = 5
    for _ in range(threashold):
        generator = LLMJazzerHarnessGenerator(temperature=0.3)
        generator.class_name = fuzz_class_name
        generator.code = harness.source_code
        generator.is_included_origin = is_include_origin
        fuzz_harness_code = generator.generate()
        if generator.is_valid:
            break
    
    if not generator.is_valid:
        Log.e(f'Invalid Jazzer Harness generated')
    
    fuzz_file_path = os.path.join(output_dir, f'{fuzz_class_name}.java')
    if fuzz_harness_code is None:
        Log.e(f'Failed to generate Jazzer Harness')
        return
    with open(fuzz_file_path, 'w') as f:
        f.write(fuzz_harness_code)
    Log.i(f'Generated Fuzz Harness: {fuzz_file_path}')

    # Create Blob Generator File
    blob_harness = Harness()
    blob_harness.class_name = fuzz_class_name
    blob_harness.source_code = generator.harness_code
    blob_harness.target_class = harness.target_class
    blob_class_name = f'{harness.target_class}_JazzerBlobGenerator'
    blob_harness_code = generate_jazzerblob_code(blob_class_name, blob_harness)
    blob_file_path = os.path.join(output_dir, f'{blob_class_name}.java')
    with open(blob_file_path, 'w') as f:
        f.write(blob_harness_code)
    Log.i(f'Generated Blob Harness: {blob_file_path}')

def create_composite_harness_files(output_dir, harness: Harness, is_include_origin):
    fuzz_class_name = f'{harness.target_class}_Fuzz'
    

    threashold = 5
    it = 0

    # Try to generate valid protobuf harness
    while it < threashold:
        # Try to create Protobuf Harness File
        generator = LLMProtobufHarnessGenerator()
        generator.jazzer_code = harness.source_code
        generator.target_class_name = harness.target_class
        generator.main_class_name = fuzz_class_name
        generator.is_included_origin = is_include_origin
        fuzz_harness_code = generator.generate()
        
        if generator.is_valid:
            # Create Protobuf Fuzz Harness File
            fuzz_file_path = os.path.join(output_dir, f'{fuzz_class_name}.java')  
            with open(fuzz_file_path, 'w') as f:
                f.write(fuzz_harness_code)
            
            Log.i(f'Generated Fuzz Harness: {fuzz_file_path}')

            # Create Protobuf File
            proto_generator = ProtoBufMultiTypeGenerator()
            proto_generator.argument_types = generator.arguments
            protobuf_code = proto_generator.generate()
            output_proto_file = f'{output_dir}/{fuzz_class_name}.proto'

            with open(output_proto_file, "w") as f:
                f.write(protobuf_code)
            Log.i(f'Generated Protobuf: {output_proto_file}')
            
            # Create Blob Generator File
            blob_harness = Harness()
            blob_harness.class_name = fuzz_class_name
            blob_harness.source_code = generator.harness_code
            blob_harness.target_class = harness.target_class
            blob_class_name = f'{harness.target_class}_BlobGenerator'
            blob_harness_code = generate_protoblob_code(blob_class_name, blob_harness)
            blob_file_path = os.path.join(output_dir, f'{blob_class_name}.java')
            with open(blob_file_path, 'w') as f:
                f.write(blob_harness_code)
            Log.i(f'Generated Blob Harness: {blob_file_path}')
            return

        it += 1
        
    # Create Jazzer Harness File as fallback
    create_jazzer_harness_files(output_dir, harness, is_include_origin, True)

def llm_processing(args):
    project_path = args.project
    harness_id = args.harnessid
    harness_format = args.format
    output_dir = args.output_dir
    is_include_origin = args.include_origin
        
    if 'AIXCC_LITELLM_HOSTNAME' not in os.environ or 'LITELLM_KEY' not in os.environ:
        raise Exception("AIXCC_LITELLM_HOSTNAME or LITELLM_KEY is not set")

    LLMConfig.base_url      = os.environ["AIXCC_LITELLM_HOSTNAME"]
    LLMConfig.api_key       = os.environ["LITELLM_KEY"] 
    LLMConfig.model         = os.environ.get("LITELLM_MODEL", LLMConfig.model)
    LLMConfig.temperature   = os.environ.get("LITELLM_TEMPERATURE", LLMConfig.temperature)
    LLMConfig.top_p         = os.environ.get("LITELLM_TOP_P", LLMConfig.top_p)
    LLMConfig.n             = os.environ.get("LITELLM_N", LLMConfig.n)
    LLMConfig.max_tokens    = os.environ.get("LITELLM_TOKENS", LLMConfig.max_tokens)
    
    Log.d(f'---------------------------------------------')
    Log.d(f'Harness Processor: LLM Processor')
    Log.d(f'Parsing project:   {project_path}')
    Log.d(f'Harness ID:        {harness_id}')
    Log.d(f'Output Format:     {harness_format}')
    Log.d(f'Output Directory:  {output_dir}')
    Log.d(f'---------------------------------------------')
    Log.d(f'Model:       {LLMConfig.model}')
    Log.d(f'Temperature: {LLMConfig.temperature}')
    Log.d(f'Top P:       {LLMConfig.top_p}')
    Log.d(f'N:           {LLMConfig.n}')
    Log.d(f'Max Tokens:  {LLMConfig.max_tokens}')
    
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
    
    # Parse Challenge Project
    project = Project(project_path)
    harness = LLMHarnessParser(project).get_harness(harness_id)
    
    # Generate Formatted Harness
    if harness_format == 'composite':
        create_composite_harness_files(output_dir, harness, is_include_origin)
    elif harness_format == 'jazzer':
        create_jazzer_harness_files(output_dir, harness, is_include_origin)
    elif harness_format == 'protobuf':
        create_protobuf_harness_files(output_dir, harness, is_include_origin)
    elif harness_format == 'concolic':
        create_concolic_harness_files(output_dir, harness)
    
