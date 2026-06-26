# WiFi-PWN Toolkit v2.0

> WiFi Adapter Payload-Based Password Recovery Toolkit (Internal & External)

![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20Windows-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)

A comprehensive WiFi security assessment toolkit designed to extract saved WiFi passwords, capture PMKID hashes, perform WPA handshake captures, and crack passwords using hashcat — works with both internal (built-in) and external WiFi adapters.

---

## Features

| Feature | Description |
|---|---|
| Saved Password Extraction | Extract all saved WiFi passwords from Windows/Linux |
| PMKID Capture | Capture PMKID hashes from nearby access points |
| WPA Handshake Capture | Capture WPA 4-way handshakes via monitor mode |
| Deauth Attacks | Send deauthentication packets to force reconnections |
| Password Cracking | Crack captured hashes with hashcat + wordlists/masks |
| Auto Scan | Scan nearby WiFi networks |
| Capability Detection | Check what your internal WiFi adapter supports |
| Full Auto Mode | One-command end-to-end: recon → capture → crack |

---

## Requirements

### Linux (Recommended)
- Python 3.8+
- Root/sudo privileges
- Wireless adapter with monitor mode support

**Install dependencies:**
```bash
sudo apt update
sudo apt install -y aircrack-ng hcxdumptool hcxtools hashcat python3
```

