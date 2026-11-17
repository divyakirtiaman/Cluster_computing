"""
CineMatch Environment & Runtime Verification Script
Diagnoses host system dependencies: Python, Java, Node.js, npm, Git, and hardware specs.
"""

import os
import sys
import subprocess
import shutil
import platform


def check_command(cmd, name, version_arg="--version"):
    """Check if an executable exists and return its version."""
    exe_path = shutil.which(cmd)
    if not exe_path:
        return False, f"MISSING: {name} was not found on PATH."
    try:
        res = subprocess.run([cmd, version_arg], capture_output=True, text=True, timeout=10)
        output = (res.stdout or res.stderr).strip().splitlines()[0]
        return True, f"OK: {name} detected ({output}) at {exe_path}"
    except Exception as e:
        return False, f"ERROR: Failed to query {name}: {str(e)}"


def check_java():
    """Java JDK check is vital for Apache Spark."""
    java_home = os.environ.get("JAVA_HOME")
    status, msg = check_command("java", "Java JDK", "-version")
    extra = f" [JAVA_HOME={java_home}]" if java_home else " [WARNING: JAVA_HOME is not set]"
    return status, msg + extra


def main():
    print("=" * 70)
    print(" CineMatch System Environment Verification")
    print("=" * 70)
    print(f"Platform: {platform.system()} {platform.release()} ({platform.machine()})")
    print(f"Current Working Directory: {os.getcwd()}")
    print("-" * 70)

    # 1. Python Check
    py_ver = sys.version.split()[0]
    print(f" Python:      OK: Python {py_ver} ({sys.executable})")

    # 2. Java Check (Needed for Spark)
    java_ok, java_msg = check_java()
    print(f" Java:        {java_msg}")

    # 3. Node.js Check
    node_ok, node_msg = check_command("node", "Node.js")
    print(f" Node.js:     {node_msg}")

    # 4. npm Check (Windows npm.cmd)
    npm_cmd = "npm.cmd" if platform.system() == "Windows" else "npm"
    npm_ok, npm_msg = check_command(npm_cmd, "npm")
    print(f" npm:         {npm_msg}")

    # 5. Git Check
    git_ok, git_msg = check_command("git", "Git")
    print(f" Git:         {git_msg}")

    print("-" * 70)
    if java_ok and node_ok and npm_ok and git_ok:
        print(" SUCCESS: All core system runtimes for CineMatch are detected and operational!")
    else:
        print(" WARNING: Some components require attention before proceeding to Phase 3.")
    print("=" * 70)


if __name__ == "__main__":
    main()
