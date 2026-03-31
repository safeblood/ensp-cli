"""Tests for config differ service."""

import pytest
from pathlib import Path

from ensp_cli.services.config_differ import (
    ConfigDiffer,
    ConfigDiff,
    DiffLine,
    compare_configs,
    diff_from_files,
)


class TestDiffLine:
    """Tests for DiffLine dataclass."""

    def test_diff_line_creation(self):
        """Test creating a DiffLine."""
        line = DiffLine(line_type='added', content='test content', line_num_new=5)
        assert line.line_type == 'added'
        assert line.content == 'test content'
        assert line.line_num_new == 5
        assert line.line_num_old is None


class TestConfigDiff:
    """Tests for ConfigDiff dataclass."""

    def test_config_diff_creation(self):
        """Test creating a ConfigDiff."""
        lines = [
            DiffLine(line_type='added', content='new line'),
            DiffLine(line_type='removed', content='old line'),
        ]
        diff = ConfigDiff(
            similarity=0.85,
            added_count=1,
            removed_count=1,
            unchanged_count=10,
            lines=lines,
            unified_diff='--- a\n+++ b\n@@ -1 +1 @@\n-old line\n+new line',
        )
        assert diff.similarity == 0.85
        assert diff.added_count == 1
        assert diff.removed_count == 1
        assert diff.unchanged_count == 10
        assert len(diff.lines) == 2

    def test_config_diff_to_dict(self):
        """Test converting ConfigDiff to dictionary."""
        lines = [
            DiffLine(line_type='added', content='new line', line_num_new=1),
        ]
        diff = ConfigDiff(
            similarity=0.95,
            added_count=1,
            removed_count=0,
            unchanged_count=5,
            lines=lines,
        )
        result = diff.to_dict()
        assert result['similarity'] == 0.95
        assert result['added_count'] == 1
        assert result['removed_count'] == 0
        assert result['unchanged_count'] == 5
        assert len(result['lines']) == 1
        assert result['lines'][0]['type'] == 'added'
        assert result['lines'][0]['content'] == 'new line'