### Windows
- Python 3.8+
- Administrator privileges
- Optional: [CommView for WiFi](https://www.tamos.com/products/commwifi/) for handshake capture

---

## Installation

```bash
# Clone the repository
git clone https://github.com/<jojin1709 >/wifi-pwn.git
cd wifi-pwn

# Verify installation
python3 wifi-pwn.py detect
```

---

## Usage

```bash
# Basic usage
python3 wifi-pwn.py <command> [options]

# Always run as root on Linux
sudo python3 wifi-pwn.py <command>
```

> **Note:** On Linux, if required tools are missing, the script will ask if you want to install them automatically via `apt`.

---

## Bundled Wordlist

The toolkit includes a built-in wordlist at `wordlists/common-wifi-passwords.txt` with the most common WiFi passwords. No download needed — it works out of the box. For larger wordlists, use `--wordlist /usr/share/wordlists/rockyou.txt`.

### Commands

#### 1. Recon — Extract Saved WiFi Passwords
Extracts all previously connected WiFi passwords from the local machine.

```bash
python3 wifi-pwn.py recon
```

**Windows:** Reads from `netsh wlan show profiles`
**Linux:** Reads from `/etc/NetworkManager/system-connections/` and `/etc/wpa_supplicant/`

---

#### 2. Scan — Scan Nearby Networks
Scans and lists nearby WiFi networks with SSID, BSSID, and channel info.

```bash
python3 wifi-pwn.py scan
python3 wifi-pwn.py scan --interface wlan0
```

---

#### 3. PMKID Capture
Captures PMKID hashes from a target access point. Works on most internal WiFi adapters.

```bash
python3 wifi-pwn.py pmkid
python3 wifi-pwn.py pmkid --bssid AA:BB:CC:DD:EE:FF --timeout 120
```

**Output:** `.pcapng` capture file → `.22000` hash file for hashcat

---

#### 4. Handshake Capture
Captures WPA 4-way handshake via monitor mode. Requires monitor mode support.

```bash
python3 wifi-pwn.py capture --bssid AA:BB:CC:DD:EE:FF --channel 6
python3 wifi-pwn.py capture --bssid AA:BB:CC:DD:EE:FF --channel 6 --timeout 180
```

**Tip:** If monitor mode fails, use PMKID capture instead — it works on more adapters.

---

#### 5. Deauth Attack
Sends deauthentication packets to disconnect a client or AP, forcing a reconnection for handshake capture.

```bash
python3 wifi-pwn.py deauth --bssid AA:BB:CC:DD:EE:FF --iface wlan0mon
python3 wifi-pwn.py deauth --bssid AA:BB:CC:DD:EE:FF --client 11:22:33:44:55:66 --iface wlan0mon --count 10
```

---

#### 6. Crack — Password Cracking
Crack captured hashes using hashcat with wordlists or mask attacks.

```bash
# Dictionary attack
python3 wifi-pwn.py crack --input hash.22000 --wordlist rockyou.txt

# Mask attack (e.g. 8-digit PIN)
python3 wifi-pwn.py crack --input hash.22000 --mask "?d?d?d?d?d?d?d?d"

# With rules
python3 wifi-pwn.py crack --input hash.22000 --wordlist rockyou.txt --rules /path/to/best64.rule

# Auto-convert .cap files
python3 wifi-pwn.py crack --input capture.cap --wordlist rockyou.txt
```

---

#### 7. Full Auto Mode
End-to-end automated workflow: recon → PMKID capture → crack.

```bash
python3 wifi-pwn.py full --bssid AA:BB:CC:DD:EE:FF --wordlist rockyou.txt
```

Without BSSID, it will scan first, then prompt for target selection.

---

#### 8. Detect Capabilities
Check what your WiFi adapter supports before running attacks.

```bash
python3 wifi-pwn.py detect
```

---

## All Options

| Option | Description | Default |
|---|---|---|
| `--bssid` | Target BSSID (MAC address) | — |
| `--channel` | Target channel number | — |
| `--timeout` | Capture timeout (seconds) | 60 |
| `--interface` | Wireless interface name | auto-detect |
| `--input` | Input hash/capture file for cracking | — |
| `--wordlist` | Path to wordlist file | auto-detect |
| `--mask` | Hashcat mask (e.g. `?d?d?d?d?d?d?d?d`) | — |
| `--rules` | Hashcat rules file path | — |
| `--client` | Client MAC for targeted deauth | — |
| `--count` | Number of deauth packets | 5 |
| `--output` | Custom output directory | `./wifi-pwn-output` |
| `--no-admin` | Skip admin/root check | false |

---

## Workflow Examples

### Example 1: Quick WiFi Password Extraction
```bash
# Extract all saved passwords from this machine
sudo python3 wifi-pwn.py recon
```

### Example 2: Capture and Crack a Target Network
```bash
# Step 1: Scan for networks
sudo python3 wifi-pwn.py scan

# Step 2: Capture PMKID (works on most internal cards)
sudo python3 wifi-pwn.py pmkid --bssid AA:BB:CC:DD:EE:FF --timeout 120

# Step 3: Crack the hash (uses bundled wordlist by default)
sudo python3 wifi-pwn.py crack --input wifi-pwn-output/pmkid-*.22000
```

### Example 3: Full Automated Attack
```bash
# One command to do everything (uses bundled wordlist)
sudo python3 wifi-pwn.py full --bssid AA:BB:CC:DD:EE:FF --timeout 120
```

### Example 4: Check Adapter Capabilities
```bash
# See what your card can do before attempting attacks
sudo python3 wifi-pwn.py detect
```

---

## Supported Tools

| Tool | Purpose | Install |
|---|---|---|
| `hcxdumptool` | PMKID/pcap capture | `sudo apt install hcxdumptool` |
| `hcxpcapngtool` | Convert captures to hashcat format | `sudo apt install hcxtools` |
| `hashcat` | Password cracking | `sudo apt install hashcat` |
| `aircrack-ng` suite | Monitor mode, deauth, handshake capture | `sudo apt install aircrack-ng` |
| `airodump-ng` | Handshake capture | `sudo apt install aircrack-ng` |
| `aireplay-ng` | Deauth attacks | `sudo apt install aircrack-ng` |
| `iw` | Interface management | `sudo apt install iw` |

---

## Output Structure

```
wifi-pwn-output/
├── audit-report.txt          # Full audit report
├── cracked-passwords.txt     # Cracked passwords
├── saved-passwords.txt       # Extracted saved passwords (recon)
├── pmkid-capture-HHMMSS.pcapng
├── pmkid-capture-HHMMSS.22000
├── pmkid-capture-HHMMSS.essid
├── handshake-HHMMSS.cap
└── handshake-HHMMSS.22000

wordlists/
└── common-wifi-passwords.txt # Bundled wordlist (ready to use)
```

---

## Legal Disclaimer

> **FOR AUTHORIZED SECURITY ASSESSMENTS ONLY**

This tool is intended for educational purposes and authorized security testing only. You must have explicit written permission from the network owner before testing or auditing any network. Unauthorized access to computer networks is illegal and may result in criminal penalties.

The author is not responsible for any misuse or damage caused by this software. Use it responsibly and ethically.

---

## Troubleshooting

| Issue | Solution |
|---|---|
| "No wireless interfaces found" | Check `iw dev` — your adapter may need drivers |
| "Monitor mode failed" | Try PMKID capture instead (`pmkid` command) |
| "Tools not found" | The script will auto-prompt to install missing tools on Linux |
| "No wordlist found" | Bundled wordlist included at `wordlists/common-wifi-passwords.txt` |
| "PMKID not captured" | Try longer timeout, check if AP supports PMKID, move closer to AP |
| "Permission denied" | Run with `sudo` on Linux or as Administrator on Windows |

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit your changes: `git commit -m 'Add feature'`
4. Push to the branch: `git push origin feature-name`
5. Open a Pull Request

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Star History

If this tool helped you, consider giving it a ⭐ on GitHub!

---

**Built for security professionals and penetration testers. Use responsibly.**
