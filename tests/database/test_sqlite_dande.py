"""
SQLite DandE.db Tests

Tests for DandE.db (Development/Operational Tracking):
- Connection management
- Version tracking
- Test result recording
- Error tracking
- Trial run tracking
- TODO management
- Test coverage tracking
- Test pyramid metrics
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from src.utils.dande_db import (
    DandEDatabase, TestStatus, ErrorSeverity, TrialStatus, TODOStatus
)


class TestDandEDatabaseConnection:
    """Test DandE.db connection management"""
    
    def test_dande_db_connect(self):
        """Test basic DandE.db connection"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            db = DandEDatabase(db_path=db_path)
            assert db.conn is not None
            assert db.db_type == "sqlite"
            db.close()
        finally:
            Path(db_path).unlink()
    
    def test_dande_db_tables_created(self):
        """Test that all required tables are created"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            db = DandEDatabase(db_path=db_path)
            
            # Check all tables exist
            tables = db.fetchall("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """)
            table_names = [t['name'] for t in tables]
            
            required_tables = [
                'versions', 'tests', 'test_assertions', 'errors',
                'trial_runs', 'todos', 'test_coverage', 'test_pyramid'
            ]
            
            for table in required_tables:
                assert table in table_names
            
            db.close()
        finally:
            Path(db_path).unlink()


class TestVersionTracking:
    """Test version tracking"""
    
    def test_record_version(self):
        """Test recording a version"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            db = DandEDatabase(db_path=db_path)
            
            version_id = db.record_version(
                version="1.0.1",
                description="Test version",
                git_commit_hash="abc123",
                git_branch="master"
            )
            
            # Verify version recorded
            result = db.fetchone("SELECT * FROM versions WHERE version = ?", ("1.0.1",))
            assert result is not None
            assert result['version'] == "1.0.1"
            assert result['description'] == "Test version"
            
            db.close()
        finally:
            Path(db_path).unlink()
    
    def test_get_version_stats(self):
        """Test getting version statistics"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            db = DandEDatabase(db_path=db_path)
            
            # Record version
            db.record_version(version="1.0.1", description="Test")
            
            # Record test
            db.record_test(
                test_name="test_example",
                test_file="test_example.py",
                version="1.0.1",
                status=TestStatus.PASSED
            )
            
            # Get stats
            stats = db.get_version_stats("1.0.1")
            
            assert stats['version'] == "1.0.1"
            assert stats['tests']['total'] == 1
            assert stats['tests']['passed'] == 1
            
            db.close()
        finally:
            Path(db_path).unlink()


class TestTestTracking:
    """Test test result tracking"""
    
    def test_record_test(self):
        """Test recording a test execution"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            db = DandEDatabase(db_path=db_path)
            db.record_version(version="1.0.1")
            
            test_id = db.record_test(
                test_name="test_example",
                test_file="test_example.py",
                version="1.0.1",
                test_class="TestExample",
                test_method="test_example",
                status=TestStatus.PASSED,
                duration_ms=100,
                coverage_percent=85.5
            )
            
            # Verify test recorded
            result = db.fetchone("SELECT * FROM tests WHERE test_id = ?", (test_id,))
            assert result is not None
            assert result['test_name'] == "test_example"
            assert result['status'] == "passed"
            assert result['duration_ms'] == 100
            
            db.close()
        finally:
            Path(db_path).unlink()
    
    def test_record_failed_test(self):
        """Test recording a failed test"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            db = DandEDatabase(db_path=db_path)
            db.record_version(version="1.0.1")
            
            test_id = db.record_test(
                test_name="test_failed",
                test_file="test_failed.py",
                version="1.0.1",
                status=TestStatus.FAILED,
                error_message="AssertionError: expected 1, got 2",
                stack_trace="Traceback..."
            )
            
            # Verify test recorded
            result = db.fetchone("SELECT * FROM tests WHERE test_id = ?", (test_id,))
            assert result is not None
            assert result['status'] == "failed"
            assert "AssertionError" in result['error_message']
            
            db.close()
        finally:
            Path(db_path).unlink()


