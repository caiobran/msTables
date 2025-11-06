#!/usr/bin/env python3
"""
TODO Scanner for MSTables

Scans the codebase for TODO comments and generates TODO_IN_CODE.md
and updates the DandE.db with TODO tracking.

Based on PDS TODO Management Standards v1.8.
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime
import sqlite3
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Project root
PROJECT_ROOT = Path(__file__).parent.parent
DANDE_DB_PATH = PROJECT_ROOT / 'data' / 'DandE.db'
TODO_IN_CODE_MD = PROJECT_ROOT / 'TODO_IN_CODE.md'


class TODOItem:
    """Represents a single TODO item."""
    
    def __init__(self, file_path: str, line_number: int, todo_type: str, 
                 content: str, version: str = None, priority: str = None):
        self.file_path = file_path
        self.line_number = line_number
        self.todo_type = todo_type  # TODO, FIXME, HACK, XXX, NOTE
        self.content = content.strip()
        self.version = version
        self.priority = priority
        self.extracted_at = datetime.now()
    
    def __repr__(self):
        return f"TODOItem({self.file_path}:{self.line_number}, {self.todo_type}, {self.content[:50]})"


class TODOScanner:
    """Scans codebase for TODO comments."""
    
    # Patterns for different TODO types
    PATTERNS = {
        'TODO': r'#\s*TODO\s*(?:(\d+\.\d+\.\d+)[:\s]+)?(.+)',
        'FIXME': r'#\s*FIXME\s*(?:(\d+\.\d+\.\d+)[:\s]+)?(.+)',
        'HACK': r'#\s*HACK\s*(?:(\d+\.\d+\.\d+)[:\s]+)?(.+)',
        'XXX': r'#\s*XXX\s*(?:(\d+\.\d+\.\d+)[:\s]+)?(.+)',
        'NOTE': r'#\s*NOTE\s*(?:(\d+\.\d+\.\d+)[:\s]+)?(.+)',
    }
    
    # Files/directories to ignore
    IGNORE_PATTERNS = [
        '**/__pycache__/**',
        '**/node_modules/**',
        '**/.git/**',
        '**/venv/**',
        '**/env/**',
        '**/.venv/**',
        '**/mstables_002/**',  # Will be merged in 1.0.6
        '**/data/**',
        '**/*.pyc',
        '**/*.pyo',
        '**/*.egg-info/**',
    ]
    
    def __init__(self, project_root: Path = PROJECT_ROOT):
        self.project_root = project_root
        self.todos: List[TODOItem] = []
    
    def scan(self) -> List[TODOItem]:
        """Scan the entire project for TODO items."""
        logger.info(f"Scanning project: {self.project_root}")
        
        # Get all Python files
        python_files = list(self.project_root.rglob('*.py'))
        
        # Filter out ignored files
        python_files = [f for f in python_files if not self._should_ignore(f)]
        
        logger.info(f"Found {len(python_files)} Python files to scan")
        
        # Scan each file
        for file_path in python_files:
            try:
                todos = self._scan_file(file_path)
                self.todos.extend(todos)
            except Exception as e:
                logger.error(f"Error scanning {file_path}: {e}")
        
        logger.info(f"Found {len(self.todos)} TODO items")
        return self.todos
    
    def _should_ignore(self, file_path: Path) -> bool:
        """Check if a file should be ignored."""
        file_str = str(file_path)
        for pattern in self.IGNORE_PATTERNS:
            if pattern.replace('**/', '').replace('/**', '') in file_str:
                return True
        return False
    
    def _scan_file(self, file_path: Path) -> List[TODOItem]:
        """Scan a single file for TODO items."""
        todos = []
        rel_path = file_path.relative_to(self.project_root)
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    for todo_type, pattern in self.PATTERNS.items():
                        match = re.search(pattern, line, re.IGNORECASE)
                        if match:
                            version = match.group(1) if match.group(1) else None
                            content = match.group(2) if match.group(2) else match.group(0)
                            
                            # Extract priority if present
                            priority_match = re.search(r'\[(CRITICAL|HIGH|MEDIUM|LOW)\]', content, re.IGNORECASE)
                            priority = priority_match.group(1) if priority_match else None
                            
                            todo = TODOItem(
                                file_path=str(rel_path),
                                line_number=line_num,
                                todo_type=todo_type,
                                content=content,
                                version=version,
                                priority=priority
                            )
                            todos.append(todo)
        except Exception as e:
            logger.warning(f"Could not read {file_path}: {e}")
        
        return todos
    
    def save_to_dande_db(self):
        """Save TODOs to DandE.db."""
        if not DANDE_DB_PATH.exists():
            logger.warning(f"DandE.db not found at {DANDE_DB_PATH}")
            return
        
        try:
            conn = sqlite3.connect(str(DANDE_DB_PATH))
            cursor = conn.cursor()
            
            # Ensure todos table exists
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS todos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL,
                    line_number INTEGER NOT NULL,
                    todo_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    version TEXT,
                    priority TEXT,
                    status TEXT DEFAULT 'OPEN',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            ''')
            
            # Insert or update TODOs
            for todo in self.todos:
                cursor.execute('''
                    INSERT OR REPLACE INTO todos 
                    (file_path, line_number, todo_type, content, version, priority, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, 'OPEN', ?, ?)
                ''', (
                    todo.file_path,
                    todo.line_number,
                    todo.todo_type,
                    todo.content,
                    todo.version,
                    todo.priority,
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))
            
            conn.commit()
            conn.close()
            logger.info(f"Saved {len(self.todos)} TODOs to DandE.db")
        except Exception as e:
            logger.error(f"Error saving to DandE.db: {e}")
    
    def generate_markdown(self) -> str:
        """Generate TODO_IN_CODE.md content."""
        # Group TODOs by version
        by_version: Dict[str, List[TODOItem]] = {}
        by_file: Dict[str, List[TODOItem]] = {}
        
        for todo in self.todos:
            version = todo.version or 'Unversioned'
            if version not in by_version:
                by_version[version] = []
            by_version[version].append(todo)
            
            if todo.file_path not in by_file:
                by_file[todo.file_path] = []
            by_file[todo.file_path].append(todo)
        
        # Generate markdown
        md = f"""# TODO Items Found in Code

