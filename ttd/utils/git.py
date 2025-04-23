import subprocess
from typing import Dict, Optional

def get_git_metadata() -> Dict[str, Optional[str]]:
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
        branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"]).decode().strip()
        repo = subprocess.check_output(["git", "config", "--get", "remote.origin.url"]).decode().strip()
        return {
            "git_commit": commit,
            "git_branch": branch,
            "git_repo": repo
        }
    except Exception:
        return {
            "git_commit": None,
            "git_branch": None,
            "git_repo": None
        }