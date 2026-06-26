# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-06-26

## [2.1.0] - 2026-06-26

### Added
- **WPS Attack** (`wps` command) with reaver / pixie-dust support (`--pixie`)
- **Windows guard clauses** — Linux-only commands now show clear "Not supported on Windows" errors
- **macOS support** — Recon and scan commands now work on macOS (Keychain + airport utility)
- **Bundled rockyou.txt** — 14M+ passwords (133 MB) included via Git LFS
- **Auto-install missing tools** — prompts to install `apt` packages on Linux
- **Auto-download wordlist** — downloads wordlists automatically if missing
- **`--exit` flag for hashcat** — stops cracking immediately when password is found
- **`--json` flag for scan** — outputs scan results as JSON for scripting
- **`--pixie` flag** — enables Pixie-Dust WPS attack mode
- **Config file support** — `wifi-pwn-config.json` for default options
- **WPS auto-monitor mode** — automatically enables monitor mode for WPS attacks
- **Documentation website** — full static docs at `docs/index.html`
- **GitHub Pages** — deployable from `/docs` folder
- **Buy Me a Coffee** — support button and widget in README and docs
- **LinkedIn badge** — developer profile link

### Fixed
- Windows UnicodeEncodeError crash when printing banner/colored output
- Wordlist detection logic — now checks bundled `wordlists/rockyou.txt` first
- Hashcat timeout too short for large wordlists — increased default to 1h
- PMKID capture now works on more adapter types (nl80211 / hcxdumptool)
- **scan_networks() return value bug** — fixed incorrect indentation causing `scan` command to return `None` instead of network list on Windows
- **scan_wps() interface detection** — fixed hardcoded `mon0` interface, now properly auto-detects available interfaces and enables monitor mode

### Changed
- Updated branding: "Internal & External WiFi Adapters"
- Split documentation into README + static website
- Added Windows-specific run instructions
- Added Kali Linux install + run guide
- Added WSL2 setup guide for Windows users

### Security
- Legal disclaimer added to README and docs
- Clear "Authorized use only" warnings
