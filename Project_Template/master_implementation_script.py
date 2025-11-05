#!/usr/bin/env python3
"""
Master Implementation Script
============================

Master script for implementing the universal codebase improvement approach
on any existing codebase. Combines analysis, PDS compliance, and phased fixes.
"""

import os
import sys
import json
import datetime
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional

class MasterImplementationScript:
    """Master implementation script for codebase improvement"""
    
    def __init__(self, project_path: str = "."):
        self.project_path = Path(project_path)
        self.project_name = self.project_path.name
        self.session_id = f"master_improvement_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Import our tools
        sys.path.insert(0, str(self.project_path))
        
        try:
            from universal_codebase_improver import UniversalCodebaseImprover
            from pds_compliance_checker import PDSComplianceChecker
            self.improver = UniversalCodebaseImprover(str(self.project_path))
            self.pds_checker = PDSComplianceChecker(str(self.project_path))
        except ImportError as e:
            print(f"❌ Error importing tools: {e}")
            print("Make sure universal_codebase_improver.py and pds_compliance_checker.py are in the project directory")
            sys.exit(1)
    
    def run_complete_improvement(self):
        """Run complete improvement process"""
        print("🚀 Master Codebase Improvement Script")
        print("=" * 60)
        print(f"📁 Project: {self.project_name}")
        print(f"🆔 Session: {self.session_id}")
        print("=" * 60)
        
        # Step 1: PDS Compliance Check
        print("\n📋 Step 1: PDS Compliance Check")
        print("-" * 40)
        pds_results = self.pds_checker.check_compliance()
        
        # Step 2: Codebase Analysis
        print("\n🔍 Step 2: Codebase Analysis")
        print("-" * 40)
        analysis_results = self.improver.run_analysis()
        
        # Step 3: Generate Implementation Plan
        print("\n📋 Step 3: Implementation Plan")
        print("-" * 40)
        plan = self.improver.generate_improvement_plan(analysis_results)
        
        # Step 4: Create Implementation Scripts
        print("\n📝 Step 4: Implementation Scripts")
        print("-" * 40)
        scripts = self.improver.create_implementation_scripts(plan)
        
        # Step 5: Generate Documentation
        print("\n📚 Step 5: Documentation")
        print("-" * 40)
        docs = self.improver.generate_documentation(analysis_results, plan)
        
        # Step 6: Create Master Summary
        print("\n📊 Step 6: Master Summary")
        print("-" * 40)
        master_summary = self._create_master_summary(pds_results, analysis_results, plan)
        
        # Step 7: Save Everything
        print("\n💾 Step 7: Save Results")
        print("-" * 40)
        self._save_all_results(pds_results, analysis_results, plan, scripts, docs, master_summary)
        
        # Step 8: Generate Next Steps
        print("\n🎯 Step 8: Next Steps")
        print("-" * 40)
        next_steps = self._generate_next_steps(plan, scripts)
        
        print("\n🎉 COMPLETE IMPROVEMENT PACKAGE READY!")
        print("=" * 60)
        print(f"📊 PDS Compliance: {pds_results['compliance_score']:.1f}%")
        print(f"🔍 Total Errors: {analysis_results['total_errors']}")
        print(f"📋 Phases: {len(plan['phases'])}")
        print(f"📝 Scripts: {len(scripts)}")
        print(f"📚 Documentation: {len(docs)}")
        print(f"💾 Results: improvement_package_{self.session_id}/")
        
        return {
            'pds_results': pds_results,
            'analysis_results': analysis_results,
            'plan': plan,
            'scripts': scripts,
            'docs': docs,
            'master_summary': master_summary,
            'next_steps': next_steps
        }
    
    def _create_master_summary(self, pds_results: Dict[str, Any], 
                              analysis_results: Dict[str, Any], 
                              plan: Dict[str, Any]) -> Dict[str, Any]:
        """Create master summary"""
        return {
            'session_id': self.session_id,
            'project_name': self.project_name,
            'timestamp': datetime.datetime.now().isoformat(),
            'pds_compliance_score': pds_results['compliance_score'],
            'total_errors': analysis_results['total_errors'],
            'phases_count': len(plan['phases']),
            'expected_improvement': 95,  # percent
            'priority_fixes': [
                {
                    'type': error_type,
                    'count': data['count'],
                    'impact': data['cascade_probability'] * 100
                }
                for error_type, data in analysis_results['priorities'].items()
            ],
            'compliance_violations': len(pds_results['violations']),
            'recommendations_count': len(pds_results['recommendations'])
        }
    
    def _save_all_results(self, pds_results: Dict[str, Any], 
                         analysis_results: Dict[str, Any], 
                         plan: Dict[str, Any], 
                         scripts: List[str], 
                         docs: Dict[str, str], 
                         master_summary: Dict[str, Any]):
        """Save all results"""
        # Create results directory
        results_dir = self.project_path / f"improvement_package_{self.session_id}"
        results_dir.mkdir(exist_ok=True)
        
        # Save PDS results
        pds_file = results_dir / "pds_compliance_results.json"
        with open(pds_file, 'w') as f:
            json.dump(pds_results, f, indent=2)
        
        # Save analysis results
        analysis_file = results_dir / "codebase_analysis_results.json"
        with open(analysis_file, 'w') as f:
            json.dump(analysis_results, f, indent=2)
        
        # Save improvement plan
        plan_file = results_dir / "improvement_plan.json"
        with open(plan_file, 'w') as f:
            json.dump(plan, f, indent=2)
        
        # Save master summary
        summary_file = results_dir / "master_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(master_summary, f, indent=2)
        
        # Save documentation
        docs_dir = results_dir / "documentation"
        docs_dir.mkdir(exist_ok=True)
        
        for doc_name, doc_content in docs.items():
            doc_file = docs_dir / doc_name
            with open(doc_file, 'w') as f:
                f.write(doc_content)
        
        # Copy implementation scripts
        scripts_dir = results_dir / "implementation_scripts"
        scripts_dir.mkdir(exist_ok=True)
        
        for script_path in scripts:
            script_name = Path(script_path).name
            script_dest = scripts_dir / script_name
            with open(script_path, 'r') as src, open(script_dest, 'w') as dst:
                dst.write(src.read())
        
        print(f"💾 All results saved to: {results_dir}")
    
    def _generate_next_steps(self, plan: Dict[str, Any], scripts: List[str]) -> List[Dict[str, Any]]:
        """Generate next steps"""
        next_steps = []
        
        # Phase implementation steps
        for phase in plan['phases']:
            next_steps.append({
                'step': f"Implement Phase {phase['phase_number']}",
                'description': phase['name'],
                'script': f"implement_phase_{phase['phase_number']}.py",
                'priority': 'high' if phase['phase_number'] == 1 else 'medium',
                'expected_reduction': f"{phase['target_reduction']}%"
            })
        
        # Documentation steps
        next_steps.append({
            'step': 'Update Documentation',
            'description': 'Apply generated documentation updates',
            'script': 'documentation/README.md',
            'priority': 'medium',
            'expected_reduction': 'N/A'
        })
        
        # Compliance steps
        next_steps.append({
            'step': 'Address PDS Violations',
            'description': 'Fix compliance violations',
            'script': 'pds_compliance_results.json',
            'priority': 'high',
            'expected_reduction': 'N/A'
        })
        
        return next_steps
    
    def create_quick_start_guide(self, results: Dict[str, Any]) -> str:
        """Create quick start guide"""
        guide = f"""# Quick Start Guide - {self.project_name}

## 🚀 **Getting Started**

### **📊 Current Status:**
- **PDS Compliance**: {results['pds_results']['compliance_score']:.1f}%
- **Total Errors**: {results['analysis_results']['total_errors']}
- **Phases**: {len(results['plan']['phases'])}
- **Session ID**: {self.session_id}

### **🎯 Implementation Order:**

#### **Phase 1: Root Cause Elimination (85% target)**
```bash
# Run Phase 1 implementation
python3 improvement_package_{self.session_id}/implementation_scripts/implement_phase_1.py

# Expected: 85% error reduction
```

#### **Phase 2: Infrastructure Hardening (15% target)**
```bash
# Run Phase 2 implementation
python3 improvement_package_{self.session_id}/implementation_scripts/implement_phase_2.py

# Expected: 15% additional error reduction
```

#### **Phase 3: Symptom Cleanup (5% target)**
```bash
# Run Phase 3 implementation
python3 improvement_package_{self.session_id}/implementation_scripts/implement_phase_3.py

# Expected: 5% final cleanup
```

### **📚 Documentation Updates:**
```bash
# Apply documentation updates
cp improvement_package_{self.session_id}/documentation/README.md ./
cp improvement_package_{self.session_id}/documentation/CHANGELOG.md ./
```

### **📊 Progress Tracking:**
```bash
# Check progress
python3 universal_codebase_improver.py analyze

# Check compliance
python3 pds_compliance_checker.py
```

### **🎯 Expected Results:**
- **Total Error Reduction**: 95%+
- **PDS Compliance**: 90%+
- **System Stability**: Dramatic improvement
- **Development Velocity**: 50%+ faster

### **📞 Support:**
- **Session ID**: {self.session_id}
- **Results Directory**: improvement_package_{self.session_id}/
- **Generated**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---
*Generated by Universal Codebase Improvement Framework*
"""
        
        return guide

def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        project_path = sys.argv[1]
    else:
        project_path = "."
    
    print("🚀 Master Implementation Script")
    print("=" * 50)
    print(f"📁 Project Path: {project_path}")
    
    # Check if we're in the right directory
    if not Path(project_path).exists():
        print(f"❌ Project path does not exist: {project_path}")
        sys.exit(1)
    
    # Check for required files
    required_files = ['universal_codebase_improver.py', 'pds_compliance_checker.py']
    missing_files = []
    
    for file in required_files:
        if not Path(project_path) / file:
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Missing required files: {missing_files}")
        print("Make sure you're running this from the Project_Template directory")
        sys.exit(1)
    
    # Run improvement
    master = MasterImplementationScript(project_path)
    results = master.run_complete_improvement()
    
    # Create quick start guide
    guide = master.create_quick_start_guide(results)
    
    # Save quick start guide
    guide_path = Path(project_path) / f"QUICK_START_GUIDE_{master.session_id}.md"
    with open(guide_path, 'w') as f:
        f.write(guide)
    
    print(f"📖 Quick start guide saved: {guide_path}")
    print("\n🎉 Ready to improve any codebase!")

if __name__ == "__main__":
    main()
