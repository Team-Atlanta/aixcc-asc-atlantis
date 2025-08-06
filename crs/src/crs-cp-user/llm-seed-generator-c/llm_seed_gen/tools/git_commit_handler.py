from git import Repo


class GitCommitHandler:
    def __init__(self, repo_path):
        self.repo_path = repo_path
        self.repo = Repo(repo_path)

    def get_all_commit_hashes(self):
        commits = list(self.repo.iter_commits())
        commit_hashes = [commit.hexsha for commit in commits]
        return commit_hashes

    def get_oneline_log(self):
        """
        Get the --oneline log of all commits in the given repository.

        Returns:
        str: A string containing the --oneline log of all commits.
        """
        git_cmd = self.repo.git
        oneline_log = git_cmd.log('--oneline')
        return oneline_log

    def get_get_oneline_log_tool(self):
        return self.get_oneline_log, {
            "type": "function",
            "function": {
                "name": "get_oneline_log",
                "description": self.get_oneline_log.__doc__,
            }
        }

    def fetch_diff(self, commit_hash):
        """
        Fetch the diff between a given commit and its parent commit.

        Parameters:
        commit_hash (str): The hash of the commit for which the diff is to be fetched.

        Returns:
        str: A string representing the diff between the commit and its parent.
            Returns None if an error occurs.

        The diff is formatted in a unified diff format, with each change represented as:
        Commit: commit_hash
        --- old_path
        +++ new_path
        followed by the diff data.
        """
        try:
            diff_data = f'Commit: {commit_hash}\n'

            commit = self.repo.commit(commit_hash)
            # Assume single parent
            parent_commit = commit.parents[0]

            diffs = parent_commit.diff(commit, create_patch=True)

            for diff in diffs:
                old_path = diff.a_path
                new_path = diff.b_path
                data = diff.diff.decode('utf-8')
                diff_data += f'--- {old_path}\n+++ {new_path}\n{data}'

            return diff_data
        except:
            return f'[Error] Commit {commit_hash} not found'

    def get_fetch_diff_tool(self):
        return self.fetch_diff, {
            "type": "function",
            "function": {
                "name": "fetch_diff",
                "description": self.fetch_diff.__doc__,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "commit_hash": {
                            "type": "string",
                            "description": "The hash of the commit for which the diff is to be fetched.",
                        }
                    },
                    "required": ["commit_hash"],
                },
            }
        }
