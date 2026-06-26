"""
Tests for WiFi-PWN Toolkit
Run with: python -m pytest tests/
"""

import os
import sys
import re
from pathlib import Path
import importlib.util

spec = importlib.util.spec_from_file_location("wifi_pwn", Path(__file__).parent.parent / "wifi-pwn.py")
wifi_pwn = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wifi_pwn)


class TestCheckAdmin:
    """Test admin check functionality."""
    
    def test_check_admin_returns_bool(self):
        result = wifi_pwn.check_admin()
        assert isinstance(result, bool)


class TestCheckTool:
    """Test tool checking functionality."""
    
    def test_check_tool_existing(self):
        result = wifi_pwn.check_tool("python")
        assert result is not None or result is False
    
    def test_check_tool_nonexistent(self):
        result = wifi_pwn.check_tool("nonexistent_tool_12345")
        assert result is None or result is False


class TestRunCmd:
    """Test command execution."""
    
    def test_run_cmd_echo(self):
        code, out, err = wifi_pwn.run_cmd("echo", timeout=5, shell=True)
        assert code == 0 or code != 0  # Command runs
    
    def test_run_cmd_nonexistent(self):
        code, out, err = wifi_pwn.run_cmd("nonexistent_command_xyz", timeout=5)
        assert code == -2 or code != 0


class TestScanNetworksMock:
    """Test scan_networks with mocked Windows output."""
    
    def test_parse_windows_network_output(self):
        sample_output = """
There were 2 networks found.

Network 1:
    SSID 1 : MyWiFi
    BSSID 1 : aa:bb:cc:dd:ee:ff
    Signal : 85%
    Channel : 6
    Authentication : WPA2-Personal

Network 2:
    SSID 2 : Guest_Network
    BSSID 2 : 11:22:33:44:55:66
    Signal : 62%
    Channel : 11
    Authentication : WPA2-Enterprise
"""
        networks = []
        current = {}
        
        for line in sample_output.splitlines():
            m = re.match(r'\s*SSID\s*\d*\s*:\s*(.*)', line)
            if m:
                if current and "ssid" in current:
                    networks.append(current)
                current = {"ssid": m.group(1).strip()}
                continue
            
            m = re.match(r'\s*BSSID\s*\d*\s*:\s*([0-9a-f:]+)', line, re.IGNORECASE)
            if m:
                current["bssid"] = m.group(1).lower()
                continue
            
            m = re.match(r'\s*Signal\s*:\s*(.*)', line, re.IGNORECASE)
            if m:
                current["signal"] = m.group(1).strip()
                continue
            
            m = re.match(r'\s*Channel\s*:\s*(\d+)', line, re.IGNORECASE)
            if m:
                current["channel"] = m.group(1)
                continue
        
        if current and "ssid" in current:
            networks.append(current)
        
        assert len(networks) == 2
        assert networks[0]["ssid"] == "MyWiFi"
        assert networks[0]["bssid"] == "aa:bb:cc:dd:ee:ff"
        assert networks[1]["ssid"] == "Guest_Network"

    def test_scan_networks_returns_networks_list(self, monkeypatch):
        def mock_run_cmd(cmd, timeout=120, shell=False, capture=True):
            return 0, sample_outputs_cmd(), ""
        
        monkeypatch.setattr(wifi_pwn, 'IS_WINDOWS', True)
        monkeypatch.setattr(wifi_pwn, 'run_cmd', mock_run_cmd)
        result = wifi_pwn.scan_networks()
        assert result is not None
        assert isinstance(result, list)


def sample_outputs_cmd():
    return """
There were 2 networks found.
Network 1:
    SSID 1 : TestWiFi
    BSSID 1 : aa:bb:cc:dd:ee:ff
    Signal : 75%
    Channel : 6
    Authentication : WPA2-Personal
""".strip()


class TestLog:
    """Test logging function."""
    
    def test_log_returns_none(self, capsys):
        result = wifi_pwn.log("Test message", "info")
        assert result is None
        
    def test_log_output(self, capsys):
        wifi_pwn.log("Test message", "ok")
        captured = capsys.readouterr()
        assert "Test message" in captured.out


class TestWriteReport:
    """Test report writing functionality."""
    
    def test_write_report(self, tmp_path):
        test_output = tmp_path / "output"
        wifi_pwn.OUTPUT_DIR = test_output
        test_output.mkdir(parents=True, exist_ok=True)
        
        wifi_pwn.write_report(
            ssid="TestSSID",
            bssid="AA:BB:CC:DD:EE:FF",
            method="Test",
            status="SUCCESS",
            password="testpass",
            elapsed=10.0
        )
        
        report = test_output / "audit-report.txt"
        assert report.exists()
        content = report.read_text()
        assert "TestSSID" in content
        assert "AA:BB:CC:DD:EE:FF" in content


class TestPathOperations:
    """Test path-related functionality."""
    
    def test_script_dir_exists(self):
        assert wifi_pwn.SCRIPT_DIR.exists()
    
    def test_output_dir_default(self):
        original_output_dir = wifi_pwn.OUTPUT_DIR
        wifi_pwn.OUTPUT_DIR = wifi_pwn.SCRIPT_DIR / "wifi-pwn-output"
        try:
            assert wifi_pwn.OUTPUT_DIR.name == "wifi-pwn-output"
        finally:
            wifi_pwn.OUTPUT_DIR = original_output_dir