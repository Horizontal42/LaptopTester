# Hardware detection: WMI, smartctl, matching raw names against configured lists.
import json
import os
import re
import subprocess

import wmi
from PyQt5.QtCore import QThread, pyqtSignal

from config import AppConfig, get_base_path

NO_WINDOW = subprocess.CREATE_NO_WINDOW
CPU_PATTERN = re.compile(r"(i\d-\w+|R\d \w+|N\d+|E2-\w+)")


def _normalize(s: str) -> str:
    return " ".join(re.sub(r"[:(),®™]", " ", s.upper()).split())


def _tokens(s: str) -> set:
    return set(_normalize(s).split())


def find_best_match(value: str, allowed: list) -> str:
    """Match a raw WMI name against a configured list.

    Exact normalized match wins; otherwise the longest list entry whose
    tokens all appear in the raw name.  For entries formatted as "VENDOR
    FAMILY: MODEL" (e.g. "NVIDIA MX: MX450"), also tries matching only the
    model part so that WMI names like "NVIDIA GeForce MX450" still hit.
    """
    if not value:
        return ""
    norm_val = _normalize(value)
    val_tokens = set(norm_val.split())

    for item in allowed:
        if item and _normalize(item) == norm_val:
            return item

    best = ""
    for item in allowed:
        if not item:
            continue
        key_toks = _tokens(item.split(": ", 1)[1]) if ": " in item else _tokens(item)
        if (_tokens(item) <= val_tokens or key_toks <= val_tokens) and len(item) > len(best):
            best = item
    return best


def _parse_size_bytes(label: str) -> float:
    n = float(label.split()[0])
    return n * 1e12 if "TB" in label.upper() else n * 1e9


def match_ssd_volume(capacity_bytes: int, ssd_list: list) -> str:
    """Pick the closest advertised size within 7% (drives report decimal GB)."""
    if not capacity_bytes:
        return ""
    best, best_diff = "", 0.07
    for label in ssd_list:
        size = _parse_size_bytes(label)
        diff = abs(capacity_bytes - size) / size
        if diff < best_diff:
            best, best_diff = label, diff
    return best


class HardwareScanner(QThread):
    finished = pyqtSignal(dict)
    log = pyqtSignal(str)

    def __init__(self, cfg: AppConfig):
        super().__init__()
        self.cfg = cfg

    def run(self):
        data = {}
        try:
            c = wmi.WMI()

            self.log.emit("BIOS...")
            for bios in c.Win32_BIOS():
                data["Serial"] = (bios.SerialNumber or "").strip()
                break

            self.log.emit("System...")
            for sys_info in c.Win32_ComputerSystem():
                data["Brand"] = self.match_brand((sys_info.Manufacturer or "").strip())
                data["Model"] = find_best_match((sys_info.Model or "").strip(), self.cfg.models)
                data["RAM"] = self.match_ram(sys_info.TotalPhysicalMemory)
                break

            self.log.emit("CPU...")
            for cpu in c.Win32_Processor():
                data["CPU"] = self.match_cpu((cpu.Name or "").strip())
                break

            self.log.emit("GPU...")
            data["GPU"] = self.detect_gpu(c)

            self.log.emit("Disk...")
            vol, info = self.detect_disk()
            data["SSD_Vol"] = vol
            data["SSD_Info"] = info

            self.log.emit("Password expiry...")
            data["Win_Pass"] = self.reset_password_expiry()
        except Exception as e:
            print(f"Scan error: {e}")

        self.finished.emit(data)

    def match_brand(self, raw: str) -> str:
        alias = self.cfg.brand_aliases.get(raw)
        if alias:
            return alias
        return find_best_match(raw, self.cfg.brands)

    def match_ram(self, total_bytes) -> str:
        try:
            gb = round(int(total_bytes or 0) / 1024**3)
        except (TypeError, ValueError):
            return ""
        # WMI rarely reports DDR generation; the list is ordered so DDR4 wins,
        # the tester corrects it manually when needed.
        target = f"{gb} GB"
        for r in self.cfg.ram:
            if target in r:
                return r
        return ""

    def match_cpu(self, raw: str) -> str:
        # WMI reports "AMD Ryzen 5 3500U ...", the lists use the short "R5 3500U" form
        raw = re.sub(r"Ryzen\s+(\d)", r"R\1", raw, flags=re.IGNORECASE)
        match = find_best_match(raw, self.cfg.cpus)
        if match:
            return match
        m = CPU_PATTERN.search(raw)
        return find_best_match(m.group(0), self.cfg.cpus) if m else ""

    def detect_gpu(self, c) -> str:
        try:
            for gpu in c.Win32_VideoController():
                match = find_best_match(gpu.Name or "", self.cfg.gpus)
                if match:
                    return match
        except Exception as e:
            print(f"GPU error: {e}")
        return ""

    def detect_disk(self):
        smart_path = os.path.join(get_base_path(), "tools", "smartctl.exe")
        if not os.path.exists(smart_path):
            return "", ""
        try:
            proc = subprocess.run(
                [smart_path, "-j", "-a", "/dev/pd0"],
                capture_output=True, text=True, creationflags=NO_WINDOW,
            )
            js = json.loads(proc.stdout)
            capacity = js.get("user_capacity", {}).get("bytes", 0)
            return match_ssd_volume(capacity, self.cfg.ssd), self.parse_smart(js)
        except Exception as e:
            print(f"Disk error: {e}")
            return "", "Err/0/0"

    def parse_smart(self, js: dict) -> str:
        hours = cycles = 0
        if "nvme_smart_health_information_log" in js:
            log = js["nvme_smart_health_information_log"]
            hours = log.get("power_on_hours", 0)
            cycles = log.get("power_cycles", 0)
        elif "ata_smart_attributes" in js:
            for item in js["ata_smart_attributes"].get("table", []):
                if item["id"] == 9:
                    hours = item["raw"]["value"]
                if item["id"] == 12:
                    cycles = item["raw"]["value"]

        grade = "B"
        if hours < 1000:
            grade = "A"
        elif hours > 15000:
            grade = "C"
        return f"{grade}/{hours}/{cycles}"

    def reset_password_expiry(self) -> str:
        proc = subprocess.run(
            ["net", "accounts", "/maxpwage:unlimited"],
            capture_output=True, creationflags=NO_WINDOW,
        )
        return "Сброшен" if proc.returncode == 0 else "Не сброшен"
