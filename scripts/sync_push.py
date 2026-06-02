import subprocess
import sys


def get_current_branch() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def sync_push(branch: str | None = None) -> None:
    if not branch:
        branch = get_current_branch()

    print(f"Pushing src/ contents to origin/{branch} via git subtree...")

    result = subprocess.run(
        ["git", "subtree", "push", "--prefix=src", "origin", branch],
        capture_output=True, text=True,
    )

    if result.returncode == 0:
        print(f"Sync pushed to origin/{branch}")
    else:
        print(f"Failed to push to origin/{branch}")
        print(result.stderr)
        sys.exit(1)


if __name__ == "__main__":
    branch = sys.argv[1] if len(sys.argv) > 1 else None
    sync_push(branch)