class TestErrorTracking:
    """Test error tracking"""
    
    def test_record_error(self):
        """Test recording an error"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            db = DandEDatabase(db_path=db_path)
            db.record_version(version="1.0.1")
            
            error_id = db.record_error(
                version="1.0.1",
                error_type="ValueError",
                error_message="Invalid value",
                severity=ErrorSeverity.HIGH,
                file_path="src/utils/example.py",
                line_number=42,
                function_name="process_data",
                stack_trace="Traceback..."
            )
            
            # Verify error recorded
            result = db.fetchone("SELECT * FROM errors WHERE error_id = ?", (error_id,))
            assert result is not None
            assert result['error_type'] == "ValueError"
            assert result['severity'] == "high"
            assert result['file_path'] == "src/utils/example.py"
            
            db.close()
        finally:
            Path(db_path).unlink()


class TestTrialTracking:
    """Test trial run tracking"""
    
    def test_record_trial(self):
        """Test recording a trial run"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            db = DandEDatabase(db_path=db_path)
            db.record_version(version="1.0.1")
            
            trial_id = db.record_trial(
                version="1.0.1",
                feature_name="new_feature",
                status=TrialStatus.COMPLETED,
                success=True,
                notes="Successfully implemented",
                duration_ms=5000
            )
            
            # Verify trial recorded
            result = db.fetchone("SELECT * FROM trial_runs WHERE trial_id = ?", (trial_id,))
            assert result is not None
            assert result['feature_name'] == "new_feature"
            assert result['status'] == "completed"
            assert result['success'] == 1
            
            db.close()
        finally:
            Path(db_path).unlink()


class TestTODOTracking:
    """Test TODO tracking"""
    
    def test_record_todo(self):
        """Test recording a TODO"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            db = DandEDatabase(db_path=db_path)
            db.record_version(version="1.0.1")
            
            todo_id = db.record_todo(
                version="1.0.1",
                title="Implement feature X",
                description="Add new feature",
                status=TODOStatus.OPEN,
                priority=5,
                file_path="src/utils/example.py",
                line_number=100
            )
            
            # Verify TODO recorded
            result = db.fetchone("SELECT * FROM todos WHERE todo_id = ?", (todo_id,))
            assert result is not None
            assert result['title'] == "Implement feature X"
            assert result['status'] == "open"
            assert result['priority'] == 5
            
            db.close()
        finally:
            Path(db_path).unlink()


class TestTestCoverage:
    """Test test coverage tracking"""
    
    def test_record_coverage(self):
        """Test recording test coverage"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            db = DandEDatabase(db_path=db_path)
            db.record_version(version="1.0.1")
            
            db.record_coverage(
                version="1.0.1",
                file_path="src/utils/example.py",
                total_lines=1000,
                covered_lines=850,
                coverage_percent=85.0
            )
            
            # Verify coverage recorded
            result = db.fetchone(
                "SELECT * FROM test_coverage WHERE version = ? AND file_path = ?",
                ("1.0.1", "src/utils/example.py")
            )
            assert result is not None
            assert result['coverage_percent'] == 85.0
            assert result['covered_lines'] == 850
            
            db.close()
        finally:
            Path(db_path).unlink()


class TestTestPyramid:
    """Test test pyramid metrics"""
    
    def test_record_pyramid_metrics(self):
        """Test recording test pyramid metrics"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            db = DandEDatabase(db_path=db_path)
            db.record_version(version="1.0.1")
            
            db.record_pyramid_metrics(
                version="1.0.1",
                unit_count=70,
                integration_count=20,
                e2e_count=10,
                unit_passed=68,
                integration_passed=19,
                e2e_passed=9
            )
            
            # Verify metrics recorded
            result = db.fetchone(
                "SELECT * FROM test_pyramid WHERE version = ?",
                ("1.0.1",)
            )
            assert result is not None
            assert result['unit_tests_count'] == 70
            assert result['integration_tests_count'] == 20
            assert result['e2e_tests_count'] == 10
            assert result['unit_tests_passed'] == 68
            
            db.close()
        finally:
            Path(db_path).unlink()

