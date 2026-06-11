[Русский](README.ru.md)

# LaptopTester

A Windows QA tool for laptop acceptance testing: auto-detects hardware, walks you through a checklist, writes results to a Google Sheet.

```
python tester.py
# Scans WMI + smartctl → fills in brand, model, CPU, RAM, SSD, GPU
# → checklist page for sound/screen/keyboard/camera/... → one click sends to Google Sheets
```

> **Note:** The app runs `net accounts /maxpwage:unlimited` on startup to reset Windows password expiry. It requires **administrator privileges**.

## Install

**Requirements:** Windows 10/11, Python 3.9+

```
pip install -r requirements.txt
```

1. Copy `sheet_config.example.json` → `sheet_config.json` and adjust to your spreadsheet (worksheet name, column numbers, hardware lists).
2. Download the test utilities listed in [`tools/README.md`](tools/README.md) into the `tools/` folder.
3. Add Google credentials (one of):
   - `service_key.json` — service account key (recommended for shared use)
   - `credentials.json` — OAuth 2.0 client JSON (runs a browser login on first use)

## What it does

- **Hardware autodetect:** reads brand, model, CPU, RAM from WMI; disk capacity and SMART data (power-on hours, cycle count, health grade) from `smartctl`; GPU from WMI — matched against your configured lists.
- **Checklist page:** sound, screen, touchscreen, keyboard, camera, mic, touchpad, ports, biometrics, CMOS battery, BIOS/Windows password, LTE, drivers, display colours — each a pass/fail combo box.
- **Google Sheets write:** finds the row by serial number (updates if found, appends if not), writes all fields in one batch call.

## Handy things

- **Second battery:** check the "Вторая батарея" group box to enter a second battery's cycles/capacity.
- **Re-scan:** "Рескан" button reruns hardware detection without restarting the app.
- **SMART grade:** SSD info field shows `<grade>/<hours>/<cycles>` — A (<1000 h), B (1000–15000 h), C (>15000 h).

## For developers

Stack: Python 3, PyQt5, WMI, gspread, google-auth. Build: `pyinstaller LaptopTester.spec`

Column map and hardware option lists live in `sheet_config.json` — no code change needed to adapt to a different spreadsheet.

## Credits

Optional third-party utilities (not included — see `tools/README.md` for download links):
smartmontools, NirSoft BatteryInfoView, SoftwareOK IsMyLcdOK / IsMyTouchScreenOK, PassMark KeyboardTest, OCCT, CrystalDiskInfo.

## License

MIT
