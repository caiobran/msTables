"""
Automation Tests

Tests for automation systems:
- Version bumping
- Test runner automation
- Git commit automation
- CHANGELOG updates
- DandE.db tracking
"""

import pytest
from pathlib import Path
import subprocess
import sys


class TestVersionAutomation:
    """Test version automation"""
    
    def test_version_manager_initialization(self):
        """Test version manager initialization"""
        from src.utils.version_manager import VersionManager
        
        vm = VersionManager()
        assert vm is not None
        assert vm.current_version is not None
    
    def test_version_increment(self):
        """Test version increment"""
        from src.utils.version_manager import VersionManager
        
        vm = VersionManager()
        current = vm.get_current_version()
        next_v = vm.increment_nano()
        
        assert next_v != current
        assert len(next_v.split('.')) == 3
        
        # Should increment patch version
        current_parts = current.split('.')
        next_parts = next_v.split('.')
        
        if current_parts[2] == '9':
            # Should increment minor
            assert int(next_parts[1]) == int(current_parts[1]) + 1
            assert next_parts[2] == '0'
        else:
            # Should increment patch
            assert int(next_parts[2]) == int(current_parts[2]) + 1
    
    def test_version_save(self):
        """Test saving version"""
        from src.utils.version_manager import VersionManager
        
        vm = VersionManager()
        version = vm.get_current_version()
        
        # Save version
        vm.save_version(version, "Test description")
        
        # Verify VERSION file exists
        version_file = Path("VERSION")
        assert version_file.exists()
        
        # Verify content
        content = version_file.read_text().strip()
        assert content == version


class TestTestRunnerAutomation:
    """Test test runner automation"""
    
    def test_test_runner_initialization(self):
        """Test test runner initialization"""
        from src.utils.test_runner import TestRunner
        
        runner = TestRunner()
        assert runner is not None
        assert runner.version is not None
        assert runner.dande_db is not None
        
        runner.close()
    
    def test_test_runner_run_tests(self):
        """Test running tests with test runner"""
        from src.utils.test_runner import TestRunner
        
        runner = TestRunner()
        
        # Run unit tests
        results = runner.run_tests(test_type="unit")
        
        assert results is not None
        assert 'success' in results
        assert 'exit_code' in results
        
        runner.close()
    
    def test_test_runner_all_tests(self):
        """Test running all tests"""
        from src.utils.test_runner import TestRunner
        
        runner = TestRunner()
        
        # Run all tests
        results = runner.run_all_tests()
        
        assert results is not None
        assert isinstance(results, dict)
        assert 'unit' in results
        assert 'integration' in results
        assert 'e2e' in results
        
        runner.close()


class TestGitAutomation:
    """Test git automation"""
    
    def test_git_repository_exists(self):
        """Test git repository exists"""
        git_dir = Path(".git")
        assert git_dir.exists() or git_dir.is_dir()
    
    def test_git_commit_hash(self):
        """Test getting git commit hash"""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                commit_hash = result.stdout.strip()
                assert len(commit_hash) >= 7
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pytest.skip("Git not available")
    
    def test_git_branch(self):
        """Test getting git branch"""
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                branch = result.stdout.strip()
                assert len(branch) > 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pytest.skip("Git not available")


class TestCHANGELOGAutomation:
    """Test CHANGELOG automation"""
    
    def test_changelog_exists(self):
        """Test CHANGELOG.md exists"""
        changelog = Path("CHANGELOG.md")
        assert changelog.exists()
    
    def test_changelog_format(self):
        """Test CHANGELOG.md format"""
        changelog = Path("CHANGELOG.md")
        if not changelog.exists():
            pytest.skip("CHANGELOG.md not found")
        
        content = changelog.read_text()
        
        # Should contain version headers
        assert "## [" in content or "## [Unreleased]" in content
    
    def test_changelog_version_entry(self):
        """Test CHANGELOG version entry format"""
        changelog = Path("CHANGELOG.md")
        if not changelog.exists():
            pytest.skip("CHANGELOG.md not found")
        
        content = changelog.read_text()
        
        # Should contain version sections
        assert "## [" in content or "## [Unreleased]" in content


class TestDandETrackingAutomation:
    """Test DandE.db tracking automation"""
    
    def test_version_tracking(self):
        """Test version tracking in DandE.db"""
        from src.utils.dande_db import DandEDatabase
        from src.utils.version_manager import VersionManager
        
        vm = VersionManager()
        version = vm.get_current_version()
        
        db = DandEDatabase()
        db.record_version(version, "Test version")
        
        stats = db.get_version_stats(version)
        assert stats is not None
        assert stats['version'] == version
        
        db.close()
    
    def test_test_result_tracking(self):
        """Test test result tracking in DandE.db"""
        from src.utils.dande_db import DandEDatabase, TestStatus
        from src.utils.version_manager import VersionManager
        
        vm = VersionManager()
        version = vm.get_current_version()
        
        db = DandEDatabase()
        db.record_version(version)
        
        test_id = db.record_test(
            test_name="test_example",
            test_file="test_example.py",
            version=version,
            status=TestStatus.PASSED
        )
        
        assert test_id is not None
        
        db.close()

