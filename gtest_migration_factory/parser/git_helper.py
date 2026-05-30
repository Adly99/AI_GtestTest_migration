import subprocess
import os
import sys

def get_repo_root(project_root=None):
    """
    Returns the absolute path to the root of the git repository.
    Falls back to project_root or current working directory if not in a git repo.
    """
    cwd = project_root if project_root else os.getcwd()
    try:
        root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd,
            stderr=subprocess.DEVNULL
        ).decode().strip()
        return os.path.abspath(root)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return os.path.abspath(cwd)

def is_git_repo(project_root=None):
    """Checks if the project root is part of a git repository."""
    cwd = project_root if project_root else os.getcwd()
    try:
        subprocess.check_call(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=cwd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def get_modified_files(project_root=None):
    """
    Returns list of modified or untracked C++ files (.h, .hpp, .cpp, .cc).
    If git is not available or the path is not a git repo, lists all C++ files
    in the project root recursively.
    """
    cwd = os.path.abspath(project_root if project_root else os.getcwd())
    cpp_extensions = (".h", ".hpp", ".cpp", ".cc", ".cxx", ".hh")

    if not is_git_repo(cwd):
        # Fallback: scan directory recursively for C++ files
        cpp_files = []
        for root, _, files in os.walk(cwd):
            for file in files:
                if file.lower().endswith(cpp_extensions):
                    cpp_files.append(os.path.join(root, file))
        return cpp_files

    # Git commands to get modified, added, unstaged, and untracked files
    try:
        # Get tracked modified/added files (staged & unstaged)
        cmd_diff = ["git", "diff", "--name-only", "HEAD"]
        diff_files = subprocess.check_output(cmd_diff, cwd=cwd, stderr=subprocess.DEVNULL).decode().splitlines()

        # Get untracked files
        cmd_untracked = ["git", "status", "--porcelain"]
        status_lines = subprocess.check_output(cmd_untracked, cwd=cwd, stderr=subprocess.DEVNULL).decode().splitlines()
        
        untracked_files = []
        for line in status_lines:
            if line.startswith("?? "):
                untracked_files.append(line[3:])

        all_files = set(diff_files + untracked_files)
        repo_root = get_repo_root(cwd)

        # Map relative git paths to absolute paths, filtering for C++ extensions
        result = []
        for f in all_files:
            abs_path = os.path.abspath(os.path.join(repo_root, f))
            # Ensure the file is actually inside our target project root and is a C++ file
            if abs_path.startswith(cwd) and abs_path.lower().endswith(cpp_extensions) and os.path.exists(abs_path):
                result.append(abs_path)
        return sorted(result)

    except (subprocess.CalledProcessError, FileNotFoundError):
        # Graceful fallback on error
        cpp_files = []
        for root, _, files in os.walk(cwd):
            for file in files:
                if file.lower().endswith(cpp_extensions):
                    cpp_files.append(os.path.join(root, file))
        return cpp_files
