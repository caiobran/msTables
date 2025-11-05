"""
Smoke Tests

Quick essential tests that verify basic functionality:
- Database connections
- API availability
- Core functionality
- Critical paths
"""

import pytest
from pathlib import Path


class TestSmokeDatabase:
    """Smoke tests for databases"""
    
    def test_postgresql_connection_smoke(self):
        """Smoke test: PostgreSQL connection"""
        try:
            from src.utils.database_adapter import FinancialDataDB
            
            db = FinancialDataDB()
            result = db.fetchone("SELECT 1 as test")
            assert result is not None
            assert result['test'] == 1
            db.close()
        except Exception as e:
            pytest.skip(f"PostgreSQL not available: {e}")
    
    def test_sqlite_dande_connection_smoke(self):
        """Smoke test: SQLite DandE.db connection"""
        try:
            from src.utils.dande_db import DandEDatabase
            
            db = DandEDatabase()
            db.record_version("1.0.1", "Smoke test")
            db.close()
        except Exception as e:
            pytest.fail(f"DandE.db connection failed: {e}")


class TestSmokeAPIs:
    """Smoke tests for APIs"""
    
    def test_version_manager_smoke(self):
        """Smoke test: Version manager"""
        from src.utils.version_manager import VersionManager
        
        vm = VersionManager()
        version = vm.get_current_version()
        
        assert version is not None
        assert len(version.split('.')) == 3
    
    def test_test_runner_smoke(self):
        """Smoke test: Test runner"""
        from src.utils.test_runner import TestRunner
        
        runner = TestRunner()
        assert runner is not None
        assert runner.version is not None
        
        runner.close()


class TestSmokeCoreFunctionality:
    """Smoke tests for core functionality"""
    
    def test_database_adapter_smoke(self):
        """Smoke test: Database adapter"""
        from src.utils.database_adapter import DatabaseAdapter
        
        # Test SQLite adapter
        db = DatabaseAdapter(db_type="sqlite", db_path="data/test_smoke.db")
        result = db.fetchone("SELECT 1 as test")
        assert result['test'] == 1
        db.close()
        
        # Cleanup
        Path("data/test_smoke.db").unlink(missing_ok=True)
    
    def test_dande_db_smoke(self):
        """Smoke test: DandE.db"""
        from src.utils.dande_db import DandEDatabase, TestStatus
        
        db = DandEDatabase()
        db.record_version("1.0.1", "Smoke test")
        
        test_id = db.record_test(
            test_name="smoke_test",
            test_file="test_smoke.py",
            version="1.0.1",
            status=TestStatus.PASSED
        )
        
        assert test_id is not None
        db.close()


class TestSmokeCriticalPaths:
    """Smoke tests for critical paths"""
    
    def test_version_bump_smoke(self):
        """Smoke test: Version bump"""
        from src.utils.version_manager import VersionManager
        
        vm = VersionManager()
        current = vm.get_current_version()
        next_v = vm.get_next_version()
        
        assert next_v != current
    
    def test_file_structure_smoke(self):
        """Smoke test: File structure"""
        # Check critical files exist
        assert Path("VERSION").exists() or Path("pyproject.toml").exists()
        assert Path("CHANGELOG.md").exists()
        assert Path("src/utils").exists()
        assert Path("tests").exists()

