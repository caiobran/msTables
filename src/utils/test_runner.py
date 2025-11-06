"""
Test Runner with DandE.db Integration

Runs tests and records results in DandE.db
Integrates with nano versioning system
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import logging

from src.utils.dande_db import DandEDatabase, TestStatus, ErrorSeverity, TrialStatus
from src.utils.version_manager import VersionManager

logging.basicConfig(level=logging.INFO)


class TestRunner:
    """Runs tests and tracks results in DandE.db"""
    
    def __init__(self, version: Optional[str] = None):
        """Initialize test runner"""
        self.version_manager = VersionManager()
        self.version = version or self.version_manager.get_current_version()
        self.dande_db = DandEDatabase()
        self.dande_db.record_version(self.version)
    
    def run_tests(self, test_path: Optional[str] = None, 
                  test_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Run tests and record results
        
        Args:
            test_path: Specific test file or directory to run
            test_type: "unit", "integration", or "e2e"
        
        Returns:
            Dictionary with test results
        """
        # Record trial run
        trial_id = self.dande_db.record_trial(
            version=self.version,
            feature_name=f"test_run_{test_type or 'all'}",
            status=TrialStatus.IN_PROGRESS
        )
        
        # Build pytest command
        cmd = ["pytest", "-v", "--tb=short"]
        
        if test_path:
            cmd.append(test_path)
        elif test_type:
            if test_type == "unit":
                cmd.append("tests/unit/")
            elif test_type == "integration":
                cmd.append("tests/integration/")
            elif test_type == "e2e":
                cmd.append("tests/e2e/")
        
        # Run tests
        start_time = datetime.now()
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        end_time = datetime.now()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)
        
        # Parse results
        success = result.returncode == 0
        output = result.stdout + result.stderr
        
        # Record trial completion
        self.dande_db.record_trial(
            version=self.version,
            feature_name=f"test_run_{test_type or 'all'}",
            status=TrialStatus.COMPLETED if success else TrialStatus.FAILED,
            success=success,
            notes=output[:1000],  # Truncate to first 1000 chars
            trial_id=trial_id,
            duration_ms=duration_ms
        )
        
        # Record errors if any
        if not success:
            error_id = self.dande_db.record_error(
                version=self.version,
                error_type="TestFailure",
                error_message=f"Tests failed with exit code {result.returncode}",
                severity=ErrorSeverity.HIGH,
                stack_trace=output
            )
        
        return {
            "success": success,
            "exit_code": result.returncode,
            "duration_ms": duration_ms,
            "output": output,
            "trial_id": trial_id
        }
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests (unit, integration, e2e)"""
        results = {
            "unit": self.run_tests(test_type="unit"),
            "integration": self.run_tests(test_type="integration"),
            "e2e": self.run_tests(test_type="e2e")
        }
        
        # Calculate pyramid metrics
        unit_count = self._count_tests("tests/unit/")
        integration_count = self._count_tests("tests/integration/")
        e2e_count = self._count_tests("tests/e2e/")
        
        unit_passed = results["unit"]["success"]
        integration_passed = results["integration"]["success"]
        e2e_passed = results["e2e"]["success"]
        
        # Record pyramid metrics
        self.dande_db.record_pyramid_metrics(
            version=self.version,
            unit_count=unit_count,
            integration_count=integration_count,
            e2e_count=e2e_count,
            unit_passed=1 if unit_passed else 0,
            integration_passed=1 if integration_passed else 0,
            e2e_passed=1 if e2e_passed else 0
        )
        
        return results
    
    def _count_tests(self, test_dir: str) -> int:
        """Count test files in directory"""
        test_path = Path(test_dir)
        if not test_path.exists():
            return 0
        return len(list(test_path.glob("test_*.py")))
    
    def close(self):
        """Close database connection"""
        self.dande_db.close()


if __name__ == "__main__":
    runner = TestRunner()
    try:
        results = runner.run_all_tests()
        print(f"\nTest Results:")
        print(f"Unit: {'PASSED' if results['unit']['success'] else 'FAILED'}")
        print(f"Integration: {'PASSED' if results['integration']['success'] else 'FAILED'}")
        print(f"E2E: {'PASSED' if results['e2e']['success'] else 'FAILED'}")
    finally:
        runner.close()

