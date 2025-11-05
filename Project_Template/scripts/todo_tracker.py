#!/usr/bin/env python3
"""
TODO Tracker
============

Comprehensive TODO tracking system for PyCharm integration and CHANGELOG management.
Based on PDS TODO Management Standards v1.8.
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict

@dataclass
class TODOItem:
    """Represents a single TODO item."""
    file_path: str
    line_number: int
    todo_type: str  # TODO, FIXME, HACK, XXX, NOTE
    priority: Optional[str] = None
    description: str = ""
    assignee: Optional[str] = None
    due_date: Optional[str] = None
    raw_line: str = ""

class TODOTracker:
    """Comprehensive TODO tracking system."""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.todo_patterns = {
            'TODO': r'#\s*TODO:?\s*(?:\[([^\]]+)\])?\s*(.+?)(?:\s*-\s*\[([^\]]+)\])?(?:\s*-\s*\[([^\]]+)\])?',
            'FIXME': r'#\s*FIXME:?\s*(?:\[([^\]]+)\])?\s*(.+?)(?:\s*-\s*\[([^\]]+)\])?(?:\s*-\s*\[([^\]]+)\])?',
            'HACK': r'#\s*HACK:?\s*(?:\[([^\]]+)\])?\s*(.+?)(?:\s*-\s*\[([^\]]+)\])?(?:\s*-\s*\[([^\]]+)\])?',
            'XXX': r'#\s*XXX:?\s*(?:\[([^\]]+)\])?\s*(.+?)(?:\s*-\s*\[([^\]]+)\])?(?:\s*-\s*\[([^\]]+)\])?',
            'NOTE': r'#\s*NOTE:?\s*(?:\[([^\]]+)\])?\s*(.+?)(?:\s*-\s*\[([^\]]+)\])?(?:\s*-\s*\[([^\]]+)\])?'
        }
    
    def scan_project(self) -> List[TODOItem]:
        """Scan entire project for TODO items."""
        todos = []
        
        # Scan Python files
        for py_file in self.project_root.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue
            todos.extend(self._scan_file(py_file))
        
        # Scan other relevant files
        for ext in [".js", ".ts", ".jsx", ".tsx", ".java", ".cpp", ".c", ".h"]:
            for file_path in self.project_root.rglob(f"*{ext}"):
                if self._should_skip_file(file_path):
                    continue
                todos.extend(self._scan_file(file_path))
        
        return todos
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped."""
        skip_dirs = {'.git', '__pycache__', '.pytest_cache', 'node_modules', '.venv', 'venv'}
        skip_files = {'build.sh', 'setup.py', 'requirements.txt'}
        
        # Skip if in skip directory
        for part in file_path.parts:
            if part in skip_dirs:
                return True
        
        # Skip if file name in skip list
        if file_path.name in skip_files:
            return True
        
        return False
    
    def _scan_file(self, file_path: Path) -> List[TODOItem]:
        """Scan a single file for TODO items."""
        todos = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
        except Exception as e:
            print(f"Warning: Could not read {file_path}: {e}")
            return todos
        
        for line_num, line in enumerate(lines, 1):
            for todo_type, pattern in self.todo_patterns.items():
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    priority, description, assignee, due_date = match.groups()
                    
                    todo = TODOItem(
                        file_path=str(file_path.relative_to(self.project_root)),
                        line_number=line_num,
                        todo_type=todo_type,
                        priority=priority,
                        description=description.strip(),
                        assignee=assignee,
                        due_date=due_date,
                        raw_line=line.strip()
                    )
                    todos.append(todo)
        
        return todos
    
    def generate_changelog_section(self, todos: List[TODOItem]) -> str:
        """Generate CHANGELOG.md section for TODOs."""
        if not todos:
            return ""
        
        # Group by type
        by_type = {}
        for todo in todos:
            if todo.todo_type not in by_type:
                by_type[todo.todo_type] = []
            by_type[todo.todo_type].append(todo)
        
        # Generate section
        section = "### TODO Items\n\n"
        
        for todo_type in ['TODO', 'FIXME', 'HACK', 'XXX', 'NOTE']:
            if todo_type in by_type:
                section += f"#### {todo_type} Items\n"
                for todo in by_type[todo_type]:
                    priority_str = f" [{todo.priority}]" if todo.priority else ""
                    assignee_str = f" - [{todo.assignee}]" if todo.assignee else ""
                    due_date_str = f" - [{todo.due_date}]" if todo.due_date else ""
                    
                    section += f"- **{todo_type}:{priority_str} {todo.description}**{assignee_str}{due_date_str}\n"
                    section += f"  - File: `{todo.file_path}:{todo.line_number}`\n"
                section += "\n"
        
        return section
    
    def generate_summary(self, todos: List[TODOItem]) -> Dict[str, Any]:
        """Generate TODO summary statistics."""
        summary = {
            'total_todos': len(todos),
            'by_type': {},
            'by_priority': {},
            'by_assignee': {},
            'by_file': {},
            'overdue': [],
            'high_priority': []
        }
        
        for todo in todos:
            # Count by type
            summary['by_type'][todo.todo_type] = summary['by_type'].get(todo.todo_type, 0) + 1
            
            # Count by priority
            if todo.priority:
                summary['by_priority'][todo.priority] = summary['by_priority'].get(todo.priority, 0) + 1
            
            # Count by assignee
            if todo.assignee:
                summary['by_assignee'][todo.assignee] = summary['by_assignee'].get(todo.assignee, 0) + 1
            
            # Count by file
            summary['by_file'][todo.file_path] = summary['by_file'].get(todo.file_path, 0) + 1
            
            # Check for overdue items
            if todo.due_date:
                try:
                    due_date = datetime.strptime(todo.due_date, '%Y-%m-%d')
                    if due_date < datetime.now():
                        summary['overdue'].append(todo)
                except ValueError:
                    pass
            
            # Check for high priority
            if todo.priority == 'HIGH':
                summary['high_priority'].append(todo)
        
        return summary
    
    def print_summary(self, todos: List[TODOItem]):
        """Print TODO summary to console."""
        summary = self.generate_summary(todos)
        
        print("=" * 60)
        print("TODO TRACKING SUMMARY")
        print("=" * 60)
        print(f"Total TODOs: {summary['total_todos']}")
        print()
        
        print("By Type:")
        for todo_type, count in summary['by_type'].items():
            print(f"  {todo_type}: {count}")
        print()
        
        if summary['by_priority']:
            print("By Priority:")
            for priority, count in summary['by_priority'].items():
                print(f"  {priority}: {count}")
            print()
        
        if summary['by_assignee']:
            print("By Assignee:")
            for assignee, count in summary['by_assignee'].items():
                print(f"  {assignee}: {count}")
            print()
        
        if summary['overdue']:
            print("OVERDUE ITEMS:")
            for todo in summary['overdue']:
                print(f"  {todo.todo_type}: {todo.description} - {todo.file_path}:{todo.line_number}")
            print()
        
        if summary['high_priority']:
            print("HIGH PRIORITY ITEMS:")
            for todo in summary['high_priority']:
                print(f"  {todo.todo_type}: {todo.description} - {todo.file_path}:{todo.line_number}")
            print()
    
    def export_to_json(self, todos: List[TODOItem], output_file: str = "todos.json"):
        """Export TODOs to JSON file."""
        data = {
            'scan_date': datetime.now().isoformat(),
            'total_count': len(todos),
            'todos': [asdict(todo) for todo in todos]
        }
        
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"TODO data exported to {output_file}")

def main():
    """Main function for CLI usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description="TODO Tracker for PyCharm Integration")
    parser.add_argument("--project-root", default=".", help="Project root directory")
    parser.add_argument("--export-json", help="Export TODOs to JSON file")
    parser.add_argument("--changelog", action="store_true", help="Generate CHANGELOG section")
    parser.add_argument("--quiet", action="store_true", help="Quiet mode (no console output)")
    
    args = parser.parse_args()
    
    tracker = TODOTracker(args.project_root)
    todos = tracker.scan_project()
    
    if not args.quiet:
        tracker.print_summary(todos)
    
    if args.export_json:
        tracker.export_to_json(todos, args.export_json)
    
    if args.changelog:
        changelog_section = tracker.generate_changelog_section(todos)
        print("\n" + "=" * 60)
        print("CHANGELOG SECTION")
        print("=" * 60)
        print(changelog_section)

if __name__ == "__main__":
    main()

