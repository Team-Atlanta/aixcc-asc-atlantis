import sys

from aider.main import main

def caller(target="", model="--4", key="", commands=[]):
    return main(
        argv=[
            target,
            model,
            f"--openai-api-key={key}",
            "--map-tokens=0",
            "--no-auto-commits",
            "--retrieve-edits"
        ],
        input=None,
        output=None,
        force_git_root=None,
        cmds=commands
    )

if __name__ == "__main__":
    edits = caller(
        target="../cp-linux-exemplar-source/drivers/CADET-00001/service.c",
        key="your-openai-api-key",
        commands=[
            "fix the stack buffer overflow vulnerability",
        ]
    )

    print(edits)