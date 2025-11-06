"""
Nano Versioning System

Manages version numbers following nano versioning:
- 1.0.1, 1.0.2, ..., 1.0.9
- Then 1.1.0, 1.1.1, ..., 1.1.9
- Then 1.2.0, etc.

Integrates with CHANGELOG.md for version tracking
"""

import re
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)


class VersionManager:
    """Manages nano versioning for the project"""
    
    VERSION_FILE = Path("VERSION")
    PYPROJECT_FILE = Path("pyproject.toml")
    
    def __init__(self):
        """Initialize version manager"""
        self.current_version = self.get_current_version()
    
    def get_current_version(self) -> str:
        """Get current version from VERSION file or pyproject.toml"""
        # Try VERSION file first
        if self.VERSION_FILE.exists():
            version = self.VERSION_FILE.read_text().strip()
            if self._is_valid_version(version):
                return version
        
        # Try pyproject.toml
        if self.PYPROJECT_FILE.exists():
            content = self.PYPROJECT_FILE.read_text()
            match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
            if match:
                version = match.group(1)
                if self._is_valid_version(version):
                    return version
        
        # Default version
        return "1.0.0"
    
    def _is_valid_version(self, version: str) -> bool:
        """Check if version string is valid (X.Y.Z format)"""
        pattern = r'^\d+\.\d+\.\d+$'
        return bool(re.match(pattern, version))
    
    def _parse_version(self, version: str) -> Tuple[int, int, int]:
        """Parse version string into (major, minor, patch) tuple"""
        parts = version.split('.')
        return (int(parts[0]), int(parts[1]), int(parts[2]))
    
    def _format_version(self, major: int, minor: int, patch: int) -> str:
        """Format version tuple into string"""
        return f"{major}.{minor}.{patch}"
    
    def increment_nano(self) -> str:
        """Increment nano version (patch version)"""
        major, minor, patch = self._parse_version(self.current_version)
        
        # If patch is 9, increment minor and reset patch to 0
        if patch == 9:
            minor += 1
            patch = 0
        else:
            patch += 1
        
        new_version = self._format_version(major, minor, patch)
        self.current_version = new_version
        return new_version
    
    def increment_minor(self) -> str:
        """Increment minor version and reset patch"""
        major, minor, patch = self._parse_version(self.current_version)
        minor += 1
        patch = 0
        new_version = self._format_version(major, minor, patch)
        self.current_version = new_version
        return new_version
    
    def increment_major(self) -> str:
        """Increment major version and reset minor and patch"""
        major, minor, patch = self._parse_version(self.current_version)
        major += 1
        minor = 0
        patch = 0
        new_version = self._format_version(major, minor, patch)
        self.current_version = new_version
        return new_version
    
    def save_version(self, version: Optional[str] = None, description: str = "", 
                     git_commit_hash: str = "", git_branch: str = ""):
        """Save version to VERSION file, pyproject.toml, and CHANGELOG.md"""
        version = version or self.current_version
        
        # Save to VERSION file
        self.VERSION_FILE.write_text(f"{version}\n")
        
        # Update pyproject.toml
        if self.PYPROJECT_FILE.exists():
            content = self.PYPROJECT_FILE.read_text()
            updated = re.sub(
                r'version\s*=\s*["\'][^"\']+["\']',
                f'version = "{version}"',
                content
            )
            self.PYPROJECT_FILE.write_text(updated)
        
        # Update CHANGELOG.md
        self._update_changelog(version, description, git_commit_hash, git_branch)
        
        logging.info(f"Version saved: {version}")
    
    def _update_changelog(self, version: str, description: str = "",
                         git_commit_hash: str = "", git_branch: str = ""):
        """Update CHANGELOG.md with new version entry"""
        changelog_path = Path("CHANGELOG.md")
        
        if not changelog_path.exists():
            logging.warning("CHANGELOG.md not found, skipping update")
            return
        
        content = changelog_path.read_text()
        date_str = datetime.now().strftime("%Y-%m-%d")
        
        # Find the [Unreleased] section
        unreleased_pattern = r'## \[Unreleased\](.*?)(?=## \[|\Z)'
        
        # Create new version entry
        version_entry = f"""## [{version}] - {date_str}

### Added
{description if description else "- Version bump"}

### Changed
- Updated version to {version}

### Technical
- Git commit: {git_commit_hash if git_commit_hash else "N/A"}
- Git branch: {git_branch if git_branch else "N/A"}

---

"""
        
        # Insert new version entry after [Unreleased]
        if re.search(r'## \[Unreleased\]', content):
            # Insert after [Unreleased] section
            content = re.sub(
                r'(## \[Unreleased\].*?\n---\n)',
                r'\1\n' + version_entry,
                content,
                flags=re.DOTALL
            )
        else:
            # Add at the beginning if [Unreleased] doesn't exist
            content = f"## [Unreleased]\n\n### Added\n\n---\n\n{version_entry}" + content
        
        changelog_path.write_text(content)
        logging.info(f"CHANGELOG.md updated with version {version}")
    
    def get_next_version(self) -> str:
        """Get next version without incrementing"""
        major, minor, patch = self._parse_version(self.current_version)
        
        if patch == 9:
            return self._format_version(major, minor + 1, 0)
        else:
            return self._format_version(major, minor, patch + 1)


if __name__ == "__main__":
    vm = VersionManager()
    print(f"Current version: {vm.get_current_version()}")
    print(f"Next version: {vm.get_next_version()}")
    new_version = vm.increment_nano()
    print(f"Incremented to: {new_version}")
    vm.save_version()

