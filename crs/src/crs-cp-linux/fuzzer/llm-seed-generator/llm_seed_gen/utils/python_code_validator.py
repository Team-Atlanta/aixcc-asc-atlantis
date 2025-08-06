import subprocess
import os


class PythonCodeValidator:
    def __init__(self):
        self.python_cmd = 'python3'
        self.blob_file = f'blob.bin'

    def run_code(self, python_file_name, python_code, verify_cnt=5, timeout_retry=5):
        attempt = 0

        while True:
            try:
                blob_file = os.path.join(os.path.dirname(python_file_name), self.blob_file)
                with open(python_file_name, 'w') as f:
                    f.write(python_code)
                for _ in range(verify_cnt):
                    if os.path.exists(blob_file):
                        os.remove(blob_file)

                    process = subprocess.run([self.python_cmd, os.path.basename(python_file_name)], cwd=os.path.dirname(python_file_name), capture_output=True, text=True, timeout=30)
                    if process.returncode != 0:
                        raise Exception(process.stderr)
                    if not os.path.exists(blob_file):
                        return 'blob.bin was not created. The blob file name must be blob.bin'
                    blob_size = os.path.getsize(blob_file)
                    if blob_size == 0:
                        return 'blob.bin was empty. Blob file must not be empty'
                    if blob_size >= 2 * 1024 * 1024:
                        error_msg = f'blob.bin is too large({blob_size} bytes). The blob file must be under 2MB'
                        return error_msg
                return None
            except subprocess.TimeoutExpired as e:
                attempt += 1
                if attempt >= timeout_retry:
                    return str(e)
            except Exception as e:
                return str(e)
