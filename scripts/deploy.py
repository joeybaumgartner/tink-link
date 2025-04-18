import os
import shutil
import gzip
import fnmatch

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEPLOY_DIR = os.path.join(PROJECT_ROOT, "deploy")
WEB_DIR_NAME = "static"

# File extensions that should be gzipped if under the web folder. 
# Hard-to-compress files like jpeg, png, etc should be excluded
WEB_EXTENSIONS = [".html", ".css", ".js", ".json", ".svg", ".txt"]

# These are specific files that we want to skip compression
COMP_IGNORE_PATTERNS = [

]

# Glob-style patterns to ignore (relative to project root). These will not be copied to DEPLOY_DIR
IGNORE_PATTERNS = [

    ".git",                 # VCS
    ".gitignore",           # VCS
    "__pycache__",          # Python cache
    ".vscode",              # Editor settings
    "*.md",                 # Markdown files
    "*.pyc",                # Compiled Python files
    "images",               # Images folder
    "deploy",               # Output folder
    "PCB",                  # PCB folder
    "scripts",              # scripts folder
]

def should_compress(file_path):
    return os.path.splitext(file_path)[1] in WEB_EXTENSIONS and not is_comp_ignored(file_path)

def is_ignored(rel_path):
    rel_path = rel_path.replace(os.sep, "/")  # Normalize for pattern matching
    for pattern in IGNORE_PATTERNS:
        if fnmatch.fnmatch(rel_path, pattern):
            return True
        # Check each part of the path to match folder ignores like "__pycache__"
        parts = rel_path.split("/")
        for part in parts:
            if fnmatch.fnmatch(part, pattern):
                return True
    return False

def is_comp_ignored(rel_path):
    rel_path = rel_path.replace(os.sep, "/")  # Normalize for pattern matching
    for pattern in COMP_IGNORE_PATTERNS:
        if fnmatch.fnmatch(rel_path, pattern):
            return True
        # Check each part of the path to match folder ignores like "__pycache__"
        parts = rel_path.split("/")
        for part in parts:
            if fnmatch.fnmatch(part, pattern):
                return True
    return False

def clean_deploy_dir():
    if os.path.exists(DEPLOY_DIR):
        shutil.rmtree(DEPLOY_DIR)
    os.makedirs(DEPLOY_DIR)

def copy_and_process_files():
    for dirpath, dirnames, filenames in os.walk(PROJECT_ROOT):
        rel_dir = os.path.relpath(dirpath, PROJECT_ROOT)
        if is_ignored(rel_dir):
            dirnames[:] = []  # Skip walking into subdirectories
            continue

        for filename in filenames:
            src_path = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(src_path, PROJECT_ROOT)

            if is_ignored(rel_path):
                continue

            is_web_file = rel_path.startswith(WEB_DIR_NAME + os.sep)
            dst_path = os.path.join(DEPLOY_DIR, rel_path)

            if is_web_file and should_compress(src_path):
                dst_path += ".gz"
                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                with open(src_path, 'rb') as f_in:
                    with gzip.open(dst_path, 'wb', compresslevel=9) as f_out:
                        shutil.copyfileobj(f_in, f_out)
                print(f"Compressed: {rel_path} → {os.path.relpath(dst_path, DEPLOY_DIR)}")
            else:
                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                shutil.copy2(src_path, dst_path)
                print(f"Copied: {rel_path}")

def main():
    print("Preparing deploy directory...")
    clean_deploy_dir()
    print("Copying and compressing files...")
    copy_and_process_files()
    print("Done!")

if __name__ == "__main__":
    main()