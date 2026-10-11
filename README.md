# hacker.7sam — FiveM PC Check Scanner

A Windows utility that scans for potential cheat-related indicators in FiveM and GTA V files, processes, and recent system activity. Findings are heuristic and may include false positives; review each result manually.

## Requirements

- Windows 10 or 11
- Python 3.8 or newer
- Administrator privileges are required for some USN, Prefetch, and memory checks.

## Usage

```powershell
python .\hacker_7sam.py
```

The report is saved to the Desktop. To enable known-hash matching, add SHA-256 entries to `known_hashes.txt` in the same folder as the script. Use one hash per line; an optional description may follow the hash.

When `pe-sieve64.exe` is not present, the scanner downloads it from the latest release in the official [PE-sieve repository](https://github.com/hasherezade/pe-sieve/releases) and uses it for live memory scanning. Review downloaded files before running the scanner with elevated privileges.

## Scope and limitations

The scanner does not delete files or transmit scan results. It combines filename, metadata, hash, string, signature, FiveM plugin, process, Prefetch, Recycle Bin, NTFS USN journal, and memory checks. Detection relies partly on heuristics and does not prove that a system is clean or that a user cheated.
