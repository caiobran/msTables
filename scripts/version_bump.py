#!/usr/bin/env python3
"""
Version Bump Script

Increments nano version, runs tests, updates CHANGELOG, and commits to git
Follows TDD workflow: test → commit → fix → test → commit
"""

import subprocess
import sys
from pathlib import Path
from typing import Optional
import logging

from src.utils.version_manager import VersionManager
from src.utils.dande_db import DandEDatabase, TrialStatus
from src.utils.test_runner import TestRunner

logging.basicConfig(level=logging.INFO)


def get_git_commit_hash() -> str:
    """Get current git commit hash"""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True
        )
        return result.stdout.strip()[:7]  # Short hash
    except:
        return ""


def get_git_branch() -> str:
    """Get current git branch"""
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True
        )
        return result.stdout.strip()
    except:
        return ""


def run_tests_and_commit(version: str, description: str = "", 
                         test_type: Optional[str] = None) -> bool:
    """Run tests, commit if they pass, record in DandE.db"""
    dande_db = DandEDatabase()
    dande_db.record_version(version, description)
    
    # Run tests
    runner = TestRunner(version=version)
    try:
        if test_type:
            results = runner.run_tests(test_type=test_type)
        else:
            results = runner.run_all_tests()
        
        success = results["success"] if isinstance(results, dict) else all(r["success"] for r in results.values())
        
        if success:
            # Commit to git
            commit_message = f"Version {version}: {description or 'Version bump'}"
            subprocess.run(["git", "add", "."])
            subprocess.run(["git", "commit", "-m", commit_message])
            
            logging.info(f"✅ Version {version} committed successfully")
            return True
        else:
            logging.error(f"❌ Tests failed for version {version}")
            return False
    finally:
        runner.close()
        dande_db.close()


def main():
    """Main version bump workflow"""
    if len(sys.argv) > 1:
        description = " ".join(sys.argv[1:])
    else:
        description = input("Enter version description: ").strip()
    
    vm = VersionManager()
    current_version = vm.get_current_version()
    next_version = vm.increment_nano()
    
    print(f"Current version: {current_version}")
    print(f"Next version: {next_version}")
    print(f"Description: {description}")
    
    # Get git info
    git_hash = get_git_commit_hash()
    git_branch = get_git_branch()
    
    # Save version
    vm.save_version(next_version, description, git_hash, git_branch)
    
    # Run tests and commit
    success = run_tests_and_commit(next_version, description)
    
    if success:
        print(f"\n✅ Version {next_version} bumped successfully!")
        print(f"   Git commit: {git_hash}")
        print(f"   Git branch: {git_branch}")
    else:
        print(f"\n❌ Version bump failed - tests did not pass")
        sys.exit(1)


if __name__ == "__main__":
    main()

