#!/usr/bin/env python3
import subprocess
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from cpgqls_client import CPGQLSClient, import_code_query

server_endpoint = "localhost:8000"
client = CPGQLSClient(server_endpoint)

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        data = {"message": "Hello, this is a GET request. Send a Joern query via POST."}
        self.wfile.write(json.dumps(data).encode())

    def single_query(self, data):
        joern_input_file = data.get("input")
        joern_query = data.get("query")
        if not joern_input_file:
            return {"status": "error", "message": "You need to provide the path for import"}
        joern_input_file.replace("\n","")
        query = import_code_query(joern_input_file)
        result = client.execute(query)
        print(result)
        if result['success']:
            result = client.execute(joern_query)
            print(result)
            return result
        else:
            return result

    def replace_parameters(self, script_path, params):
        with open(script_path, 'r') as file:
            script = file.read()
        for key, value in params.items():
            print(key)
            script = script.replace(f"<{key}>", value)
        return script   

    def script_query(self, data):
        joern_input_file = data.get("input")
        joern_query_path = data.get("queryPath")
        if not joern_input_file:
            return {"status": "error", "message": "You need to provide the path for import"}
        joern_input_file.replace("\n","")
        query = import_code_query(joern_input_file)
        result = client.execute(query)
        if result['success']:
            parameters=data.get("param")
            script=self.replace_parameters(joern_query_path,parameters)
            result = client.execute(script)
            print(result)
            return result
        else:
            return result

    def run_joern_graph(self, joern_input_file):
        try:
            query = import_code_query(joern_input_file)
            result = client.execute(query)
            print(result)
            if result['success']:
                joern_query ="project.path"
                result = client.execute(joern_query)
                print(result)
                result=result['stdout'].split('=')[-1]
                output_directory= result.replace('\n','')+"/out"
                cpgfile=result.replace('\n','')+"/cpg.bin"
                command = f'joern-export --out {output_directory}  --repr all --format dot {cpgfile}'
                process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = process.communicate()
                if process.returncode == 0:
                    return stdout.decode()
                else:
                    return {"status": "error", "message": f"Joern Error: {stderr.decode()}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def run_joezrn_javasrc(self, data):
        exclude_dirs = ', '.join(data["exclude"])
        output = data.get("output")
        input_file = data.get("input")
        dependent_jars = ', '.join(data["dependent_jars"])
        try:
            command = ['javasrc2cpg']
            if exclude_dirs:
                command += ['--exclude', exclude_dirs]
            if dependent_jars:
                command += ['--inference-jar-paths', dependent_jars]
            command += ['-o', output, input_file]

            try:
                print(command)
                result = subprocess.run(command, check=True, capture_output=True, text=True)
            except subprocess.CalledProcessError as e:
                return {"status": "error1", "message": str(e)}

            load_result = client.execute(f'importCpg("{output}")')
            print(load_result)
            parameters = data.get("param")
            joern_query_path = data.get("queryPath")
            script =self.replace_parameters(joern_query_path, parameters)
            result = client.execute(script)
            print(result)
            return result
        except Exception as e:
            return {"status": "error2", "message": str(e)}

    def graph_query(self, data):
        joern_input_file = data.get("input")
        result = self.run_joern_graph(joern_input_file)
        return {"status": "success", "data": result} if isinstance(result, str) else result

    def llm_poc(self, data):
        result = self.run_joezrn_javasrc(data)
        return {"status": "success", "data": result} if isinstance(result, str) else result

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error", "message": "No Content Found"}).encode())
            return

        post_data = self.rfile.read(content_length)
        try:
            request_data = json.loads(post_data.decode())
        except json.JSONDecodeError:
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error", "message": "Invalid JSON"}).encode())
            return

        if self.path == '/single_query':
            response = self.single_query(request_data)
        elif self.path == '/script_query':
            response = self.script_query(request_data)
        elif self.path == '/graph_query':
            response = self.graph_query(request_data)
        elif self.path == '/llm_poc':
            response = self.llm_poc(request_data)
        else:
            response = {"status": "error", "message": "Invalid endpoint"}
            self.send_response(404)
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            return

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())

def run(server_class=HTTPServer, handler_class=SimpleHTTPRequestHandler, port=9000):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f"Server running on port {port}...", flush=True)
    httpd.serve_forever()

if __name__ == '__main__':
    run()