This document tracks all TODO comments found in the codebase, organized by version and linked to [PRIORITIZED_TODO_LIST.md](PRIORITIZED_TODO_LIST.md).

**Last Updated**: {datetime.now().strftime('%Y-%m-%d')}  
**Total TODOs**: {len(self.todos)} items found across codebase

---

## Summary Statistics

### By Version
"""
        
        # Add version statistics
        for version in sorted(by_version.keys()):
            count = len(by_version[version])
            md += f"- **{version}**: {count} items\n"
        
        md += f"""
### By Type
"""
        # Count by type
        by_type: Dict[str, int] = {}
        for todo in self.todos:
            by_type[todo.todo_type] = by_type.get(todo.todo_type, 0) + 1
        
        for todo_type, count in sorted(by_type.items()):
            md += f"- **{todo_type}**: {count} items\n"
        
        md += f"""
### By Priority
"""
        # Count by priority
        by_priority: Dict[str, int] = {}
        for todo in self.todos:
            priority = todo.priority or 'Unprioritized'
            by_priority[priority] = by_priority.get(priority, 0) + 1
        
        for priority, count in sorted(by_priority.items()):
            md += f"- **{priority}**: {count} items\n"
        
        md += "\n---\n\n"
        
        # Add detailed TODO list by file
        md += "## Detailed TODO List by File\n\n"
        
        for file_path in sorted(by_file.keys()):
            todos = by_file[file_path]
            md += f"### `{file_path}`\n\n"
            
            for todo in todos:
                md += f"- **Line {todo.line_number}**: `{todo.todo_type}` - {todo.content}\n"
                if todo.version:
                    md += f"  - Version: {todo.version}\n"
                if todo.priority:
                    md += f"  - Priority: {todo.priority}\n"
                md += "\n"
        
        md += """
---

## Related Documents

- [PRIORITIZED_TODO_LIST.md](PRIORITIZED_TODO_LIST.md) - Comprehensive prioritized TODO list
- [DDD_MERGE_PLAN.md](DDD_MERGE_PLAN.md) - Domain-Driven Design merge plan
- [CHANGELOG.md](CHANGELOG.md) - Version history and changes
- [PDS_V2_INTEGRATION_PLAN.md](PDS_V2_INTEGRATION_PLAN.md) - Project Development Standard integration

---

**Note**: This document is auto-generated. To update, run:
```bash
python scripts/todo_scanner.py
```
"""
        
        return md
    
    def save_markdown(self):
        """Save TODO_IN_CODE.md."""
        try:
            md_content = self.generate_markdown()
            with open(TODO_IN_CODE_MD, 'w', encoding='utf-8') as f:
                f.write(md_content)
            logger.info(f"Saved TODO_IN_CODE.md to {TODO_IN_CODE_MD}")
        except Exception as e:
            logger.error(f"Error saving markdown: {e}")


def main():
    """Main entry point."""
    scanner = TODOScanner()
    todos = scanner.scan()
    
    # Save to database
    scanner.save_to_dande_db()
    
    # Save markdown
    scanner.save_markdown()
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"TODO Scanner Summary")
    print(f"{'='*60}")
    print(f"Total TODOs found: {len(todos)}")
    print(f"Files scanned: {len(set(t.file_path for t in todos))}")
    print(f"\nBy type:")
    by_type = {}
    for todo in todos:
        by_type[todo.todo_type] = by_type.get(todo.todo_type, 0) + 1
    for todo_type, count in sorted(by_type.items()):
        print(f"  {todo_type}: {count}")
    print(f"\nResults saved to:")
    print(f"  - TODO_IN_CODE.md")
    print(f"  - data/DandE.db (todos table)")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    main()