class TestConfigDiffer:
    """Tests for ConfigDiffer class."""

    def test_init_default_patterns(self):
        """Test initialization with default ignore patterns."""
        differ = ConfigDiffer()
        assert len(differ.ignore_patterns) > 0
        assert any('sysname' in p for p in differ.ignore_patterns)
        assert any('timestamp' in p for p in differ.ignore_patterns)

    def test_init_custom_patterns(self):
        """Test initialization with custom ignore patterns."""
        custom_patterns = [r'^custom-pattern$']
        differ = ConfigDiffer(ignore_patterns=custom_patterns)
        assert any('custom-pattern' in p for p in differ.ignore_patterns)

    def test_compare_configs_identical(self):
        """Test comparing identical configs."""
        config = "interface GigabitEthernet0/0/1\n ip address 192.168.1.1 255.255.255.0"
        differ = ConfigDiffer()
        result = differ.compare_configs(config, config)
        
        assert result.similarity == 1.0
        assert result.added_count == 0
        assert result.removed_count == 0

    def test_compare_configs_different(self):
        """Test comparing different configs."""
        config1 = "interface GigabitEthernet0/0/1\n ip address 192.168.1.1 255.255.255.0"
        config2 = "interface GigabitEthernet0/0/1\n ip address 192.168.1.2 255.255.255.0"
        differ = ConfigDiffer()
        result = differ.compare_configs(config1, config2)
        
        assert result.similarity < 1.0
        assert result.added_count > 0 or result.removed_count > 0

    def test_compare_configs_with_names(self):
        """Test comparing configs with custom names."""
        config1 = "sysname R1"
        config2 = "sysname R2"
        differ = ConfigDiffer()
        result = differ.compare_configs(config1, config2, config1_name='R1', config2_name='R2')
        
        assert 'R1' in result.unified_diff
        assert 'R2' in result.unified_diff

    def test_compare_configs_with_section(self):
        """Test comparing specific section of configs."""
        config1 = """
interface GigabitEthernet0/0/1
 ip address 192.168.1.1 255.255.255.0
#
ospf 1
 area 0
"""
        config2 = """
interface GigabitEthernet0/0/1
 ip address 192.168.1.2 255.255.255.0
#
ospf 1
 area 0
"""
        differ = ConfigDiffer()
        result = differ.compare_configs(config1, config2, section='interface')
        
        # Should only show interface differences
        assert result.similarity < 1.0

    def test_compare_configs_section_not_found(self):
        """Test comparing non-existent section."""
        config = "interface GigabitEthernet0/0/1"
        differ = ConfigDiffer()
        result = differ.compare_configs(config, config, section='bgp')
        
        assert "not found" in str(result.lines).lower() or result.similarity == 1.0

    def test_compare_configs_smart_ignore(self):
        """Test smart ignore filters volatile fields."""
        config1 = """
sysname R1
# Time: 12:00:00
interface GigabitEthernet0/0/1
"""
        config2 = """
sysname R2
# Time: 13:00:00
interface GigabitEthernet0/0/1
"""
        differ = ConfigDiffer()
        
        # Without smart ignore - should be different
        result_normal = differ.compare_configs(config1, config2)
        
        # With smart ignore - should filter sysname and timestamp
        result_smart = differ.compare_configs(config1, config2, smart_ignore=True)
        
        # Smart ignore should result in higher similarity
        assert result_smart.similarity >= result_normal.similarity

    def test_extract_section_interface(self):
        """Test extracting interface section."""
        config = """
sysname R1
#
interface GigabitEthernet0/0/1
 ip address 192.168.1.1 255.255.255.0
#
interface GigabitEthernet0/0/2
 ip address 10.0.0.1 255.255.255.0
#
ospf 1
"""
        differ = ConfigDiffer()
        result = differ._extract_section(config, 'interface')
        
        assert 'GigabitEthernet0/0/1' in result
        assert 'GigabitEthernet0/0/2' in result
        # Pattern captures all interfaces and separator lines until next section
        assert 'sysname' not in result

    def test_extract_section_ospf(self):
        """Test extracting OSPF section."""
        config = """
interface GigabitEthernet0/0/1
#
ospf 1
 area 0
  network 192.168.1.0 0.0.0.255
#
"""
        differ = ConfigDiffer()
        result = differ._extract_section(config, 'ospf')
        
        assert 'ospf 1' in result
        assert 'area 0' in result
        assert 'interface' not in result

    def test_extract_section_not_found(self):
        """Test extracting non-existent section."""
        config = "interface GigabitEthernet0/0/1"
        differ = ConfigDiffer()
        result = differ._extract_section(config, 'bgp')
        
        assert "not found" in result.lower()

    def test_filter_config(self):
        """Test filtering volatile fields."""
        config = """
sysname R1
# Jan 01 2024 12:00:00
! Comment
interface GigabitEthernet0/0/1
 ip address 192.168.1.1 255.255.255.0
#
return
"""
        differ = ConfigDiffer()
        result = differ._filter_config(config)
        
        assert 'sysname' not in result
        assert 'Jan 01' not in result
        assert 'Comment' not in result
        assert 'return' not in result
        assert 'interface' in result
        assert '192.168.1.1' in result

    def test_calculate_similarity_identical(self):
        """Test similarity calculation for identical configs."""
        config = "interface test\n ip address 1.1.1.1"
        differ = ConfigDiffer()
        result = differ._calculate_similarity(config, config)
        
        assert result == 1.0

    def test_calculate_similarity_empty(self):
        """Test similarity calculation for empty configs."""
        differ = ConfigDiffer()
        
        # Both empty
        assert differ._calculate_similarity('', '') == 1.0
        
        # One empty
        assert differ._calculate_similarity('config', '') == 0.0
        assert differ._calculate_similarity('', 'config') == 0.0

    def test_calculate_similarity_different(self):
        """Test similarity calculation for different configs."""
        config1 = "interface A\n ip address 1.1.1.1"
        config2 = "interface B\n ip address 2.2.2.2"
        differ = ConfigDiffer()
        result = differ._calculate_similarity(config1, config2)
        
        assert 0.0 < result < 1.0

    def test_generate_unified_diff(self):
        """Test generating unified diff."""
        lines1 = ['line1', 'line2', 'line3']
        lines2 = ['line1', 'line2 modified', 'line3']
        differ = ConfigDiffer()
        result = differ._generate_unified_diff(lines1, lines2, 'file1', 'file2')
        
        assert '--- file1' in result
        assert '+++ file2' in result
        assert '@@' in result

    def test_parse_unified_diff(self):
        """Test parsing unified diff output."""
        unified = """--- file1
+++ file2
@@ -1,3 +1,3 @@
 line1
-line2
+line2 modified
 line3
"""
        differ = ConfigDiffer()
        result = differ._parse_unified_diff(unified)
        
        # Should have info lines, range line, and diff lines
        line_types = [line.line_type for line in result]
        assert 'info' in line_types
        assert 'removed' in line_types
        assert 'added' in line_types
        assert 'unchanged' in line_types

    def test_audit_configs(self):
        """Test auditing multiple configurations."""
        configs = {
            'R1': 'interface GE0/0/1\n ip address 192.168.1.1',
            'R2': 'interface GE0/0/1\n ip address 192.168.1.2',
            'R3': 'interface GE0/0/1\n ip address 192.168.1.1',
        }
        differ = ConfigDiffer()
        result = differ.audit_configs(configs, threshold=0.9)
        
        assert result['device_count'] == 3
        assert len(result['comparisons']) == 3  # C(3,2) = 3 pairs
        
        # R1 vs R3 should be identical
        r1_r3 = next((c for c in result['comparisons'] 
                      if set([c['device1'], c['device2']]) == {'R1', 'R3'}), None)
        assert r1_r3 is not None
        assert r1_r3['similarity'] == 1.0

    def test_audit_configs_with_warnings(self):
        """Test audit with similarity warnings."""
        configs = {
            'R1': 'interface GE0/0/1\n ip address 192.168.1.1',
            'R2': 'completely different config here',
        }
        differ = ConfigDiffer()
        result = differ.audit_configs(configs, threshold=0.9)
        
        assert len(result['warnings']) > 0
        assert 'Significant difference' in result['warnings'][0]['message']


