"""Configuration differ service for comparing device configurations."""

import difflib
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Optional


@dataclass
class DiffLine:
    """Represents a single line in a diff."""
    
    line_type: str  # 'added', 'removed', 'unchanged', 'info'
    content: str
    line_num_old: Optional[int] = None
    line_num_new: Optional[int] = None


@dataclass
class ConfigDiff:
    """Result of a configuration comparison."""
    
    similarity: float  # 0.0 to 1.0
    added_count: int
    removed_count: int
    unchanged_count: int
    lines: list[DiffLine] = field(default_factory=list)
    unified_diff: str = ""
    
    def to_dict(self) -> dict:
        """Convert to dictionary format."""
        return {
            "similarity": round(self.similarity, 2),
            "added_count": self.added_count,
            "removed_count": self.removed_count,
            "unchanged_count": self.unchanged_count,
            "lines": [
                {
                    "type": line.line_type,
                    "content": line.content,
                    "line_num_old": line.line_num_old,
                    "line_num_new": line.line_num_new,
                }
                for line in self.lines
            ],
        }


class ConfigDiffer:
    """Service for comparing device configurations."""
    
    # Default patterns to ignore during comparison (volatile fields)
    DEFAULT_IGNORE_PATTERNS = [
        r'^#.*$',  # Comments starting with #
        r'^!.*$',  # Comments starting with !
        r'^sysname\s+',  # Hostname (when comparing different devices)
        r'^.*timestamp.*$',  # Timestamps (case insensitive)
        r'^.*uptime.*$',  # Uptime information
        r'^.*Time:\s*\w+.*$',  # Time displays
        r'^.*Statistics.*$',  # Statistics lines
        r'^\s*return\s*$',  # Return command at end
    ]
    
    # Section extraction patterns
    SECTION_PATTERNS = {
        'interface': r'(^interface\s+.*$)(.*?)(?=^\S|$)',
        'ospf': r'(^ospf\s+.*$)(.*?)(?=^\S|$)',
        'bgp': r'(^bgp\s+.*$)(.*?)(?=^\S|$)',
        'acl': r'(^acl\s+.*$|.*-acl\s+.*$)(.*?)(?=^\S|$)',
        'vlan': r'(^vlan\s+batch.*$|^vlan\s+\d+.*$)(.*?)(?=^\S|$)',
        'routing': r'(^ip route.*$|^route.*$)(.*?)(?=^\S|$)',
        'snmp': r'(^snmp.*$)(.*?)(?=^\S|$)',
        'ntp': r'(^ntp.*$)(.*?)(?=^\S|$)',
    }
    
    def __init__(self, ignore_patterns: Optional[list[str]] = None):
        """Initialize the config differ.
        
        Args:
            ignore_patterns: Additional regex patterns to ignore during comparison.
        """
        self.ignore_patterns = self.DEFAULT_IGNORE_PATTERNS.copy()
        if ignore_patterns:
            self.ignore_patterns.extend(ignore_patterns)
        self._compiled_patterns = [re.compile(p, re.IGNORECASE) for p in self.ignore_patterns]
    
    def compare_configs(
        self,
        config1: str,
        config2: str,
        config1_name: str = "config1",
        config2_name: str = "config2",
        smart_ignore: bool = False,
        section: Optional[str] = None,
    ) -> ConfigDiff:
        """Compare two configurations and return differences.
        
        Args:
            config1: First configuration text.
            config2: Second configuration text.
            config1_name: Label for first config (used in unified diff).
            config2_name: Label for second config (used in unified diff).
            smart_ignore: If True, filter out volatile fields.
            section: Optional section to compare (e.g., 'interface', 'ospf').
            
        Returns:
            ConfigDiff with comparison results.
        """
        # Extract section if specified
        if section:
            config1 = self._extract_section(config1, section)
            config2 = self._extract_section(config2, section)
        
        # Filter lines if smart ignore is enabled
        if smart_ignore:
            config1 = self._filter_config(config1)
            config2 = self._filter_config(config2)
        
        # Split into lines for comparison
        lines1 = config1.splitlines() if config1 else []
        lines2 = config2.splitlines() if config2 else []
        
        # Calculate similarity score
        similarity = self._calculate_similarity(config1, config2)
        
        # Generate unified diff
        unified = self._generate_unified_diff(
            lines1, lines2, config1_name, config2_name
        )
        
        # Parse diff into structured lines
        diff_lines = self._parse_unified_diff(unified)
        
        # Count changes
        added = sum(1 for line in diff_lines if line.line_type == 'added')
        removed = sum(1 for line in diff_lines if line.line_type == 'removed')
        unchanged = sum(1 for line in diff_lines if line.line_type == 'unchanged')
        
        return ConfigDiff(
            similarity=similarity,
            added_count=added,
            removed_count=removed,
            unchanged_count=unchanged,
            lines=diff_lines,
            unified_diff=unified,
        )
    
    def _extract_section(self, config: str, section: str) -> str:
        """Extract a specific section from configuration.
        
        Args:
            config: Full configuration text.
            section: Section name to extract.
            
        Returns:
            Extracted section or empty string if not found.
        """
        # First try built-in patterns
        section_lower = section.lower()
        
        # Use pattern matching for known sections
        if section_lower in self.SECTION_PATTERNS:
            pattern = self.SECTION_PATTERNS[section_lower]
            matches = re.findall(pattern, config, re.MULTILINE | re.IGNORECASE | re.DOTALL)
            if matches:
                return '\n'.join(''.join(m) for m in matches)
        
        # Fallback: line-by-line section extraction
        lines = config.splitlines()
        filtered_lines = []
        in_section = False
        section_indent = None
        
        for line in lines:
            stripped = line.strip().lower()
            
            # Check if this line starts the section
            if stripped.startswith(section_lower):
                in_section = True
                section_indent = len(line) - len(line.lstrip())
                filtered_lines.append(line)
            elif in_section:
                # Check if we've exited the section
                current_indent = len(line) - len(line.lstrip())
                if line.strip() and current_indent <= section_indent:
                    in_section = False
                    section_indent = None
                else:
                    filtered_lines.append(line)
        
        return '\n'.join(filtered_lines) if filtered_lines else f"# Section '{section}' not found"
    
    def _filter_config(self, config: str) -> str:
        """Filter out volatile fields from configuration.
        
        Args:
            config: Raw configuration text.
            
        Returns:
            Filtered configuration.
        """
        lines = config.splitlines()
        filtered = []
        
        for line in lines:
            stripped = line.strip()
            # Skip empty lines
            if not stripped:
                continue
            # Check against ignore patterns
            if any(pattern.match(stripped) for pattern in self._compiled_patterns):
                continue
            filtered.append(line)
        
        return '\n'.join(filtered)
    
    def _calculate_similarity(self, config1: str, config2: str) -> float:
        """Calculate similarity ratio between two configs.
        
        Args:
            config1: First configuration.
            config2: Second configuration.
            
        Returns:
            Similarity ratio between 0.0 and 1.0.
        """
        if not config1 and not config2:
            return 1.0
        if not config1 or not config2:
            return 0.0
        
        return SequenceMatcher(None, config1, config2).ratio()
    
    def _generate_unified_diff(
        self,
        lines1: list[str],
        lines2: list[str],
        name1: str,
        name2: str,
    ) -> str:
        """Generate unified diff output.
        
        Args:
            lines1: Lines from first config.
            lines2: Lines from second config.
            name1: Label for first config.
            name2: Label for second config.
            
        Returns:
            Unified diff as string.
        """
        diff = difflib.unified_diff(
            lines1,
            lines2,
            fromfile=name1,
            tofile=name2,
            lineterm='',
        )
        return '\n'.join(diff)
    
    def _parse_unified_diff(self, unified_diff: str) -> list[DiffLine]:
        """Parse unified diff into structured DiffLine objects.
        
        Args:
            unified_diff: Unified diff output.
            
        Returns:
            List of DiffLine objects.
        """
        lines = []
        old_line_num = 0
        new_line_num = 0
        
        for line in unified_diff.splitlines():
            if not line:
                continue
                
            # Header lines
            if line.startswith('---') or line.startswith('+++'):
                lines.append(DiffLine(line_type='info', content=line))
            
            # Range info (@@ -old,lines +new,lines @@)
            elif line.startswith('@@'):
                lines.append(DiffLine(line_type='info', content=line))
                # Parse line numbers from range
                match = re.match(r'@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@', line)
                if match:
                    old_line_num = int(match.group(1))
                    new_line_num = int(match.group(3))
            
            # Removed lines
            elif line.startswith('-'):
                lines.append(DiffLine(
                    line_type='removed',
                    content=line[1:],
                    line_num_old=old_line_num,
                ))
                old_line_num += 1
            
            # Added lines
            elif line.startswith('+'):
                lines.append(DiffLine(
                    line_type='added',
                    content=line[1:],
                    line_num_new=new_line_num,
                ))
                new_line_num += 1
            
            # Context lines (unchanged)
            elif line.startswith(' '):
                lines.append(DiffLine(
                    line_type='unchanged',
                    content=line[1:],
                    line_num_old=old_line_num,
                    line_num_new=new_line_num,
                ))
                old_line_num += 1
                new_line_num += 1
            else:
                # Other lines (context)
                lines.append(DiffLine(line_type='unchanged', content=line))
        
        return lines
    
    def audit_configs(
        self,
        configs: dict[str, str],
        group_by: str = 'type',
        threshold: float = 0.9,
    ) -> dict:
        """Audit multiple configurations for consistency.
        
        Args:
            configs: Dictionary mapping device names to their configurations.
            group_by: How to group devices ('type' or 'model').
            threshold: Similarity threshold below which to flag differences.
            
        Returns:
            Audit results with similarity scores and warnings.
        """
        device_names = list(configs.keys())
        results = {
            'device_count': len(device_names),
            'comparisons': [],
            'warnings': [],
            'groups': {},
        }
        
        # Compare all pairs
        for i, name1 in enumerate(device_names):
            for name2 in device_names[i + 1:]:
                diff = self.compare_configs(
                    configs[name1],
                    configs[name2],
                    name1,
                    name2,
                )
                
                comparison = {
                    'device1': name1,
                    'device2': name2,
                    'similarity': diff.similarity,
                    'added': diff.added_count,
                    'removed': diff.removed_count,
                }
                results['comparisons'].append(comparison)
                
                # Flag if below threshold
                if diff.similarity < threshold:
                    results['warnings'].append({
                        'devices': f"{name1} <-> {name2}",
                        'similarity': diff.similarity,
                        'message': f"Significant difference detected ({diff.similarity:.0%} similar)",
                    })
        
        return results


