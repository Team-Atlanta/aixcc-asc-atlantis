import os
import shutil
import subprocess
import hashlib

from llm_seed_gen.utils import error

class SeedGeneratorRunner:
    def __init__(self, seed_generator_scripts, workdir):
        self.python_cmd = 'python3'
        self.blob_file = f'{workdir}/blob.bin'
        self.seed_generator_scripts = seed_generator_scripts

    def _run_python_script(self, script, max_attempts=5):
        attempts = 0

        while attempts < max_attempts:
            try:
                subprocess.run([self.python_cmd, os.path.basename(script)], cwd=os.path.dirname(script), capture_output=True, text=True)
                if os.path.exists(self.blob_file) and os.path.getsize(self.blob_file) < 2 * 1024 * 1024:
                    return True
            except:
                attempts += 1

        return False

    def _compute_sha1(self, file):
        sha1 = hashlib.sha1()
        with open(file, 'rb') as f:
            while True:
                data = f.read(4096)
                if not data:
                    break
                sha1.update(data)
        return sha1.hexdigest()

    def _move_blob_to_output_dir(self, output_dir):
        sha1_hash = self._compute_sha1(self.blob_file)
        new_file_path = os.path.join(output_dir, sha1_hash)
        shutil.move(self.blob_file, new_file_path)

    def _run_one(self, script, output_dir):
        if not self._run_python_script(script):
            return False
        self._move_blob_to_output_dir(output_dir)
        return True

    def run(self, output_dir, nblobs):
        print(f'Generating {nblobs} blobs...')
        scripts = [self.seed_generator_scripts.git_commit_upgraded, self.seed_generator_scripts.test_harness_upgraded]
        for _ in range(nblobs):
            if not scripts:
                error.fatal('No working scripts to run')
                break
            if not self._run_one(scripts[0], output_dir):
                scripts.pop(0)
