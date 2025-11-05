#!/usr/bin/env python3
"""
PDS Compliance Checker
======================

Checks any codebase for PDS (Project Development Standards) compliance
and generates improvement recommendations.
"""

import os
import sys
import json
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

class PDSComplianceChecker:
    """PDS compliance checker for any codebase"""
    
    def __init__(self, project_path: str = "."):
        self.project_path = Path(project_path)
        self.project_name = self.project_path.name
        self.violations = []
        self.compliance_score = 0
        
        # PDS Standards
        self.pds_standards = {
            'project_structure': {
                'required_files': ['README.md', 'CHANGELOG.md', 'requirements.txt', 'setup.py'],
                'required_dirs': ['src', 'tests', 'docs'],
                'weight': 20
            },
            'code_quality': {
                'max_file_size': 1000,  # lines
                'max_function_length': 50,  # lines
                'max_class_length': 200,  # lines
                'required_docstrings': True,
                'weight': 25
            },
            'testing': {
                'min_test_coverage': 80,  # percent
                'required_test_types': ['unit', 'integration', 'e2e'],
                'test_pyramid_ratio': [70, 20, 10],  # unit, integration, e2e
                'weight': 30
            },
            'documentation': {
                'required_docs': ['README.md', 'API.md', 'CONTRIBUTING.md'],
                'code_comments_ratio': 0.2,  # 20% of lines should be comments
                'weight': 15
            },
            'security': {
                'no_hardcoded_secrets': True,
                'dependency_vulnerabilities': False,
                'weight': 10
            }
        }
    
    def check_compliance(self) -> Dict[str, Any]:
        """Check PDS compliance"""
        print(f"🔍 Checking PDS compliance for {self.project_name}")
        print("=" * 60)
        
        results = {
            'project_name': self.project_name,
            'timestamp': datetime.datetime.now().isoformat(),
            'compliance_score': 0,
            'violations': [],
            'recommendations': [],
            'standards': {}
        }
        
        # Check each standard
        for standard_name, standard_config in self.pds_standards.items():
            print(f"📋 Checking {standard_name}...")
            
            standard_result = self._check_standard(standard_name, standard_config)
            results['standards'][standard_name] = standard_result
            
            # Add violations
            results['violations'].extend(standard_result['violations'])
            
            # Calculate compliance score
            weight = standard_config['weight']
            compliance = standard_result['compliance_percentage']
            results['compliance_score'] += (compliance * weight / 100)
        
        # Generate recommendations
        results['recommendations'] = self._generate_recommendations(results['violations'])
        
        print(f"✅ Compliance check complete!")
        print(f"📊 Overall compliance: {results['compliance_score']:.1f}%")
        print(f"⚠️ Violations found: {len(results['violations'])}")
        
        return results
    
    def _check_standard(self, standard_name: str, standard_config: Dict[str, Any]) -> Dict[str, Any]:
        """Check a specific PDS standard"""
        violations = []
        compliance_percentage = 100
        
        if standard_name == 'project_structure':
            compliance_percentage, violations = self._check_project_structure(standard_config)
        elif standard_name == 'code_quality':
            compliance_percentage, violations = self._check_code_quality(standard_config)
        elif standard_name == 'testing':
            compliance_percentage, violations = self._check_testing(standard_config)
        elif standard_name == 'documentation':
            compliance_percentage, violations = self._check_documentation(standard_config)
        elif standard_name == 'security':
            compliance_percentage, violations = self._check_security(standard_config)
        
        return {
            'standard_name': standard_name,
            'compliance_percentage': compliance_percentage,
            'violations': violations,
            'weight': standard_config['weight']
        }
    
    def _check_project_structure(self, config: Dict[str, Any]) -> tuple[float, List[Dict[str, Any]]]:
        """Check project structure compliance"""
        violations = []
        score = 100
        
        # Check required files
        for required_file in config['required_files']:
            file_path = self.project_path / required_file
            if not file_path.exists():
                violations.append({
                    'type': 'missing_file',
                    'file': required_file,
                    'severity': 'high',
                    'message': f'Missing required file: {required_file}'
                })
                score -= 15
        
        # Check required directories
        for required_dir in config['required_dirs']:
            dir_path = self.project_path / required_dir
            if not dir_path.exists():
                violations.append({
                    'type': 'missing_directory',
                    'directory': required_dir,
                    'severity': 'high',
                    'message': f'Missing required directory: {required_dir}'
                })
                score -= 10
        
        return max(0, score), violations
    
    def _check_code_quality(self, config: Dict[str, Any]) -> tuple[float, List[Dict[str, Any]]]:
        """Check code quality compliance"""
        violations = []
        score = 100
        
        # Check Python files
        for py_file in self.project_path.rglob("*.py"):
            if any(exclude in str(py_file) for exclude in ['venv', '.venv', '__pycache__']):
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                # Check file size
                if len(lines) > config['max_file_size']:
                    violations.append({
                        'type': 'file_too_large',
                        'file': str(py_file),
                        'severity': 'medium',
                        'message': f'File too large: {len(lines)} lines (max: {config["max_file_size"]})'
                    })
                    score -= 5
                
                # Check for docstrings
                if config['required_docstrings']:
                    has_docstring = False
                    for line in lines[:10]:  # Check first 10 lines
                        if '"""' in line or "'''" in line:
                            has_docstring = True
                            break
                    
                    if not has_docstring:
                        violations.append({
                            'type': 'missing_docstring',
                            'file': str(py_file),
                            'severity': 'low',
                            'message': 'Missing module docstring'
                        })
                        score -= 2
                
            except Exception:
                continue
        
        return max(0, score), violations
    
    def _check_testing(self, config: Dict[str, Any]) -> tuple[float, List[Dict[str, Any]]]:
        """Check testing compliance"""
        violations = []
        score = 100
        
        # Check for test files
        test_files = list(self.project_path.rglob("test_*.py")) + list(self.project_path.rglob("*_test.py"))
        
        if not test_files:
            violations.append({
                'type': 'no_tests',
                'severity': 'high',
                'message': 'No test files found'
            })
            score -= 50
        
        # Check test types
        test_types = {'unit': 0, 'integration': 0, 'e2e': 0}
        
        for test_file in test_files:
            if 'unit' in str(test_file):
                test_types['unit'] += 1
            elif 'integration' in str(test_file):
                test_types['integration'] += 1
            elif 'e2e' in str(test_file):
                test_types['e2e'] += 1
        
        # Check test pyramid
        total_tests = sum(test_types.values())
        if total_tests > 0:
            unit_ratio = test_types['unit'] / total_tests
            integration_ratio = test_types['integration'] / total_tests
            e2e_ratio = test_types['e2e'] / total_tests
            
            expected_ratios = [0.7, 0.2, 0.1]  # unit, integration, e2e
            
            if abs(unit_ratio - expected_ratios[0]) > 0.1:
                violations.append({
                    'type': 'test_pyramid_violation',
                    'severity': 'medium',
                    'message': f'Unit test ratio: {unit_ratio:.1%} (expected: {expected_ratios[0]:.1%})'
                })
                score -= 10
        
        return max(0, score), violations
    
    def _check_documentation(self, config: Dict[str, Any]) -> tuple[float, List[Dict[str, Any]]]:
        """Check documentation compliance"""
        violations = []
        score = 100
        
        # Check required documentation files
        for required_doc in config['required_docs']:
            doc_path = self.project_path / required_doc
            if not doc_path.exists():
                violations.append({
                    'type': 'missing_documentation',
                    'file': required_doc,
                    'severity': 'medium',
                    'message': f'Missing documentation: {required_doc}'
                })
                score -= 20
        
        # Check code comment ratio
        total_lines = 0
        comment_lines = 0
        
        for py_file in self.project_path.rglob("*.py"):
            if any(exclude in str(py_file) for exclude in ['venv', '.venv', '__pycache__']):
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                total_lines += len(lines)
                comment_lines += sum(1 for line in lines if line.strip().startswith('#'))
                
            except Exception:
                continue
        
        if total_lines > 0:
            comment_ratio = comment_lines / total_lines
            if comment_ratio < config['code_comments_ratio']:
                violations.append({
                    'type': 'insufficient_comments',
                    'severity': 'low',
                    'message': f'Comment ratio: {comment_ratio:.1%} (minimum: {config["code_comments_ratio"]:.1%})'
                })
                score -= 5
        
        return max(0, score), violations
    
    def _check_security(self, config: Dict[str, Any]) -> tuple[float, List[Dict[str, Any]]]:
        """Check security compliance"""
        violations = []
        score = 100
        
        # Check for hardcoded secrets
        secret_patterns = ['password', 'secret', 'key', 'token', 'api_key']
        
        for py_file in self.project_path.rglob("*.py"):
            if any(exclude in str(py_file) for exclude in ['venv', '.venv', '__pycache__']):
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read().lower()
                
                for pattern in secret_patterns:
                    if f'{pattern} =' in content or f'{pattern}:' in content:
                        violations.append({
                            'type': 'hardcoded_secret',
                            'file': str(py_file),
                            'severity': 'high',
                            'message': f'Potential hardcoded secret: {pattern}'
                        })
                        score -= 20
                
            except Exception:
                continue
        
        return max(0, score), violations
    
    def _generate_recommendations(self, violations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate improvement recommendations"""
        recommendations = []
        
        # Group violations by type
        violation_types = {}
        for violation in violations:
            vtype = violation['type']
            if vtype not in violation_types:
                violation_types[vtype] = []
            violation_types[vtype].append(violation)
        
        # Generate recommendations for each violation type
        for vtype, violations_list in violation_types.items():
            if vtype == 'missing_file':
                recommendations.append({
                    'type': 'create_missing_files',
                    'priority': 'high',
                    'description': f'Create {len(violations_list)} missing required files',
                    'action': 'Create README.md, CHANGELOG.md, requirements.txt, setup.py'
                })
            elif vtype == 'missing_directory':
                recommendations.append({
                    'type': 'create_missing_directories',
                    'priority': 'high',
                    'description': f'Create {len(violations_list)} missing required directories',
                    'action': 'Create src/, tests/, docs/ directories'
                })
            elif vtype == 'no_tests':
                recommendations.append({
                    'type': 'create_test_suite',
                    'priority': 'high',
                    'description': 'Create comprehensive test suite',
                    'action': 'Implement unit, integration, and e2e tests'
                })
            elif vtype == 'file_too_large':
                recommendations.append({
                    'type': 'refactor_large_files',
                    'priority': 'medium',
                    'description': f'Refactor {len(violations_list)} oversized files',
                    'action': 'Break large files into smaller, focused modules'
                })
            elif vtype == 'hardcoded_secret':
                recommendations.append({
                    'type': 'secure_secrets',
                    'priority': 'high',
                    'description': f'Secure {len(violations_list)} hardcoded secrets',
                    'action': 'Move secrets to environment variables or config files'
                })
        
        return recommendations
    
    def generate_compliance_report(self, results: Dict[str, Any]) -> str:
        """Generate compliance report"""
        report = f"""
# PDS Compliance Report - {self.project_name}

## 📊 **Overall Compliance Score: {results['compliance_score']:.1f}%**

### **📋 Standards Compliance:**

"""
        
        for standard_name, standard_result in results['standards'].items():
            compliance = standard_result['compliance_percentage']
            violations = len(standard_result['violations'])
            
            status = "✅" if compliance >= 90 else "⚠️" if compliance >= 70 else "❌"
            
            report += f"""
#### **{standard_name.replace('_', ' ').title()}** {status}
- **Compliance**: {compliance:.1f}%
- **Violations**: {violations}
- **Weight**: {standard_result['weight']}%
"""
        
        report += f"""
### **⚠️ Violations Found: {len(results['violations'])}**

"""
        
        for violation in results['violations']:
            severity_icon = "🔴" if violation['severity'] == 'high' else "🟡" if violation['severity'] == 'medium' else "🟢"
            report += f"- {severity_icon} **{violation['type']}**: {violation['message']}\n"
        
        report += f"""
### **💡 Recommendations:**

"""
        
        for rec in results['recommendations']:
            priority_icon = "🔴" if rec['priority'] == 'high' else "🟡" if rec['priority'] == 'medium' else "🟢"
            report += f"- {priority_icon} **{rec['type']}**: {rec['description']}\n"
            report += f"  - Action: {rec['action']}\n"
        
        report += f"""
### **📈 Improvement Plan:**

1. **High Priority**: Address all high-severity violations
2. **Medium Priority**: Refactor oversized files and improve test coverage
3. **Low Priority**: Add documentation and improve code comments

### **🎯 Target Compliance Score: 90%+**

---
*Generated on {results['timestamp']}*
"""
        
        return report

def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        project_path = sys.argv[1]
    else:
        project_path = "."
    
    checker = PDSComplianceChecker(project_path)
    results = checker.check_compliance()
    
    # Generate report
    report = checker.generate_compliance_report(results)
    
    # Save results
    report_path = Path(project_path) / f"pds_compliance_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(report_path, 'w') as f:
        f.write(report)
    
    print(f"📄 Compliance report saved: {report_path}")

if __name__ == "__main__":
    main()