class TestCompareConfigsFunction:
    """Tests for compare_configs convenience function."""

    def test_compare_configs_function(self):
        """Test the convenience function."""
        config1 = "interface A"
        config2 = "interface B"
        result = compare_configs(config1, config2)
        
        assert isinstance(result, ConfigDiff)
        assert result.similarity < 1.0

    def test_compare_configs_function_with_options(self):
        """Test the convenience function with options."""
        config1 = "sysname R1\ninterface A"
        config2 = "sysname R2\ninterface A"
        result = compare_configs(config1, config2, smart_ignore=True)
        
        assert result.similarity == 1.0  # sysname should be ignored


class TestDiffFromFilesFunction:
    """Tests for diff_from_files function."""

    def test_diff_from_files(self, tmp_path: Path):
        """Test comparing config files."""
        file1 = tmp_path / 'config1.cfg'
        file2 = tmp_path / 'config2.cfg'
        
        file1.write_text('interface GE0/0/1\n ip address 192.168.1.1')
        file2.write_text('interface GE0/0/1\n ip address 192.168.1.2')
        
        result = diff_from_files(file1, file2)
        
        assert isinstance(result, ConfigDiff)
        assert result.similarity < 1.0
        assert str(file1) in result.unified_diff
        assert str(file2) in result.unified_diff

    def test_diff_from_files_smart_ignore(self, tmp_path: Path):
        """Test comparing config files with smart ignore."""
        file1 = tmp_path / 'config1.cfg'
        file2 = tmp_path / 'config2.cfg'
        
        file1.write_text('sysname R1\ninterface GE0/0/1')
        file2.write_text('sysname R2\ninterface GE0/0/1')
        
        result = diff_from_files(file1, file2, smart_ignore=True)
        
        assert result.similarity == 1.0  # sysname should be ignored

    def test_diff_from_files_with_section(self, tmp_path: Path):
        """Test comparing config files with section filter."""
        file1 = tmp_path / 'config1.cfg'
        file2 = tmp_path / 'config2.cfg'
        
        file1.write_text('interface GE0/0/1\n ip address 192.168.1.1\n#\nospf 1')
        file2.write_text('interface GE0/0/1\n ip address 192.168.1.2\n#\nospf 2')
        
        result = diff_from_files(file1, file2, section='interface')
        
        assert isinstance(result, ConfigDiff)


class TestSectionPatterns:
    """Tests for section extraction patterns."""

    @pytest.mark.parametrize("section", [
        'interface',
        'ospf',
        'bgp',
        'acl',
        'vlan',
        'routing',
        'snmp',
        'ntp',
    ])
    def test_section_patterns_exist(self, section):
        """Test that all expected section patterns exist."""
        differ = ConfigDiffer()
        assert section in differ.SECTION_PATTERNS

    def test_interface_pattern_matching(self):
        """Test interface section pattern matching."""
        config = """
interface GigabitEthernet0/0/1
 ip address 192.168.1.1 255.255.255.0
interface GigabitEthernet0/0/2
 ip address 10.0.0.1 255.255.255.0
"""
        differ = ConfigDiffer()
        result = differ._extract_section(config, 'interface')
        
        assert 'GigabitEthernet0/0/1' in result
        assert 'GigabitEthernet0/0/2' in result

    def test_ospf_pattern_matching(self):
        """Test OSPF section pattern matching."""
        config = """
ospf 1 router-id 1.1.1.1
 area 0.0.0.0
  network 192.168.1.0 0.0.0.255
"""
        differ = ConfigDiffer()
        result = differ._extract_section(config, 'ospf')
        
        assert 'ospf 1' in result
        assert 'area 0.0.0.0' in result


class TestIgnorePatterns:
    """Tests for ignore patterns."""

    @pytest.mark.parametrize("line", [
        '# This is a comment',
        '! Another comment',
        'sysname Router1',
        'Current Time: Mon Jan 01 12:00:00 2024',
        'Uptime is 10 days',
        'Statistics: packets=100',
        'return',
    ])
    def test_default_ignore_patterns_match(self, line):
        """Test that default ignore patterns match expected lines."""
        differ = ConfigDiffer()
        filtered = differ._filter_config(line)
        
        assert filtered == ''

    def test_important_lines_not_ignored(self):
        """Test that important config lines are not ignored."""
        config = """
interface GigabitEthernet0/0/1
 ip address 192.168.1.1 255.255.255.0
 ospf enable 1 area 0
#
ip route-static 0.0.0.0 0 192.168.1.254
"""
        differ = ConfigDiffer()
        result = differ._filter_config(config)
        
        assert 'interface' in result
        assert 'ip address' in result
        assert 'ospf' in result
        assert 'ip route-static' in result
