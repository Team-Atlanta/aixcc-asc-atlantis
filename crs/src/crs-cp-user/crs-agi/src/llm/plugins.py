import ast
import atexit
import os
import rich
import shutil
import subprocess
import sys
import tempfile
import json
import shlex

from abc import abstractmethod
from pathlib import Path
from loguru import logger

from .tools import get_tool_signatures
from .errors import PluginErrorGivingUp, PluginErrorRetry, PluginErrorTimeout, PluginSuccess

ROOT = Path(os.path.dirname(__file__))


class Plugin:
    name: str
    plugin_id: int = 1111

    def __init__(self, workspace):
        self.workspace = workspace if workspace else Workspace()
        self.plugin_id = Plugin.plugin_id

        Plugin.plugin_id += 1

    def store_schema(self):
        # store a schema to the workspace
        log = self.workspace.history / f"{self.name}.schema"
        with open(log, "w") as fd:
            json.dump(self.get_openai_schema(), fd, indent=4)

    @abstractmethod
    def get_openai_schema(self):
        """Return a function call schema."""
    @abstractmethod
    def __call__(self, *args, **kw):
        """Call the plugin."""


class Workspace:
    def __init__(self, root=None, delete=False):
        # workspace
        #  - tools/     : python tools for LLM
        #  - tmp/       : tmp
        #  - history/   : main-runid.py
        #  - cp/        : ln to cp
        #  - main.py    : entry point

        if root is None:
            self.workspace = Path(tempfile.mkdtemp(prefix="workspace-")).resolve()
        else:
            self.workspace = Path(root).resolve()
        self.delete = delete

        self.populate()

        logger.info(f"Workspace: {self.workspace} (delete={self.delete})")

        atexit.register(self.__at_exit)

    def populate(self):
        self.tmp = self.workspace / "tmp"
        self.history = self.workspace / "history"
        self.logfile = self.workspace / "history" / "log.txt"

        os.mkdir(self.tmp)
        os.mkdir(self.history)

    def copyfile(self, src, dst):
        if not Path(dst).is_absolute():
            dst = self.workspace / dst
        shutil.copy(src, dst)

    def copytree(self, src, dst):
        if not Path(dst).is_absolute():
            dst = self.workspace / dst
        shutil.copytree(src, dst)

    def ln(self, src, dst):
        dst = Path(dst)
        src = Path(src)
        if not src.is_absolute():
            src = self.get_path(src)
        if not dst.is_absolute():
            dst = self.get_path(dst)

        assert not dst.exists()

        os.symlink(src, dst)

    def clean_up(self):
        if self.workspace.exists():
            shutil.rmtree(self.workspace)

    def __at_exit(self):
        if self.delete:
            self.log(f"Deleting {self.workspace}", console=True)
            self.clean_up()
        else:
            self.log(f"Workspace is saved @{self.workspace}", console=True)

    def get_path(self, pn):
        return self.workspace / pn

    def get_cwd(self):
        return self.workspace

    def __prepare_run(self, args, cwd):
        cwd = Path(cwd or self.get_cwd())
        if not cwd.is_absolute():
            cwd = self.get_path(cwd)

        cmdinfo = args
        if isinstance(cmdinfo, list):
            cmdinfo = " ".join(args)
        self.log("Run: '%s' (in %s)" % (cmdinfo, cwd.relative_to(self.workspace)), console=True)

        return cwd

    def run(self, args, cwd=None, shell=False):
        cwd = self.__prepare_run(args, cwd)
        try:
            result = subprocess.run(args, cwd=cwd, stdin=subprocess.DEVNULL,
                                    check=True, shell=shell)
            return result.returncode == 0
        except subprocess.CalledProcessError:
            return False
        except FileNotFoundError:
            return False

    def run_with_capture(self, args, cwd=None, shell=False):
        p = subprocess.Popen(
            args,
            shell=False,
            stdin=None,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=self.__prepare_run(args, cwd),
            close_fds=True)
        out, _ = p.communicate()

        out = out.decode('utf-8', errors='backslashreplace')

        return (p.returncode, out)

    def log(self, msg, console=False):
        if console:
            logger.info(f"Workspace: {msg}")
        with open(self.logfile, "a+") as fd:
            fd.write(msg)
            fd.write("\n")


def execute_with_timeout(args, cwd, timeout, env=None):
    if env is None:
        env = os.environ

    args = ["timeout", "-v", str(timeout)] + args
    p = subprocess.Popen(
        args,
        shell=False,
        stdin=None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=cwd,
        env=env,
        close_fds=True)
    out, err = p.communicate()

    out = out.decode('utf-8', errors='backslashreplace')
    err = err.decode('utf-8', errors='backslashreplace')

    return (out, err)


