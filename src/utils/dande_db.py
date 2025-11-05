"""
DandE.db - Tests, Errors, Trial Runs, and TODOs Tracking Database

This module manages the DandE.db database for tracking:
- Tests: Test execution results, coverage, failures
- Errors: Runtime errors, exceptions, bugs
- Trial Runs: Feature attempts, iterations, version tracking
- TODOs: Feature requests, improvements, technical debt
"""

import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any
from enum import Enum

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class TestStatus(Enum):
    """Test execution status"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class ErrorSeverity(Enum):
    """Error severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class TrialStatus(Enum):
    """Trial run status"""
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TODOStatus(Enum):
    """TODO status"""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"
    BLOCKED = "blocked"


class DandEDatabase:
    """Manages DandE.db database for tracking tests, errors, trials, and TODOs"""
    
    def __init__(self, db_path: str = "data/DandE.db"):
        """Initialize DandE database connection and create tables"""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
        logging.info(f"DandE database initialized at {self.db_path}")
    
    def _create_tables(self):
        """Create all required tables in DandE.db"""
        cursor = self.conn.cursor()
        
        # Version tracking table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS versions (
                version TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT,
                git_commit_hash TEXT,
                git_branch TEXT
            )
        """)
        
        # Tests table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tests (
                test_id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_name TEXT NOT NULL,
                test_file TEXT NOT NULL,
                test_class TEXT,
                test_method TEXT,
                version TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                duration_ms INTEGER,
                error_message TEXT,
                stack_trace TEXT,
                coverage_percent REAL,
                FOREIGN KEY (version) REFERENCES versions(version)
            )
        """)
        
        # Test assertions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_assertions (
                assertion_id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_id INTEGER NOT NULL,
                assertion_type TEXT NOT NULL,
                assertion_description TEXT,
                passed BOOLEAN NOT NULL,
                expected_value TEXT,
                actual_value TEXT,
                FOREIGN KEY (test_id) REFERENCES tests(test_id)
            )
        """)
        
        # Errors table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS errors (
                error_id INTEGER PRIMARY KEY AUTOINCREMENT,
                version TEXT NOT NULL,
                error_type TEXT NOT NULL,
                error_message TEXT NOT NULL,
                severity TEXT NOT NULL DEFAULT 'medium',
                file_path TEXT,
                line_number INTEGER,
                function_name TEXT,
                stack_trace TEXT,
                occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP,
                resolution_notes TEXT,
                test_id INTEGER,
                FOREIGN KEY (version) REFERENCES versions(version),
                FOREIGN KEY (test_id) REFERENCES tests(test_id)
            )
        """)
        
        # Trial runs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trial_runs (
                trial_id INTEGER PRIMARY KEY AUTOINCREMENT,
                version TEXT NOT NULL,
                feature_name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'planned',
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                duration_ms INTEGER,
                success BOOLEAN,
                notes TEXT,
                test_id INTEGER,
                error_id INTEGER,
                FOREIGN KEY (version) REFERENCES versions(version),
                FOREIGN KEY (test_id) REFERENCES tests(test_id),
                FOREIGN KEY (error_id) REFERENCES errors(error_id)
            )
        """)
        
        # TODOs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS todos (
                todo_id INTEGER PRIMARY KEY AUTOINCREMENT,
                version TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL DEFAULT 'open',
                priority INTEGER DEFAULT 5,
                file_path TEXT,
                line_number INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP,
                resolved_in_version TEXT,
                test_id INTEGER,
                error_id INTEGER,
                FOREIGN KEY (version) REFERENCES versions(version),
                FOREIGN KEY (test_id) REFERENCES tests(test_id),
                FOREIGN KEY (error_id) REFERENCES errors(error_id)
            )
        """)
        
        # Test coverage table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_coverage (
                coverage_id INTEGER PRIMARY KEY AUTOINCREMENT,
                version TEXT NOT NULL,
                file_path TEXT NOT NULL,
                total_lines INTEGER,
                covered_lines INTEGER,
                coverage_percent REAL,
                measured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (version) REFERENCES versions(version)
            )
        """)
        
        # Test pyramid metrics (DDD)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_pyramid (
                pyramid_id INTEGER PRIMARY KEY AUTOINCREMENT,
                version TEXT NOT NULL,
                unit_tests_count INTEGER DEFAULT 0,
                integration_tests_count INTEGER DEFAULT 0,
                e2e_tests_count INTEGER DEFAULT 0,
                unit_tests_passed INTEGER DEFAULT 0,
                integration_tests_passed INTEGER DEFAULT 0,
                e2e_tests_passed INTEGER DEFAULT 0,
                measured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (version) REFERENCES versions(version)
            )
        """)
        
        self.conn.commit()
        logging.info("DandE database tables created successfully")
    
    def record_version(self, version: str, description: str = "", 
                       git_commit_hash: str = "", git_branch: str = ""):
        """Record a new version"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO versions (version, description, git_commit_hash, git_branch)
            VALUES (?, ?, ?, ?)
        """, (version, description, git_commit_hash, git_branch))
        self.conn.commit()
        logging.info(f"Version {version} recorded")
    
    def record_test(self, test_name: str, test_file: str, version: str,
                    test_class: Optional[str] = None, test_method: Optional[str] = None,
                    status: TestStatus = TestStatus.PENDING,
                    error_message: Optional[str] = None,
                    stack_trace: Optional[str] = None,
                    coverage_percent: Optional[float] = None,
                    duration_ms: Optional[int] = None) -> int:
        """Record a test execution"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO tests (test_name, test_file, test_class, test_method, version,
                             status, error_message, stack_trace, coverage_percent, duration_ms,
                             started_at, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (test_name, test_file, test_class, test_method, version,
              status.value, error_message, stack_trace, coverage_percent, duration_ms,
              datetime.now(), datetime.now() if status in [TestStatus.PASSED, TestStatus.FAILED, TestStatus.ERROR] else None))
        self.conn.commit()
        test_id = cursor.lastrowid
        logging.info(f"Test {test_name} recorded with ID {test_id}")
        return test_id
    
    def record_error(self, version: str, error_type: str, error_message: str,
                    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                    file_path: Optional[str] = None, line_number: Optional[int] = None,
                    function_name: Optional[str] = None, stack_trace: Optional[str] = None,
                    test_id: Optional[int] = None) -> int:
        """Record an error"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO errors (version, error_type, error_message, severity,
                             file_path, line_number, function_name, stack_trace, test_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (version, error_type, error_message, severity.value,
              file_path, line_number, function_name, stack_trace, test_id))
        self.conn.commit()
        error_id = cursor.lastrowid
        logging.warning(f"Error recorded with ID {error_id}: {error_type}")
        return error_id
    
    def record_trial(self, version: str, feature_name: str,
                    status: TrialStatus = TrialStatus.PLANNED,
                    success: Optional[bool] = None, notes: Optional[str] = None,
                    test_id: Optional[int] = None, error_id: Optional[int] = None,
                    duration_ms: Optional[int] = None) -> int:
        """Record a trial run"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO trial_runs (version, feature_name, status, success, notes,
                                  test_id, error_id, duration_ms, started_at, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (version, feature_name, status.value, success, notes,
              test_id, error_id, duration_ms,
              datetime.now() if status == TrialStatus.IN_PROGRESS else None,
              datetime.now() if status == TrialStatus.COMPLETED else None))
        self.conn.commit()
        trial_id = cursor.lastrowid
        logging.info(f"Trial run {feature_name} recorded with ID {trial_id}")
        return trial_id
    
    def record_todo(self, version: str, title: str, description: Optional[str] = None,
                   status: TODOStatus = TODOStatus.OPEN, priority: int = 5,
                   file_path: Optional[str] = None, line_number: Optional[int] = None,
                   test_id: Optional[int] = None, error_id: Optional[int] = None) -> int:
        """Record a TODO"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO todos (version, title, description, status, priority,
                             file_path, line_number, test_id, error_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (version, title, description, status.value, priority,
              file_path, line_number, test_id, error_id))
        self.conn.commit()
        todo_id = cursor.lastrowid
        logging.info(f"TODO recorded with ID {todo_id}: {title}")
        return todo_id
    
    def record_coverage(self, version: str, file_path: str, total_lines: int,
                       covered_lines: int, coverage_percent: float):
        """Record test coverage for a file"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO test_coverage (version, file_path, total_lines, covered_lines, coverage_percent)
            VALUES (?, ?, ?, ?, ?)
        """, (version, file_path, total_lines, covered_lines, coverage_percent))
        self.conn.commit()
    
    def record_pyramid_metrics(self, version: str, unit_count: int, integration_count: int,
                               e2e_count: int, unit_passed: int, integration_passed: int,
                               e2e_passed: int):
        """Record DDD test pyramid metrics"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO test_pyramid (version, unit_tests_count, integration_tests_count,
                                    e2e_tests_count, unit_tests_passed, integration_tests_passed,
                                    e2e_tests_passed)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (version, unit_count, integration_count, e2e_count,
              unit_passed, integration_passed, e2e_passed))
        self.conn.commit()
    
    def get_version_stats(self, version: str) -> Dict[str, Any]:
        """Get statistics for a version"""
        cursor = self.conn.cursor()
        
        # Get test stats
        cursor.execute("""
            SELECT COUNT(*) as total, 
                   SUM(CASE WHEN status = 'passed' THEN 1 ELSE 0 END) as passed,
                   SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
            FROM tests WHERE version = ?
        """, (version,))
        test_stats = dict(cursor.fetchone() or {})
        
        # Get error stats
        cursor.execute("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN resolved_at IS NULL THEN 1 ELSE 0 END) as unresolved
            FROM errors WHERE version = ?
        """, (version,))
        error_stats = dict(cursor.fetchone() or {})
        
        # Get TODO stats
        cursor.execute("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN status = 'open' THEN 1 ELSE 0 END) as open
            FROM todos WHERE version = ?
        """, (version,))
        todo_stats = dict(cursor.fetchone() or {})
        
        return {
            'version': version,
            'tests': test_stats,
            'errors': error_stats,
            'todos': todo_stats
        }
    
    def close(self):
        """Close database connection"""
        self.conn.close()
        logging.info("DandE database connection closed")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

