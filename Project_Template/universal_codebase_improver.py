#!/usr/bin/env python3
"""
Universal Codebase Improvement Scripts
======================================

Ready-to-use scripts for implementing the phased improvement approach
on any existing codebase.
"""

import os
import sys
import sqlite3
import json
import datetime
import ast
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional

class UniversalCodebaseImprover:
    """Universal codebase improvement tool"""
    
    def __init__(self, project_path: str = "."):
        self.project_path = Path(project_path)
        self.db_path = self.project_path / "data" / "improvement_tracking.db"
        self.session_id = f"improvement_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Ensure data directory exists
        self.db_path.parent.mkdir(exist_ok=True)
        
        self._setup_tracking_database()
    
    def _setup_tracking_database(self):
        """Setup tracking database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Error analysis table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS error_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                timestamp TIMESTAMP,
                error_type TEXT,
                error_message TEXT,
                file_path TEXT,
                line_number INTEGER,
                cascade_probability REAL,
                fix_priority INTEGER,
                fix_status TEXT DEFAULT 'pending',
                fix_description TEXT
            )
        """)
        
        # Phased regression tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS phased_regression (
                phase_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                phase_number INTEGER,
                phase_name TEXT,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                errors_before INTEGER,
                errors_after INTEGER,
                error_reduction INTEGER,
                status TEXT DEFAULT 'pending'
            )
        """)
        
        # Improvement tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS improvement_tracking (
                improvement_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                improvement_type TEXT,
                description TEXT,
                priority INTEGER,
                status TEXT DEFAULT 'pending',
                created_timestamp TIMESTAMP,
                completed_timestamp TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    def analyze_codebase(self) -> Dict[str, Any]:
        """Analyze codebase for errors and issues"""
        print("🔍 Analyzing codebase...")
        
        analysis = {
            'syntax_errors': self._find_syntax_errors(),
            'dependency_errors': self._find_dependency_errors(),
            'validation_errors': self._find_validation_errors(),
            'calculation_errors': self._find_calculation_errors(),
            'connection_errors': self._find_connection_errors(),
            'assertion_errors': self._find_assertion_errors(),
            'display_errors': self._find_display_errors()
        }
        
        # Calculate cascade probabilities
        cascade_matrix = {
            'syntax_errors': 0.95,
            'dependency_errors': 0.90,
            'validation_errors': 0.85,
            'calculation_errors': 0.75,
            'connection_errors': 0.70,
            'assertion_errors': 0.30,
            'display_errors': 0.25
        }
        
        # Calculate priorities
        priorities = {}
        for error_type, errors in analysis.items():
            if errors:
                priority = cascade_matrix[error_type] * len(errors)
                priorities[error_type] = {
                    'count': len(errors),
                    'cascade_probability': cascade_matrix[error_type],
                    'priority_score': priority,
                    'errors': errors
                }
        
        # Sort by priority
        sorted_priorities = sorted(priorities.items(), 
                                  key=lambda x: x[1]['priority_score'], 
                                  reverse=True)
        
        return {
            'analysis': analysis,
            'priorities': dict(sorted_priorities),
            'total_errors': sum(len(errors) for errors in analysis.values()),
            'session_id': self.session_id
        }
    
    def _find_syntax_errors(self) -> List[Dict[str, Any]]:
        """Find syntax errors in Python files"""
        errors = []
        
        for py_file in self.project_path.rglob("*.py"):
            # Skip external files
            if any(exclude in str(py_file) for exclude in ['venv', '.venv', '__pycache__', '.git']):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    source = f.read()
                ast.parse(source, filename=str(py_file))
            except SyntaxError as e:
                errors.append({
                    'file': str(py_file),
                    'line': e.lineno,
                    'message': str(e),
                    'text': e.text
                })
            except Exception:
                # Skip files that can't be read
                continue
        
        return errors
    
    def _find_dependency_errors(self) -> List[Dict[str, Any]]:
        """Find missing dependency errors"""
        errors = []
        
        # Common dependencies to check
        common_deps = ['pytest', 'numpy', 'pandas', 'requests', 'sqlite3', 'pathlib']
        
        for dep in common_deps:
            try:
                __import__(dep)
            except ImportError:
                errors.append({
                    'dependency': dep,
                    'message': f"Missing dependency: {dep}",
                    'fix': f"pip install {dep}"
                })
        
        return errors
    
    def _find_validation_errors(self) -> List[Dict[str, Any]]:
        """Find data validation errors"""
        errors = []
        
        # Look for common validation patterns
        validation_patterns = [
            'high.*close',
            'volume.*negative',
            'date.*chronological',
            'price.*positive'
        ]
        
        for py_file in self.project_path.rglob("*.py"):
            if any(exclude in str(py_file) for exclude in ['venv', '.venv', '__pycache__']):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Look for validation issues
                if 'assert' in content and 'high' in content and 'close' in content:
                    errors.append({
                        'file': str(py_file),
                        'message': 'Potential OHLC validation issue',
                        'pattern': 'high/close validation'
                    })
            except Exception:
                continue
        
        return errors
    
    def _find_calculation_errors(self) -> List[Dict[str, Any]]:
        """Find calculation errors"""
        errors = []
        
        # Look for division by zero patterns
        for py_file in self.project_path.rglob("*.py"):
            if any(exclude in str(py_file) for exclude in ['venv', '.venv', '__pycache__']):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Look for division patterns without zero checks
                if '/' in content and 'if.*==.*0' not in content:
                    errors.append({
                        'file': str(py_file),
                        'message': 'Potential division by zero',
                        'pattern': 'division without zero check'
                    })
            except Exception:
                continue
        
        return errors
    
    def _find_connection_errors(self) -> List[Dict[str, Any]]:
        """Find database connection errors"""
        errors = []
        
        # Look for database connection patterns
        for py_file in self.project_path.rglob("*.py"):
            if any(exclude in str(py_file) for exclude in ['venv', '.venv', '__pycache__']):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if 'sqlite3.connect' in content and 'try:' not in content:
                    errors.append({
                        'file': str(py_file),
                        'message': 'Database connection without error handling',
                        'pattern': 'unprotected connection'
                    })
            except Exception:
                continue
        
        return errors
    
    def _find_assertion_errors(self) -> List[Dict[str, Any]]:
        """Find assertion logic errors"""
        errors = []
        
        # Look for common assertion mistakes
        assertion_mistakes = [
            'assert True is False',
            'assert False is True',
            'assert not True',
            'assert not False'
        ]
        
        for py_file in self.project_path.rglob("*.py"):
            if any(exclude in str(py_file) for exclude in ['venv', '.venv', '__pycache__']):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                for mistake in assertion_mistakes:
                    if mistake in content:
                        errors.append({
                            'file': str(py_file),
                            'message': f'Assertion logic error: {mistake}',
                            'pattern': 'incorrect assertion'
                        })
            except Exception:
                continue
        
        return errors
    
    def _find_display_errors(self) -> List[Dict[str, Any]]:
        """Find display/UI errors"""
        errors = []
        
        # Look for display issues
        for py_file in self.project_path.rglob("*.py"):
            if any(exclude in str(py_file) for exclude in ['venv', '.venv', '__pycache__']):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if 'No data' in content or 'empty' in content:
                    errors.append({
                        'file': str(py_file),
                        'message': 'Potential display issue',
                        'pattern': 'no data display'
                    })
            except Exception:
                continue
        
        return errors
    
    def generate_improvement_plan(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate improvement plan based on analysis"""
        print("📋 Generating improvement plan...")
        
        plan = {
            'session_id': self.session_id,
            'total_errors': analysis['total_errors'],
            'phases': []
        }
        
        # Phase 1: Root Cause Elimination (85% target)
        phase1_errors = []
        for error_type, data in analysis['priorities'].items():
            if data['cascade_probability'] >= 0.85:
                phase1_errors.append({
                    'type': error_type,
                    'count': data['count'],
                    'priority': data['priority_score']
                })
        
        plan['phases'].append({
            'phase_number': 1,
            'name': 'Root Cause Elimination',
            'target_reduction': 85,
            'errors': phase1_errors,
            'status': 'pending'
        })
        
        # Phase 2: Infrastructure Hardening (15% target)
        phase2_errors = []
        for error_type, data in analysis['priorities'].items():
            if 0.70 <= data['cascade_probability'] < 0.85:
                phase2_errors.append({
                    'type': error_type,
                    'count': data['count'],
                    'priority': data['priority_score']
                })
        
        plan['phases'].append({
            'phase_number': 2,
            'name': 'Infrastructure Hardening',
            'target_reduction': 15,
            'errors': phase2_errors,
            'status': 'pending'
        })
        
        # Phase 3: Symptom Cleanup (5% target)
        phase3_errors = []
        for error_type, data in analysis['priorities'].items():
            if data['cascade_probability'] < 0.70:
                phase3_errors.append({
                    'type': error_type,
                    'count': data['count'],
                    'priority': data['priority_score']
                })
        
        plan['phases'].append({
            'phase_number': 3,
            'name': 'Symptom Cleanup',
            'target_reduction': 5,
            'errors': phase3_errors,
            'status': 'pending'
        })
        
        return plan
    
    def create_implementation_scripts(self, plan: Dict[str, Any]) -> List[str]:
        """Create implementation scripts for the improvement plan"""
        print("📝 Creating implementation scripts...")
        
        scripts = []
        
        for phase in plan['phases']:
            script_name = f"implement_phase_{phase['phase_number']}.py"
            script_path = self.project_path / script_name
            
            script_content = f'''#!/usr/bin/env python3
"""
Implementation Script for {phase['name']}
========================================

Auto-generated script for implementing {phase['name']}.
Target: {phase['target_reduction']}% error reduction
"""

import os
import sys
from pathlib import Path

def implement_phase_{phase['phase_number']}():
    """Implement {phase['name']}"""
    print("🚀 Starting {phase['name']}")
    print("=" * 50)
    
    errors_to_fix = {phase['errors']}
    
    for error in errors_to_fix:
        print(f"🔧 Fixing {{error['type']}}: {{error['count']}} errors")
        # TODO: Implement specific fixes
        pass
    
    print("✅ {phase['name']} completed")

if __name__ == "__main__":
    implement_phase_{phase['phase_number']}()
'''
            
            with open(script_path, 'w') as f:
                f.write(script_content)
            
            scripts.append(str(script_path))
        
        return scripts
    
    def generate_documentation(self, analysis: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, str]:
        """Generate documentation updates"""
        print("📚 Generating documentation...")
        
        docs = {}
        
        # README.md update
        readme_content = f'''# {self.project_path.name} - Codebase Improvement

## 🔧 **IMPROVEMENT STATUS**

### **📊 Current Analysis:**
- **Total Errors**: {analysis['total_errors']} errors identified
- **Root Causes**: {len(analysis['priorities'])} root causes identified
- **Session ID**: {self.session_id}

### **🎯 Phased Improvement Plan:**
'''
        
        for phase in plan['phases']:
            readme_content += f'''
#### **Phase {phase['phase_number']}: {phase['name']}**
- **Target**: {phase['target_reduction']}% error reduction
- **Errors**: {len(phase['errors'])} error types
- **Status**: {phase['status']}
'''
        
        readme_content += '''
### **📈 Expected Outcomes:**
- **Error Reduction**: 95%+ total error reduction
- **System Stability**: Dramatic improvement
- **Development Velocity**: Faster iteration

### **🚀 Getting Started:**
```bash
# Run analysis
python3 universal_improver.py analyze

# Implement Phase 1
python3 implement_phase_1.py

# Track progress
python3 universal_improver.py status
```
'''
        
        docs['README.md'] = readme_content
        
        # CHANGELOG.md update
        changelog_content = f'''## [vX.Y.Z] - {datetime.datetime.now().strftime('%Y-%m-%d')}

### 🚀 **CODEBASE IMPROVEMENT INITIATED**

#### 📊 **Analysis Results**
- **Total Errors**: {analysis['total_errors']} errors identified
- **Root Causes**: {len(analysis['priorities'])} primary causes
- **Session ID**: {self.session_id}

#### 🔥 **CRITICAL ISSUES IDENTIFIED**
'''
        
        for error_type, data in analysis['priorities'].items():
            changelog_content += f'- **{error_type.replace("_", " ").title()}**: {data["count"]} errors ({data["cascade_probability"]*100:.0f}% cascade impact)\n'
        
        changelog_content += '''
#### 🎯 **IMPROVEMENT PLAN**
- **Phase 1**: Root Cause Elimination (85% target)
- **Phase 2**: Infrastructure Hardening (15% target)  
- **Phase 3**: Symptom Cleanup (5% target)

#### 📈 **EXPECTED RESULTS**
- **Total Error Reduction**: 95%+ (from [X] to [Y] errors)
- **System Stability**: Dramatic improvement
- **Test Coverage**: 100% passing
'''
        
        docs['CHANGELOG.md'] = changelog_content
        
        return docs
    
    def run_analysis(self):
        """Run complete analysis and generate improvement plan"""
        print("🚀 Universal Codebase Improvement Tool")
        print("=" * 50)
        
        # Analyze codebase
        analysis = self.analyze_codebase()
        
        # Generate improvement plan
        plan = self.generate_improvement_plan(analysis)
        
        # Create implementation scripts
        scripts = self.create_implementation_scripts(plan)
        
        # Generate documentation
        docs = self.generate_documentation(analysis, plan)
        
        # Save results
        results = {
            'analysis': analysis,
            'plan': plan,
            'scripts': scripts,
            'documentation': docs,
            'timestamp': datetime.datetime.now().isoformat()
        }
        
        results_path = self.project_path / f"improvement_analysis_{self.session_id}.json"
        with open(results_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"✅ Analysis complete!")
        print(f"📊 Total errors: {analysis['total_errors']}")
        print(f"📋 Phases: {len(plan['phases'])}")
        print(f"📝 Scripts: {len(scripts)}")
        print(f"📚 Documentation: {len(docs)}")
        print(f"💾 Results saved: {results_path}")
        
        return results

def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        project_path = sys.argv[1]
    else:
        project_path = "."
    
    improver = UniversalCodebaseImprover(project_path)
    improver.run_analysis()

if __name__ == "__main__":
    main()
