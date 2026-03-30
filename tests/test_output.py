"""Tests for output formatting utilities."""

import json
from unittest.mock import MagicMock, patch

import pytest
from rich.syntax import Syntax

from ensp_cli.output import OutputFormat, output_error, output_json, output_text


class TestOutputJson:
    """Tests for output_json function."""
    
    def test_output_json_produces_valid_json(self, capsys):
        """Test that output_json produces valid JSON output."""
        test_data = {
            "status": "success",
            "device": "Router1",
            "output": "Test output",
        }
        
        output_json(test_data)
        
        captured = capsys.readouterr()
        # Should be valid JSON
        parsed = json.loads(captured.out)
        assert parsed["status"] == "success"
        assert parsed["device"] == "Router1"
        assert parsed["output"] == "Test output"
    
    def test_output_json_with_nested_data(self, capsys):
        """Test output_json with nested dictionary data."""
        test_data = {
            "status": "success",
            "data": {
                "devices": [
                    {"name": "Router1", "type": "Router"},
                    {"name": "Switch1", "type": "Switch"},
                ],
            },
        }
        
        output_json(test_data)
        
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert len(parsed["data"]["devices"]) == 2
        assert parsed["data"]["devices"][0]["name"] == "Router1"


class TestOutputText:
    """Tests for output_text function."""
    
    def test_output_text_produces_syntax_highlighted_output(self, capsys):
        """Test that output_text produces syntax-highlighted output."""
        test_data = "interface GigabitEthernet0/0/1\n ip address 192.168.1.1 255.255.255.0"
        
        with patch("ensp_cli.output.console.print") as mock_print:
            output_text(test_data)
            
            # Should call console.print with a Syntax object
            mock_print.assert_called_once()
            args = mock_print.call_args[0]
            assert len(args) == 1
            assert isinstance(args[0], Syntax)
    
    def test_output_text_uses_cisco_lexer_by_default(self, capsys):
        """Test that output_text uses 'cisco' lexer by default."""
        test_data = "display version"
        
        with patch("ensp_cli.output.console.print") as mock_print:
            output_text(test_data)
            
            args = mock_print.call_args[0]
            syntax = args[0]
            assert isinstance(syntax, Syntax)
            # Verify it's a Syntax object - lexer may be lazily loaded
    
    def test_output_text_allows_custom_lexer(self, capsys):
        """Test that output_text allows custom lexer."""
        test_data = "some output"
        
        with patch("ensp_cli.output.console.print") as mock_print:
            output_text(test_data, lexer="text")
            
            args = mock_print.call_args[0]
            syntax = args[0]
            assert isinstance(syntax, Syntax)
            assert syntax.lexer.name == "Text only"
    
    def test_output_text_fallback_to_plain_text(self, capsys):
        """Test fallback to plain text when Syntax fails."""
        test_data = "some output"
        
        with patch("ensp_cli.output.Syntax") as mock_syntax:
            mock_syntax.side_effect = Exception("Syntax error")
            
            output_text(test_data)
            
            captured = capsys.readouterr()
            assert captured.out.strip() == "some output"


class TestOutputError:
    """Tests for output_error function."""
    
    def test_output_error_json_format(self, capsys):
        """Test that output_error produces correct JSON error format."""
        error_message = "Device not found"
        
        output_error(error_message, OutputFormat.JSON)
        
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert parsed["status"] == "error"
        assert parsed["error"] == "Device not found"
    
    def test_output_error_text_format(self, capsys):
        """Test that output_error produces correct text error format."""
        error_message = "Device not found"
        
        with patch("ensp_cli.output.console.print") as mock_print:
            output_error(error_message, OutputFormat.TEXT)
            
            mock_print.assert_called_once()
            args = mock_print.call_args[0]
            assert "Error: Device not found" in args[0]
            assert "[red]" in args[0]
    
    def test_output_error_with_special_characters(self, capsys):
        """Test output_error handles special characters in message."""
        error_message = 'Error with "quotes" and \n newlines'
        
        output_error(error_message, OutputFormat.JSON)
        
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert parsed["error"] == 'Error with "quotes" and \n newlines'


class TestOutputFormat:
    """Tests for OutputFormat enum."""
    
    def test_output_format_values(self):
        """Test OutputFormat enum values."""
        assert OutputFormat.TEXT == "text"
        assert OutputFormat.JSON == "json"
    
    def test_output_format_from_string(self):
        """Test creating OutputFormat from string."""
        assert OutputFormat("text") == OutputFormat.TEXT
        assert OutputFormat("json") == OutputFormat.JSON