def compare_configs(
    config1: str,
    config2: str,
    config1_name: str = "config1",
    config2_name: str = "config2",
    smart_ignore: bool = False,
    section: Optional[str] = None,
) -> ConfigDiff:
    """Convenience function to compare two configurations.
    
    Args:
        config1: First configuration text.
        config2: Second configuration text.
        config1_name: Label for first config.
        config2_name: Label for second config.
        smart_ignore: If True, filter out volatile fields.
        section: Optional section to compare.
        
    Returns:
        ConfigDiff with comparison results.
    """
    differ = ConfigDiffer()
    return differ.compare_configs(
        config1, config2, config1_name, config2_name, smart_ignore, section
    )


def diff_from_files(
    file1: Path,
    file2: Path,
    smart_ignore: bool = False,
    section: Optional[str] = None,
) -> ConfigDiff:
    """Compare two configuration files.
    
    Args:
        file1: Path to first configuration file.
        file2: Path to second configuration file.
        smart_ignore: If True, filter out volatile fields.
        section: Optional section to compare.
        
    Returns:
        ConfigDiff with comparison results.
    """
    config1 = file1.read_text(encoding='utf-8')
    config2 = file2.read_text(encoding='utf-8')
    
    return compare_configs(
        config1, config2,
        config1_name=str(file1),
        config2_name=str(file2),
        smart_ignore=smart_ignore,
        section=section,
    )
