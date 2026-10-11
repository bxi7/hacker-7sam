import os, sys, csv, io, time, string, struct, hashlib, subprocess, json
from datetime import datetime, timedelta

HOURS = 24
NOW = datetime.now()
SINCE = NOW - timedelta(hours=HOURS)
QUICK = "--quick" in sys.argv
HERE = os.path.dirname(os.path.abspath(__file__))
HASH_FILE = os.path.join(HERE, "known_hashes.txt")
PE_SIEVE = os.path.join(HERE, "pe-sieve64.exe")
PE_SIEVE_API = "https://api.github.com/repos/hasherezade/pe-sieve/releases/latest"

TARGET_PROCESSES = ["fivem_gtaprocess.exe", "gta5.exe", "fivem.exe"]
PURPLE = "\033[95m"
MAGENTA_BOLD = "\033[1;35m"
CYAN = "\033[96m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def enable_vt_colors():
    if os.name == "nt":
        os.system("")
        try:
            import ctypes
            k = ctypes.windll.kernel32
            h = k.GetStdHandle(-11)
            mode = ctypes.c_uint32()
            k.GetConsoleMode(h, ctypes.byref(mode))
            k.SetConsoleMode(h, mode.value | 0x0004)
        except Exception:
            pass


def banner():
    os.system("title hacker.7sam")
    print(PURPLE + r"""
 _               _                  _____
| |__   __ _  ___| | _____ _ __     |___  / ___  __ _ _ __ ___
| '_ \ / _` |/ __| |/ / _ \ '__|_____  / / / __|/ _` | '_ ` _ \
| | | | (_| | (__|   <  __/ | |_____|/ /_ \__ \ (_| | | | | | |
|_| |_|\__,_|\___|_|\_\___|_|       /____||___/\__,_|_| |_| |_|
""" + RESET)
    print(MAGENTA_BOLD + "            hacker.7sam  -  FiveM PC Check Scanner" + RESET)
    print(PURPLE + "-" * 68 + RESET)
NAME_KEYWORDS = [
    "eulen", "redengine", "red engine", "hammafia", "skript", "lumia", "susano",
    "tzx", "kiddion", "cherax", "x-force", "xforce", "executor", "injector",
    "aimbot", "triggerbot", "wallhack", "spoofer", "hwid", "unban", "cheat",
    "hack", "menyoo", "reaper", "falcon", "phaze", "brutan", "desudo",
]
META_KEYWORDS = NAME_KEYWORDS + ["inject", "loader", "lua executor", "menu"]
STRING_MARKERS = [
    "lua executor", "aimbot", "triggerbot", "silent aim", "godmode", "noclip",
    "teleport to waypoint", "give all weapons", "spawn vehicle", "esp distance",
    "inject dll", "manualmap", "bypass anticheat", "anti-cheat bypass",
    "resource stopper", "event logger", "trigger event", "menu key",
]
MIN_STRING_HITS = 2
CHECK_EXT = {".exe", ".dll", ".asi", ".sys", ".lua"}
MAX_READ = 64 * 1024 * 1024

SKIP_DIRS = ["\\windows\\", "\\$recycle.bin", "\\system volume information",
             "\\node_modules", "\\.git\\", "\\programdata\\microsoft\\",
             "\\windowsapps\\", "\\program files\\windowsapps"]
NOISE = ["research", "address", "response", "desktop.ini"]
USER_WRITABLE = ["\\downloads\\", "\\desktop\\", "\\appdata\\", "\\temp\\", "\\documents\\", "\\public\\"]

R = {k: [] for k in ["names", "hashes", "meta", "strings", "unsigned", "fivem",
                     "recycle", "usn", "prefetch", "processes", "memory", "info"]}


def is_admin():
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def drives():
    import ctypes
    out = []
    for l in string.ascii_uppercase:
        p = f"{l}:\\"
        if os.path.exists(p) and ctypes.windll.kernel32.GetDriveTypeW(p) == 3:
            out.append(p)
    return out


def kw(name, words=NAME_KEYWORDS):
    n = name.lower()
    for k in words:
        if k in n and not any(x in n and k in x for x in NOISE):
            return k
    return None