def combine_out_err(out, err):
    # plain stdout
    if len(err) == 0:
        return out

    # combine stdout and stderr for chatgpt
    return f"# stdout:\n{out}\n\n# stderr:\n{err}\n"


def add_print_to_expression(code):
    # Parse the input code into an AST
    parsed_code = ast.parse(code)

    # Check if the last node in the body is an expression and not a print statement
    if isinstance(parsed_code.body[-1], ast.Expr):
        last_expr = parsed_code.body[-1].value
        if not (isinstance(last_expr, ast.Call)
                and isinstance(last_expr.func, ast.Name)
                and last_expr.func.id == 'print'):
            # Create a print statement for the last expression
            print_stmt = ast.Expr(value=ast.Call(
                func=ast.Name(id='print', ctx=ast.Load()),
                args=[last_expr],
                keywords=[]
            ))

            # Replace the last expression with the print statement
            parsed_code.body[-1] = print_stmt

    # Convert the modified AST back to source code
    return ast.unparse(parsed_code)


def ensure_module_imported(code, module):
    # Parse the input code into an AST
    parsed_code = ast.parse(code)

    # Check if a module is already imported
    for node in parsed_code.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == module:
                    return code
        elif isinstance(node, ast.ImportFrom):
            if node.module == 'tools':
                return code

    # the module is not imported, so we add the import statement
    module_import = ast.Import(names=[ast.alias(name=module, asname=None)])

    # Add the import statement at the beginning of the code
    parsed_code.body.insert(0, module_import)

    # Convert the modified AST back to source code
    return ast.unparse(parsed_code)


class ExecutePython(Plugin):
    name = "execute_python"

    def __init__(self, workspace=None, tools=None, packages=None):
        super().__init__(workspace)

        global ROOT

        self.runid = 0
        self.tools = tools or ROOT / "tools"
        self.terminated = False
        self.packages = packages

        assert self.tools.exists()

        self.workspace.copytree(self.tools, "tools/")

    def get_description(self):
        interpreter = f"python-{sys.version_info.major}.{sys.version_info.minor}"
        packages = self.get_packages()
        tools = "\n".join(get_tool_signatures())

        if len(tools) == 0:
            tools = "Not available."

        return f"""\
Execute the code in `{interpreter}`. Don't forget to import necessary packages \
(listed below) and do `import tools` before invoking the functions below. \
The stdout will be returned back to LLM so *explicitly* print out what you'd like to know.

# Packages:
{packages}

# Special utilities can be accessed via `tools`:
{tools}
"""

    def get_packages(self):
        if self.packages is None:
            return "Standard library."
        else:
            return "\n".join(self.packages)

    @abstractmethod
    def get_openai_schema(self):
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.get_description(),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "The Python code to execute (required)."},
                        "timeout": {
                            "type": "number",
                            "description": """\
    Expected timeout in seconds. It raises `TimeoutError` if it doesn't terminate on time. \
    Recommend in a range <60 seconds. Do not use more than 5 minutes, and use the default \
    value whenever possible. You can always try it again with a larger timeout if it takes \
    more than the expected time (default: 20 sec)."""},
                    },
                    "required": ["code"],
                },
            }
        }

    def backup_main(self):
        dst = self.workspace.history / ("main-%03d-%03d.py" % (self.plugin_id, self.runid))

        self.workspace.copyfile(self.get_main(), dst)
        self.runid += 1

    def run(self, code, timeout=5):
        assert not self.terminated

        pn = self.get_main()
        with open(pn, "w") as fd:
            fd.write(self.preprocess_code(code))
            fd.write("\n")
        self.backup_main()

        # main.py will be located under the top of the workspace/
        # but will be executed workspace.get_cwd() (e.g., cp/ for CRS).
        # it allows main.py to import tools
        env = os.environ.copy()
        env["PYTHONPATH"] = self.workspace.get_path(".")

        return execute_with_timeout(["python3", pn],
                                    cwd=self.workspace.get_cwd(),
                                    timeout=timeout,
                                    env=env)

    @abstractmethod
    def __call__(self, code, timeout=5):
        (out, err) = self.run(code, timeout)
        return combine_out_err(out, err)

    def preprocess_code(self, code):
        try:
            # fix1: add 'print' to the code that ends with an expression
            code = add_print_to_expression(code)

            # fix2: ensure 'tools' is always available in the python code
            code = ensure_module_imported(code, "tools")

            # TODO simple import errors
        except Exception as e:
            logger.warning(f"ERROR: parsing error: {e}")
            pass

        return code

    def get_main(self):
        return self.workspace.get_path("main-%03d.py" % self.plugin_id)


