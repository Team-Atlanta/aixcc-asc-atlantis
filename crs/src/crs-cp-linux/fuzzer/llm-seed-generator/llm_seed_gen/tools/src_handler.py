import os


class SourceHandler:
    """
        A handler for reading files and listing directories in the Linux kernel source tree.

        Methods:
        - read_file(file_path): Reads the content of a file given its relative path from the root of the Linux kernel source.
        - list_directory(dir_path): Lists the contents of a directory given its relative path from the root of the Linux kernel source.
        """

    def __init__(self, src_dir_path):
        self.src_dir_path = src_dir_path

    def read_file(self, file_path):
        """
                Reads the content of a file given its relative path from the root of the Linux kernel source.

                Parameters:
                file_path (str): The relative path to the file from the root of the Linux kernel source.

                Returns:
                str: The content of the file if it exists, otherwise "File not found".
                """
        try:
            with open(f'{self.src_dir_path}/{file_path}', 'r') as file:
                return file.read()
        except:
            return f'File not found.'

    def get_read_file_tool(self):
        return self.read_file, {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": self.read_file.__doc__,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "The relative path to the file from the root of the Linux kernel source.",
                        }
                    },
                    "required": ["file_path"],
                },
            }
        }

    def list_directory(self, dir_path):
        """
                Lists the contents of a directory given its relative path from the root of the Linux kernel source.

                Parameters:
                dir_path (str): The relative path to the directory from the root of the Linux kernel source.

                Returns:
                str: The result of the ls command if the directory exists, otherwise "Directory not found".
                """
        absolute_dir_path = f'{self.src_dir_path}/{dir_path}'
        if os.path.isdir(absolute_dir_path):
            return "\n".join(os.listdir(absolute_dir_path))
        else:
            return f'Directory not found.'

    def get_list_directory_tool(self):
        return self.list_directory, {
            "type": "function",
            "function": {
                "name": "list_directory",
                "description": self.list_directory.__doc__,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "dir_path": {
                            "type": "string",
                            "description": "The relative path to the directory from the root of the Linux kernel source.",
                        }
                    },
                    "required": ["dir_path"],
                },
            }
        }