def load_hashes():
    h = {}
    if os.path.exists(HASH_FILE):
        for line in open(HASH_FILE, encoding="utf-8", errors="ignore"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(None, 1)
            if len(parts[0]) == 64:
                h[parts[0].lower()] = parts[1] if len(parts) > 1 else "known cheat"
    return h


def pe_info(path):
    import ctypes
    from ctypes import wintypes
    ver = ctypes.windll.version
    size = ver.GetFileVersionInfoSizeW(path, None)
    if not size:
        return {}
    buf = ctypes.create_string_buffer(size)
    if not ver.GetFileVersionInfoW(path, 0, size, buf):
        return {}
    lp, ln = ctypes.c_void_p(), wintypes.UINT()
    if not ver.VerQueryValueW(buf, "\\VarFileInfo\\Translation", ctypes.byref(lp), ctypes.byref(ln)) or ln.value < 4:
        return {}
    lang, cp = struct.unpack("<HH", ctypes.string_at(lp.value, 4))
    res = {}
    for key in ("OriginalFilename", "InternalName", "ProductName", "CompanyName", "FileDescription"):
        sub = f"\\StringFileInfo\\{lang:04x}{cp:04x}\\{key}"
        if ver.VerQueryValueW(buf, sub, ctypes.byref(lp), ctypes.byref(ln)) and ln.value:
            res[key] = ctypes.wstring_at(lp.value)
    return res


def inspect_file(path, known):
    try:
        size = os.path.getsize(path)
        if size == 0 or size > 500 * 1024 * 1024:
            return
        sha = hashlib.sha256()
        data = None
        if size <= MAX_READ:
            data = open(path, "rb").read()
            sha.update(data)
        else:
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
                    sha.update(chunk)
        d = sha.hexdigest()
        if d in known:
            R["hashes"].append(f"HASH MATCH ({known[d]}): {path}  [{d}]")
        if path.lower().endswith((".exe", ".dll", ".asi", ".sys")):
            info = pe_info(path)
            blob = " | ".join(f"{k}={v}" for k, v in info.items())
            hit = kw(blob, META_KEYWORDS)
            if hit:
                R["meta"].append(f"[{hit}] {path}\n      {blob}")
            orig = info.get("OriginalFilename", "")
            if orig and orig.lower() != os.path.basename(path).lower() \
               and any(w in path.lower() for w in USER_WRITABLE):
                R["info"].append(f"Renamed? file '{os.path.basename(path)}' but OriginalFilename='{orig}': {path}")
        if data:
            low = data.lower()
            found = [s for s in STRING_MARKERS if s.encode() in low or s.encode("utf-16le") in low]
            if len(found) >= MIN_STRING_HITS:
                R["strings"].append(f"{path}\n      markers: {', '.join(found)}")
    except Exception:
        pass


def candidate_roots():
    if QUICK:
        up = os.environ.get("USERPROFILE", "")
        roots = [up, os.environ.get("PROGRAMDATA", ""), os.environ.get("PUBLIC", "")]
        return [r for r in roots if r and os.path.isdir(r)]
    return drives()


def full_scan(known):
    recent_user_files = []
    count = 0
    for base in candidate_roots():
        print(CYAN + f"[*] Scanning {base} ..." + RESET)
        for root, dirs, files in os.walk(base, topdown=True):
            low = (root + "\\").lower()
            if any(s in low for s in SKIP_DIRS):
                dirs[:] = []
                continue
            for name in files + dirs:
                k = kw(name)
                if k:
                    full = os.path.join(root, name)
                    try:
                        m = datetime.fromtimestamp(os.path.getmtime(full)).strftime("%Y-%m-%d %H:%M")
                    except Exception:
                        m = "?"
                    R["names"].append(f"[{k}] {full}  (modified {m})")
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in CHECK_EXT:
                    full = os.path.join(root, f)
                    inspect_file(full, known)
                    count += 1
                    if count % 500 == 0:
                        print(CYAN + f"    inspected {count} binaries..." + RESET)
                    if ext in (".exe", ".dll", ".asi") and any(w in low for w in USER_WRITABLE):
                        try:
                            if datetime.fromtimestamp(os.path.getmtime(full)) >= NOW - timedelta(days=7):
                                recent_user_files.append(full)
                        except Exception:
                            pass
    check_signatures(recent_user_files[:300])


def check_signatures(files):
    if not files:
        return
    print(CYAN + f"[*] Checking digital signatures of {len(files)} recent files ..." + RESET)
    lst = os.path.join(os.environ.get("TEMP", "."), "_sig_list.txt")
    with open(lst, "w", encoding="utf-8") as f:
        f.write("\n".join(files))
    ps = ("Get-Content -LiteralPath '%s' -Encoding UTF8 | ForEach-Object { "
          "$s = Get-AuthenticodeSignature -LiteralPath $_; "
          "if ($s.Status -ne 'Valid') { \"$($s.Status)|$_\" } }" % lst)
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                             capture_output=True, text=True, errors="ignore", timeout=600).stdout
        for line in out.splitlines():
            if "|" in line:
                st, p = line.split("|", 1)
                R["unsigned"].append(f"{st}: {p}")
    except Exception as e:
        R["unsigned"].append(f"signature check failed: {e}")
    try:
        os.remove(lst)
    except Exception:
        pass