class ExecuteShell(Plugin):
    name = "execute_shell"

    def __init__(self, workspace=None):
        super().__init__(workspace)

        self.runid = 0

    @abstractmethod
    def get_description(self):
        return f"""\
Execute the shell code in `/usr/bin/bash`. The `stdout` and `stderr` of \
the shell script will be returned after the execution.
"""

    @abstractmethod
    def get_openai_schema(self):
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.get_description(),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "The bash code to execute (required)."},
                        "timeout": {
                            "type": "number",
                            "description": """\
    Expected timeout in seconds. It raises a TERM signal if it doesn't terminate on time. \
    Recommend in a range <60 seconds. Do not use more than 5 minutes, and use the default \
    value whenever possible. You can always try it again with a larger timeout if it takes \
    more than the expected time (default: 5 sec)."""},
                    },
                    "required": ["code"],
                },
            }
        }

    def backup_script(self):
        dst = self.workspace.history / ("script-%03d-%03d.sh" % (self.plugin_id, self.runid))

        self.workspace.copyfile(self.get_script(), dst)
        self.runid += 1

    def run(self, script, timeout=5):
        pn = self.get_script()
        with open(pn, "w") as fd:
            fd.write(self.preprocess_script(script))
            fd.write("\n")
        self.backup_script()

        return execute_with_timeout(["/usr/bin/bash", pn],
                                    cwd=self.workspace.get_cwd(),
                                    timeout=timeout)

    @abstractmethod
    def __call__(self, code, timeout=5):
        (out, err) = self.run(code, timeout)
        return combine_out_err(out, err)

    def preprocess_script(self, script):
        return script

    def get_script(self):
        return self.workspace.get_path("script-%03d.sh" % self.plugin_id)


class WorkspaceTool(Plugin):
    description = "N/A"
    params = None

    def __init__(self, workspace=None):
        super().__init__(workspace)

    @abstractmethod
    def get_openai_schema(self):
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.get_description(),
                "parameters": self.get_parameters(),
            }
        }

    @abstractmethod
    def get_description(self):
        return self.description

    @abstractmethod
    def get_parameters(self):
        if self.params is None:
            return no_param()
        return self.params

    @abstractmethod
    def run(self, **args):
        pass

    @abstractmethod
    def __call__(self, **args):
        self.workspace.log(f"Tool: {self.name}({args})")
        return self.run(**args)


def no_param():
    return {
        "type": "object",
        "properties": {}
    }

class TmpdirPlugin(WorkspaceTool):
    name = "tmpdir"
    description = "Returns a tmp directory in the workspace (no argument)."

    @abstractmethod
    def run(self, **args):
        return str(self.workspace.tmp)


class CWDPlugin(WorkspaceTool):
    name = "cwd"
    description = "Returns a current working directory in the workspace (no argument)."

    @abstractmethod
    def run(self, **args):
        return str(self.workspace.get_cwd())


def get_workspace_plugins(workspace):
    return [TmpdirPlugin(workspace),
            CWDPlugin(workspace)]


class GivingUpPlugin(WorkspaceTool):
    name = "session_giving_up"
    description = """\
Giving up the current session. It will terminate the execution. \
Call it when it is absolutely necessary as a last resort."""
    params =  {
        "type": "object",
        "properties": {
            "reason": {
                "type": "string",
                "description": "Concise reason to giving up."},
        },
        "required": ["reason"]
    }

    @abstractmethod
    def run(self, **args):
        raise PluginErrorGivingUp(args.get("reason", "Unknown."))


class RetryPlugin(WorkspaceTool):
    name = "session_retry"
    description = """\
Retry the session to achieve the goal once again. It will terminate the execution, \
and restart with the summary of the past session and reason to retry. Perhaps, \
The reason might contain some hints or insights to achieve the goal in the next session. \
Call it when it is absolutely necessary as a last resort."""

    params =  {
        "type": "object",
        "properties": {
            "reason": {
                "type": "string",
                "description": "Concise reason for retry. It should contain new hints or insights for the next session"},
            "summary": {
                "type": "string",
                "description": "Summary of what was tried and their results. The summary will be passed to the next session."},
        },
        "required": ["reason", "summary"]
    }

    @abstractmethod
    def run(self, **args):
        raise PluginErrorRetry(
            reason=args.get("reason", "Unknown."),
            summary=args.get("summary", "Unknown."))


class SuccessPlugin(WorkspaceTool):
    name = "session_success"
    description = """\
It indicates that the defined goal is indeed achieved, so return the control back to the user. \
Call it only when you absolutely think the goal is properly achieved."""
    params =  {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": "Concise summary of what's tried, and directly answer what the user asked."},
        },
        "required": ["summary"]
    }

    @abstractmethod
    def run(self, **args):
        raise PluginSuccess(args.get("summary", "Unknown."))


def get_mentalcare_plugins(workspace):
    return [GivingUpPlugin(workspace),
            RetryPlugin(workspace),
            SuccessPlugin(workspace)]
