import os
import sys
import subprocess

script_path = os.path.join(os.path.dirname(__file__), "src", "run.py")

sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

if __name__ == "__main__":
    subprocess.run([sys.executable, script_path] + sys.argv[1:])
