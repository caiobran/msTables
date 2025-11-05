#!/usr/bin/env python3
"""
Comprehensive Test Runner for mstables

Runs all tests and catches issues before they reach users.
Based on NASA Exoplanet test structure.
"""

import subprocess
import sys
import time
import os
from pathlib import Path
from typing import Dict, List, Tuple


def run_command(cmd: List[str], timeout: int = 300) -> Tuple[int, str, str]:
    """Run a command and return exit code, stdout, stderr."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=Path.cwd()
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)


def run_smoke_tests() -> bool:
    """Run smoke tests (quick, essential tests)."""
    print("🔥 Running Smoke Tests...")
    
    cmd = [sys.executable, "-m", "pytest", "tests/smoke/", "-v", "--tb=short"]
    exit_code, stdout, stderr = run_command(cmd, timeout=60)
    
    print(f"Smoke tests completed in {time.time():.2f} seconds")
    print(f"Exit code: {exit_code}")
    
    if exit_code != 0:
        print("❌ Smoke tests failed!")
        print("STDOUT:", stdout)
        print("STDERR:", stderr)
        return False
    
    print("✅ Smoke tests passed!")
    return True


def run_unit_tests() -> bool:
    """Run unit tests."""
    print("🧪 Running Unit Tests...")
    
    cmd = [sys.executable, "-m", "pytest", "tests/unit/", "-v", "--tb=short"]
    exit_code, stdout, stderr = run_command(cmd, timeout=300)
    
    print(f"Unit tests completed in {time.time():.2f} seconds")
    print(f"Exit code: {exit_code}")
    
    if exit_code != 0:
        print("❌ Unit tests failed!")
        print("STDOUT:", stdout)
        print("STDERR:", stderr)
        return False
    
    print("✅ Unit tests passed!")
    return True


def run_integration_tests() -> bool:
    """Run integration tests."""
    print("🔗 Running Integration Tests...")
    
    cmd = [sys.executable, "-m", "pytest", "tests/integration/", "-v", "--tb=short"]
    exit_code, stdout, stderr = run_command(cmd, timeout=600)
    
    print(f"Integration tests completed in {time.time():.2f} seconds")
    print(f"Exit code: {exit_code}")
    
    if exit_code != 0:
        print("❌ Integration tests failed!")
        print("STDOUT:", stdout)
        print("STDERR:", stderr)
        return False
    
    print("✅ Integration tests passed!")
    return True


def run_e2e_tests() -> bool:
    """Run end-to-end tests."""
    print("🚀 Running E2E Tests...")
    
    cmd = [sys.executable, "-m", "pytest", "tests/e2e/", "-v", "--tb=short"]
    exit_code, stdout, stderr = run_command(cmd, timeout=900)
    
    print(f"E2E tests completed in {time.time():.2f} seconds")
    print(f"Exit code: {exit_code}")
    
    if exit_code != 0:
        print("❌ E2E tests failed!")
        print("STDOUT:", stdout)
        print("STDERR:", stderr)
        return False
    
    print("✅ E2E tests passed!")
    return True


def run_database_tests() -> bool:
    """Run database tests."""
    print("📊 Running Database Tests...")
    
    cmd = [sys.executable, "-m", "pytest", "tests/database/", "-v", "--tb=short"]
    exit_code, stdout, stderr = run_command(cmd, timeout=600)
    
    print(f"Database tests completed in {time.time():.2f} seconds")
    print(f"Exit code: {exit_code}")
    
    if exit_code != 0:
        print("❌ Database tests failed!")
        print("STDOUT:", stdout)
        print("STDERR:", stderr)
        return False
    
    print("✅ Database tests passed!")
    return True


def run_gpu_tests() -> bool:
    """Run GPU tests."""
    print("🎮 Running GPU Tests...")
    
    cmd = [sys.executable, "-m", "pytest", "tests/gpu/", "-v", "--tb=short", "-m", "gpu"]
    exit_code, stdout, stderr = run_command(cmd, timeout=300)
    
    print(f"GPU tests completed in {time.time():.2f} seconds")
    print(f"Exit code: {exit_code}")
    
    if exit_code != 0:
        print("⚠️ GPU tests failed (may not have GPU)")
        print("STDOUT:", stdout)
        print("STDERR:", stderr)
        return False  # Or True if GPU is optional
    
    print("✅ GPU tests passed!")
    return True


def run_multi_machine_tests() -> bool:
    """Run multi-machine tests."""
    print("🌐 Running Multi-Machine Tests...")
    
    cmd = [sys.executable, "-m", "pytest", "tests/multi_machine/", "-v", "--tb=short"]
    exit_code, stdout, stderr = run_command(cmd, timeout=300)
    
    print(f"Multi-machine tests completed in {time.time():.2f} seconds")
    print(f"Exit code: {exit_code}")
    
    if exit_code != 0:
        print("⚠️ Multi-machine tests failed (may not have network access)")
        print("STDOUT:", stdout)
        print("STDERR:", stderr)
        return False  # Or True if multi-machine is optional
    
    print("✅ Multi-machine tests passed!")
    return True


def run_automation_tests() -> bool:
    """Run automation tests."""
    print("🤖 Running Automation Tests...")
    
    cmd = [sys.executable, "-m", "pytest", "tests/automation/", "-v", "--tb=short"]
    exit_code, stdout, stderr = run_command(cmd, timeout=300)
    
    print(f"Automation tests completed in {time.time():.2f} seconds")
    print(f"Exit code: {exit_code}")
    
    if exit_code != 0:
        print("❌ Automation tests failed!")
        print("STDOUT:", stdout)
        print("STDERR:", stderr)
        return False
    
    print("✅ Automation tests passed!")
    return True


def run_comprehensive_framework() -> bool:
    """Run comprehensive test framework."""
    print("📋 Running Comprehensive Test Framework...")
    
    cmd = [sys.executable, "tests/comprehensive_test_framework.py"]
    exit_code, stdout, stderr = run_command(cmd, timeout=600)
    
    print(f"Comprehensive framework completed in {time.time():.2f} seconds")
    print(f"Exit code: {exit_code}")
    
    if exit_code != 0:
        print("❌ Comprehensive framework failed!")
        print("STDOUT:", stdout)
        print("STDERR:", stderr)
        return False
    
    print("✅ Comprehensive framework passed!")
    return True


def main():
    """Main test runner."""
    print("=" * 80)
    print("COMPREHENSIVE TEST SUITE FOR MSTABLES")
    print("=" * 80)
    print()
    
    results = {}
    
    # Run smoke tests first (fastest)
    results['smoke'] = run_smoke_tests()
    if not results['smoke']:
        print("\n❌ Smoke tests failed - stopping here")
        return False
    
    # Run unit tests
    results['unit'] = run_unit_tests()
    
    # Run integration tests
    results['integration'] = run_integration_tests()
    
    # Run database tests
    results['database'] = run_database_tests()
    
    # Run automation tests
    results['automation'] = run_automation_tests()
    
    # Run GPU tests (optional)
    results['gpu'] = run_gpu_tests()
    
    # Run multi-machine tests (optional)
    results['multi_machine'] = run_multi_machine_tests()
    
    # Run E2E tests (last, slowest)
    results['e2e'] = run_e2e_tests()
    
    # Run comprehensive framework
    results['comprehensive'] = run_comprehensive_framework()
    
    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    failed = total - passed
    
    print(f"Total Test Suites: {total}")
    print(f"Passed: {passed} ✅")
    print(f"Failed: {failed} ❌")
    print(f"Success Rate: {passed/total*100:.1f}%")
    
    print("\nDetailed Results:")
    for test_type, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {test_type.upper():20s}: {status}")
    
    print("=" * 80)
    
    return all(results.values())


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

