# tools/

Third-party utilities the app launches. They are not redistributable, so download
them yourself and place them in this folder with these exact file names.

Used by the app:

| File | What it is | Where to get it |
|------|------------|-----------------|
| `smartctl.exe` | SSD health/capacity readout (required for disk autodetect) | [smartmontools](https://www.smartmontools.org/) — take `smartctl.exe` from the installed `bin/` |
| `battery_view.exe` | Battery cycles/capacity viewer | [NirSoft BatteryInfoView](https://www.nirsoft.net/utils/battery_information_view.html) — rename `BatteryInfoView.exe` |
| `IsMyLcdOK.exe` | Dead-pixel / LCD test | [SoftwareOK](http://www.softwareok.com/?seite=Microsoft/IsMyLcdOK) |
| `IsMyTouchScreenOK_x64.exe` | Touchscreen test | [SoftwareOK](http://www.softwareok.com/?seite=Software/IsMyTouchScreenOK) |
| `KeyboardTest.exe` | Keyboard test (shareware) | [PassMark KeyboardTest](https://www.passmark.com/products/keytest/) |
| `Camera.exe` | Camera test (optional — without it the app opens the Windows Camera app) | any portable camera viewer |
| `sound_test.mp3` | Stereo speaker test track | any track with distinct left/right channels |

Optional extras (launched manually, not from the app):

| File | What it is | Where to get it |
|------|------------|-----------------|
| `OCCT.exe` | Stress test | [OCBASE/OCCT](https://www.ocbase.com/) |
| `CrystalDiskInfo/` | Disk SMART GUI | [CrystalDiskInfo](https://crystalmark.info/en/software/crystaldiskinfo/) |
