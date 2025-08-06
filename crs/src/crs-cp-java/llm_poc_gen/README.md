# vuli

vuli is a tool to generate PoVs including harness_id, sanitizer_id and blobs.
vuli uses llm, static taint analysis to infer values that trigger vulnerabilities.

## prerequisite

### joern

joern should be available. Please install joern and give joern path to the tool with option --joern_dir

### cp

cp should be available. Please install cp and build them. And then give the path to the tool with opeion --cp_dir

### gpt4-o

gpt4-o should be avilable. Please specify your api key as environment variable 'LITELLM_KEY'

## usage

`LITELLM_KEY="..." python -m vuli.main --cp_dir=...`

Optionally, you can set your joern path with `--joern-dir=...` option. Without this, this tool uses joern family tools in the PATH.
Optionally, you can use --no-reuse option if you do not want to reuse result from `output/blackboard`.
Especially, in the CRS System, `--no-reuse` must be set.

## result

vuli stores every interim result into `output/blackboard`. After finish, you can find "result" key in the result file which is the result whose element has harness_id, sanitizer_id and blobs. Note that, all byte data is encoded in base64 and stored on the blackboard. Therefore, please ensure to decode it from base64 before using it.

## limitation

So far, integer overflow is not a target of vuli.

## evaluation

|harness|result|fail reason|
|---|---|---|
|1|O||
|2|X|Integer Overflow|
|3|O||
|4|O||
|5|O||
|6|O||
|7|O||
|8|O||
|9|O||
|10|O||
|11|O||
|12|O||
|13|X|Integer Overflow|
|14|X|Fail to generate headers for multi-part/form|