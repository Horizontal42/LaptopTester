# LaptopTester Architecture

## Files

```
config.py                 # Load sheet_config.json, validate, expose AppConfig dataclass
scanner.py                # WMI/smartctl hardware detection in QThread; matching logic
sheet_manager.py          # Google Sheets auth (service account or OAuth) and row upsert
tester.py                 # PyQt5 GUI: pages, QLineEdit/QComboBox fields, thread signals
sheet_config.example.json # Template: worksheet, column numbers, hardware lists, brand aliases
requirements.txt          # Dependencies: PyQt5, WMI, gspread, google-auth libs
LaptopTester.spec         # PyInstaller config (datas, hidden imports)
```

## How hardware scan flows

1. User starts app → `TesterApp.__init__` checks admin rights, builds UI (3 pages: load, hardware, tests)
2. `start_scan()` spawns `HardwareScanner` QThread with `AppConfig`
3. Scanner queries WMI for brand, model, CPU, RAM; smartctl for SSD SMART data
4. `find_best_match(raw_wmi_name, config_list)` normalizes names and tokens to match against lists
   - Exact normalized match wins
   - Falls back to longest list entry whose tokens all appear in raw name
   - For GPU entries like "NVIDIA MX: MX450", also tries matching only the model part (after `:`)
5. Scanner emits `log()` signal → progress label updates; emits `finished(dict)` → `on_scan_finished()`
6. `on_scan_finished()` populates combo boxes: finds matching list entry, calls `setCurrentIndex()`

## How results flow to Google Sheets

1. User fills hardware page, checks tests, clicks "ОТПРАВИТЬ"
2. `finish_testing()` gathers all form data into dict
3. If second battery group checked, adds `Bat2_Cyc`/`Bat2_Cap`
4. Validates serial number (non-empty) — shows warning if missing
5. Creates `SheetManager(url, cfg)` → connects to sheet (service account or OAuth)
6. Calls `send_test_results(data_dict)`:
   - Finds row by serial number in `cfg.serial_column`
   - If found: updates; if not found: appends after last filled row
   - Iterates config columns: for each key in `cfg.columns`, writes corresponding data value
7. Returns status message, shows in QMessageBox

## Adding new hardware checks

1. Edit `sheet_config.example.json` `lists.gpus` (or other list)
2. Add brand alias if needed: `brand_aliases: {"Raw Name": "Canonical"}`
3. Restart app — scanner uses new lists

To add a _new type_ of check (e.g., WiFi module):

1. Add to `sheet_config.example.json` columns: `"WiFi": 51` (pick next free column)
2. Add to `tester.py` `init_tests_ui()`:
   ```python
   add(17, "WiFi", ["+", "-", "Не инфы"], "🌐", None)
   ```
3. Add to `finish_testing()` data dict:
   ```python
   "WiFi": self.checks["WiFi"].currentText(),
   ```
4. Update example config to include in `columns` so it gets written

## Adding new hardware detection

1. Add field to `scanner.py` `HardwareScanner.run()`:
   ```python
   self.log.emit("New hardware...")
   data["NewField"] = self.detect_new_field()
   ```
2. Add corresponding column to `sheet_config.example.json`
3. Add combo box or text field to `tester.py` hardware page
4. Add to data dict in `finish_testing()`

## Gotchas

- **WMI names are messy:** "NVIDIA GeForce RTX 3060" vs config "NVIDIA RTX: 3060". Token matching handles this, but config lists must be carefully curated (ditch duplicates like both "GeForce GT 620M" and "NVIDIA GT: GT 620M").
- **SSD sizes:** Drives report decimal GB (1 TB = 1e12 bytes), but older `int(bytes / 1024**3)` gave binary GiB. Now matches by closest size ±7%, so 240 GB at 256e9 bytes finds "240 GB" correctly.
- **AMD Ryzen format:** WMI says "Ryzen 5 3500U", config lists use "R5 3500U". Scanner normalizes "Ryzen X" → "RX" before matching.
- **Column order matters:** `sheet_config.json` `columns` dict values are 1-indexed Google Sheets column numbers. Serial column is `serial_column` (used for find/upsert logic), separate from `columns` map.
- **Rescan:** Once started, `HardwareScanner` thread blocks until done. If user clicks Rescan again before done, old thread keeps running (potential race). Check `scanner.isRunning()` before starting new one, or emit a signal to prevent UI clicks.
- **Password reset:** `net accounts /maxpwage:unlimited` changes _system state_. Runs silently in background; returncode 0 = success. Needs admin rights or fails silently.
- **Empty serial number:** `sheet_manager` checks for non-empty serial; if empty, returns error string (not written to sheet). Caller (`tester.py`) should validate before calling.

## Config format

`sheet_config.json` structure:
```json
{
  "worksheet": "Laptops",
  "serial_column": 21,
  "columns": {
    "Brand": 19,
    "CPU": 22,
    ...
  },
  "brand_aliases": {
    "Hewlett-Packard": "HP",
    ...
  },
  "lists": {
    "brands": ["HP", "Lenovo", ...],
    "models": [...],
    "cpus": [...],
    "ram": [...],
    "ssd": [...],
    "gpus": ["", "NVIDIA RTX: 3060", ...]
  }
}
```

Empty string in GPU list = "no dedicated GPU" (matches Intel/AMD integrated).
