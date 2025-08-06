import sys
import subprocess

def run_joern_command(command):
    """
    Runs a command in the Joern CLI and returns the output.
    """
    try:
        result = subprocess.run(['joern'] + command, capture_output=True, text=True)
        if result.stderr:
            print("Error:", result.stderr)
        return result.stdout
    except Exception as e:
        print(f"Failed to run command: {command}. Error: {str(e)}")
        return None

def import_project(project_path):
    """
    Imports a project into Joern.
    """
    return run_joern_command(['--script', f'importCode("{project_path}")'])

def query_jenkins_functions():
    """
    Queries for Jenkins-related functions in test files.
    """
    query = """
    cpg.file.name.l.filter(_.contains("test")).flatMap { file =>
      cpg.method.file(file).name("jenkins*").parameter.l.map(p => p.code)
    }.mkString("\n")
    """
    return run_joern_command(['--script', query])

def main():
    if len(sys.argv) < 2:
        print("Usage: python script_name.py <path_to_project>")
        sys.exit(1)

    project_path = sys.argv[1]

    # Import the project into Joern
    print("Importing the project...")
    print(import_project(project_path))
    
    # Query Jenkins related functions in the imported project
    print("Querying Jenkins functions...")
    jenkins_functions = query_jenkins_functions()
    print("Jenkins Functions Found:")
    print(jenkins_functions)

if __name__ == "__main__":
    main()

