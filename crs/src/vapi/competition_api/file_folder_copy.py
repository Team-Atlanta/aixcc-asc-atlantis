import os
from pathlib import Path
import subprocess

# rsync -a is both faster than shutil.copytree() and (more importantly)
# more reliable than cp -r in the flaky /crs_scratch filesystem

def copy_file(src: str | os.PathLike, dest: str | os.PathLike) -> None:
    subprocess.run(['rsync', '-rlptDE', str(src), str(dest)])

def copy_folder(src: str | os.PathLike, dest: str | os.PathLike) -> None:
    subprocess.run(['rsync', '-rlptDE', str(src) + '/.', str(dest)])
