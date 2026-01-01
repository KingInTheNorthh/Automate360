#!/usr/bin/env python3

import os
import subprocess
from datetime import datetime


def is_git_repo(path):
    return os.path.isdir(os.path.join(path, ".git"))


def run_git(cmd, repo_path):
    result = subprocess.run(
        ["git"] + cmd,
        cwd=repo_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    return result.stdout.strip()


import json
from datetime import datetime, timedelta


def get_remote_url(repo_path):
    url = run_git(["remote", "get-url", "origin"], repo_path)
    return url if url else "—"


def commits_last_24h(repo_path):
    since = (datetime.now() - timedelta(days=1)).isoformat()
    count = run_git(["rev-list", "--count", "--since", since, "HEAD"], repo_path)
    return int(count) if count.isdigit() else 0


def get_repo_info(repo_path):
    name = os.path.basename(repo_path)

    branch = run_git(["rev-parse", "--abbrev-ref", "HEAD"], repo_path)

    status = run_git(["status", "--porcelain"], repo_path)
    dirty = True if status else False

    last_commit_ts = run_git(["log", "-1", "--format=%ct"], repo_path)

    last_commit = datetime.fromtimestamp(int(last_commit_ts))

    return {
        "name": name,
        "branch": branch,
        "dirty": dirty,
        "last_commit": last_commit,
        "remote": get_remote_url(repo_path),
        "commits_24h": commits_last_24h(repo_path),
    }


def scan_repos(base_dir):
    repos = []

    for entry in os.scandir(base_dir):
        if entry.is_dir():
            if is_git_repo(entry.path):
                repos.append(get_repo_info(entry.path))

    return repos


def print_table(repos):
    print(f"{'REPO':18} {'BRANCH':10} {'DIRTY':5} {'24H':4} LAST COMMIT    REMOTE")
    print("-" * 90)

    for r in repos:
        ago = datetime.now() - r["last_commit"]
        hours = int(ago.total_seconds() // 3600)

        dirty = "yes" if r["dirty"] else "no"

        print(
            f"{r['name'][:18]:18} "
            f"{r['branch'][:10]:10} "
            f"{dirty:5} "
            f"{r['commits_24h']:4} "
            f"{hours:3}h ago      "
            f"{r['remote']}"
        )


if __name__ == "__main__":
    import sys

    args = sys.argv[1:]

    json_mode = "--json" in args
    args = [a for a in args if a != "--json"]

    base_dir = args[0] if args else os.getcwd()

    if not os.path.isdir(base_dir):
        print(f"Error: directory does not exist → {base_dir}")
        sys.exit(1)

    repos = scan_repos(base_dir)

    if json_mode:
        print(
            json.dumps(
                [{**r, "last_commit": r["last_commit"].isoformat()} for r in repos],
                indent=2,
            )
        )
    else:
        print_table(repos)