def scan_fivem(known):
    la, ad = os.environ.get("LOCALAPPDATA", ""), os.environ.get("APPDATA", "")
    base = os.path.join(la, "FiveM", "FiveM.app")
    if not os.path.isdir(base):
        R["fivem"].append("FiveM folder not found in default location.")
        return
    for t in [base, os.path.join(ad, "CitizenFX")]:
        for root, _, files in os.walk(t):
            for f in files:
                full = os.path.join(root, f)
                ext = os.path.splitext(f)[1].lower()
                if ext == ".asi":
                    R["fivem"].append(f"ASI plugin: {full}")
                    inspect_file(full, known)
                elif ext in (".dll", ".lua", ".exe") and "plugins" in root.lower():
                    R["fivem"].append(f"Plugin file: {full}")
                    inspect_file(full, known)
    for f in os.listdir(base):
        if f.lower() in ("dinput8.dll", "d3d9.dll", "version.dll", "winmm.dll"):
            R["fivem"].append(f"Proxy DLL in FiveM.app (review): {os.path.join(base, f)}")
            inspect_file(os.path.join(base, f), known)


def ft_to_dt(ft):
    return datetime(1601, 1, 1) + timedelta(microseconds=ft // 10)


def scan_recycle():
    for d in drives():
        rb = os.path.join(d, "$Recycle.Bin")
        try:
            sids = os.listdir(rb)
        except Exception:
            continue
        for sid in sids:
            p = os.path.join(rb, sid)
            try:
                items = os.listdir(p)
            except Exception:
                continue
            for it in items:
                if not it.startswith("$I"):
                    continue
                try:
                    data = open(os.path.join(p, it), "rb").read()
                    ver = int.from_bytes(data[0:8], "little")
                    ts = ft_to_dt(int.from_bytes(data[16:24], "little")) + (datetime.now() - datetime.utcnow())
                    path = data[28:].decode("utf-16le", "ignore") if ver == 2 else data[24:].decode("utf-16le", "ignore")
                    path = path.rstrip("\x00")
                    if ts >= SINCE:
                        flag = " <-- SUSPICIOUS" if kw(path) else ""
                        R["recycle"].append(f"{ts:%Y-%m-%d %H:%M}  {path}{flag}")
                except Exception:
                    continue


def scan_usn():
    if not is_admin():
        R["usn"].append("Skipped: insufficient privileges for USN journal access.")
        return
    for d in drives():
        vol = d[:2]
        try:
            out = subprocess.run(["fsutil", "usn", "readjournal", vol, "csv"],
                                 capture_output=True, text=True, errors="ignore", timeout=900).stdout
        except Exception as e:
            R["usn"].append(f"{vol} error: {e}")
            continue
        rows = list(csv.reader(io.StringIO(out)))
        if not rows:
            continue
        hdr = [h.lower() for h in rows[0]]
        try:
            i_name = next(i for i, h in enumerate(hdr) if "file name" in h or h == "name")
            i_reason = next(i for i, h in enumerate(hdr) if "reason" in h)
            i_time = next(i for i, h in enumerate(hdr) if "time" in h)
        except StopIteration:
            R["usn"].append(f"{vol}: could not parse journal columns.")
            continue
        for r in rows[1:]:
            try:
                if "delete" not in r[i_reason].lower():
                    continue
                ts = None
                for fmt in ("%m/%d/%Y %I:%M:%S %p", "%d/%m/%Y %I:%M:%S %p", "%Y-%m-%d %H:%M:%S",
                            "%m/%d/%Y %H:%M:%S", "%d/%m/%Y %H:%M:%S"):
                    try:
                        ts = datetime.strptime(r[i_time].strip()[:22].strip(), fmt)
                        break
                    except ValueError:
                        pass
                if ts and ts < SINCE:
                    continue
                name = r[i_name]
                flag = " <-- SUSPICIOUS" if kw(name) else ""
                if flag or name.lower().endswith((".exe", ".dll", ".asi", ".lua", ".sys")):
                    R["usn"].append(f"{r[i_time]}  {vol}  {name}{flag}")
            except Exception:
                continue


def scan_prefetch():
    pf = r"C:\Windows\Prefetch"
    try:
        for f in os.listdir(pf):
            if f.lower().endswith(".pf"):
                m = datetime.fromtimestamp(os.path.getmtime(os.path.join(pf, f)))
                if m >= SINCE:
                    flag = " <-- SUSPICIOUS" if kw(f) else ""
                    R["prefetch"].append(f"{m:%Y-%m-%d %H:%M}  {f}{flag}")
    except Exception:
        R["prefetch"].append("Prefetch access unavailable.")


def scan_processes():
    try:
        out = subprocess.run(["tasklist", "/fo", "csv", "/nh"], capture_output=True, text=True, errors="ignore").stdout
        for line in out.splitlines():
            name = line.split('","')[0].strip('"')
            k = kw(name)
            if k:
                R["processes"].append(f"[{k}] {name}")
    except Exception:
        pass
def ensure_pe_sieve():
    if os.path.exists(PE_SIEVE):
        return True
    print(YELLOW + "[*] pe-sieve64.exe not found, downloading from GitHub (hasherezade/pe-sieve) ..." + RESET)
    try:
        import urllib.request
        req = urllib.request.Request(PE_SIEVE_API, headers={"User-Agent": "hacker.7sam-scanner"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            rel = json.loads(resp.read().decode())
        asset_url = None
        for a in rel.get("assets", []):
            n = a.get("name", "").lower()
            if n.endswith(".zip") and "64" in n and "pe-sieve" in n:
                asset_url = a["browser_download_url"]
                break
        if not asset_url:
            for a in rel.get("assets", []):
                if a.get("name", "").lower().endswith(".zip"):
                    asset_url = a["browser_download_url"]
                    break
        if not asset_url:
            print(RED + "[!] Could not find a PE-sieve zip asset in the latest release." + RESET)
            return False
        zpath = os.path.join(HERE, "_pesieve.zip")
        urllib.request.urlretrieve(asset_url, zpath)
        import zipfile
        with zipfile.ZipFile(zpath) as z:
            for name in z.namelist():
                if name.lower().endswith("pe-sieve64.exe"):
                    with z.open(name) as src, open(PE_SIEVE, "wb") as dst:
                        dst.write(src.read())
                    break
        os.remove(zpath)
        if os.path.exists(PE_SIEVE):
            print(GREEN + "[+] pe-sieve64.exe downloaded successfully." + RESET)
            return True
    except Exception as e:
        print(RED + f"[!] Auto-download failed: {e}" + RESET)
    return False


def find_target_pids():
    pids = []
    try:
        out = subprocess.run(["tasklist", "/fo", "csv", "/nh"], capture_output=True,
                             text=True, errors="ignore").stdout
        for line in out.splitlines():
            parts = [p.strip('"') for p in line.split('","')]
            if len(parts) < 2:
                continue
            name, pid = parts[0], parts[1]
            if name.lower() in TARGET_PROCESSES:
                pids.append((pid, name))
    except Exception:
        pass
    return pids


def scan_memory():
    if not is_admin():
        R["memory"].append("Skipped: insufficient privileges for memory scanning.")
        return
    if not ensure_pe_sieve():
        R["memory"].append("Skipped: pe-sieve64.exe unavailable (download failed, see console).")
        return
    pids = find_target_pids()
    if not pids:
        R["memory"].append("No running FiveM/GTA5 process found.")
        return
    for pid, name in pids:
        print(CYAN + f"[*] Memory-scanning {name} (PID {pid}) with PE-sieve ..." + RESET)
        out_dir = os.path.join(os.environ.get("TEMP", "."), f"pesieve_{pid}")
        try:
            proc = subprocess.run(
                [PE_SIEVE, "/pid", pid, "/quiet", "/ofilter", "2", "/dir", out_dir],
                capture_output=True, text=True, errors="ignore", timeout=300
            )
            summary = (proc.stdout or "") + (proc.stderr or "")
            suspicious = any(w in summary.lower() for w in
                              ["suspicious", "implanted", "replaced", "hdrs_modified", "patched"])
            total_match = None
            for line in summary.splitlines():
                if "total suspicious" in line.lower() or "suspicious:" in line.lower():
                    total_match = line.strip()
            verdict = "SUSPICIOUS - possible in-memory injection" if (suspicious and proc.returncode != 0) else \
                      ("Clean (no anomalies flagged)" if proc.returncode == 0 else "Review needed")
            R["memory"].append(
                f"{name} (PID {pid}): {verdict}"
                + (f"  [{total_match}]" if total_match else "")
                + (f"\n      dumped artifacts: {out_dir}" if os.path.isdir(out_dir) and os.listdir(out_dir) else "")
            )
        except subprocess.TimeoutExpired:
            R["memory"].append(f"{name} (PID {pid}): PE-sieve timed out.")
        except Exception as e:
            R["memory"].append(f"{name} (PID {pid}): error running PE-sieve: {e}")


def write_report(known):
    desk = os.path.join(os.environ.get("USERPROFILE", "."), "Desktop")
    path = os.path.join(desk if os.path.isdir(desk) else ".", f"hacker.7sam_report_{NOW:%Y%m%d_%H%M}.txt")
    titles = [
        ("hashes", "HASH matches (strongest evidence)"),
        ("meta", "PE metadata matches (catches renamed files)"),
        ("strings", "Binaries containing cheat-related strings"),
        ("names", "Suspicious file/folder names"),
        ("unsigned", "Unsigned/invalid-signature exe/dll (last 7 days, user folders)"),
        ("fivem", "FiveM folders (ASI / plugins / proxy DLLs)"),
        ("memory", "Live memory scan of FiveM/GTA5 (PE-sieve - fileless injection)"),
        ("recycle", f"Deleted in last {HOURS}h (Recycle Bin)"),
        ("usn", f"Deleted in last {HOURS}h (NTFS USN journal)"),
        ("prefetch", f"Programs executed in last {HOURS}h (Prefetch)"),
        ("processes", "Running suspicious processes"),
        ("info", "Info (possible renamed files)"),
    ]
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"hacker.7sam - scan report - {NOW:%Y-%m-%d %H:%M}\n")
        f.write(f"Admin: {is_admin()} | Quick: {QUICK} | Known hashes loaded: {len(known)}\n")
        f.write("NOTE: heuristics only. Verify every item manually.\n\n")
        for k, t in titles:
            f.write(f"=== {t} ({len(R[k])}) ===\n")
            f.write("\n".join(R[k]) if R[k] else "Nothing found")
            f.write("\n\n")
    return path


def print_summary():
    total_flags = sum(len(R[k]) for k in ("hashes", "meta", "strings", "unsigned", "memory") )
    print(PURPLE + "-" * 68 + RESET)
    for k, label in [("hashes", "Hash matches"), ("meta", "PE metadata hits"),
                      ("strings", "String matches"), ("unsigned", "Unsigned recent files"),
                      ("memory", "Memory scan findings"), ("names", "Name matches"),
                      ("recycle", "Recently deleted (Recycle Bin)"), ("usn", "Recently deleted (USN)"),
                      ("prefetch", "Recently run programs"), ("processes", "Suspicious running processes")]:
        color = RED if R[k] and k in ("hashes", "meta", "strings", "unsigned", "memory") else CYAN
        print(color + f"  {label:32s}: {len(R[k])}" + RESET)
    print(PURPLE + "-" * 68 + RESET)
    if total_flags > 0:
        print(RED + "  RESULT: suspicious indicators found - review the report." + RESET)
    else:
        print(GREEN + "  RESULT: no strong indicators found at this detection level." + RESET)
    print(PURPLE + "-" * 68 + RESET)


def main():
    enable_vt_colors()
    banner()
    if not is_admin():
        print(RED + "[!] Limited privileges: USN, Prefetch, and memory scans may be incomplete." + RESET)
    known = load_hashes()
    if not known:
        print(YELLOW + "[!] No known hashes loaded." + RESET)
    t = time.time()
    scan_fivem(known)
    scan_processes()
    scan_memory()
    scan_recycle()
    scan_usn()
    scan_prefetch()
    full_scan(known)
    p = write_report(known)
    print_summary()
    print(GREEN + f"\nDone in {int(time.time() - t)}s. Report saved to: {p}" + RESET)


if __name__ == "__main__":
    if os.name != "nt":
        sys.exit("Windows only.")
    main()
