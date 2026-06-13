[English](ARCHITECTURE.md)

# LaptopTester: архитектура

## Файлы

```
config.py                 # Загрузка sheet_config.json, валидация, AppConfig dataclass
scanner.py                # Определение железа (WMI/smartctl) в QThread; логика матчинга
sheet_manager.py          # Google Sheets auth (service account или OAuth) и запись строк
tester.py                 # PyQt5 GUI: страницы, QLineEdit/QComboBox, сигналы потока
sheet_config.example.json # Шаблон: имя листа, номера столбцов, списки железа, алиасы брендов
requirements.txt          # Зависимости: PyQt5, WMI, gspread, google-auth
LaptopTester.spec         # Конфиг PyInstaller (datas, hidden imports)
```

## Поток сканирования железа

1. Пользователь запускает приложение → `TesterApp.__init__` проверяет права админа, строит UI (3 страницы: загрузка, железо, тесты)
2. `start_scan()` создаёт `HardwareScanner` QThread с `AppConfig`
3. Scanner запрашивает WMI (бренд, модель, CPU, RAM) и smartctl (SMART данные SSD)
4. `find_best_match(raw_wmi_name, config_list)` нормализует имена и токены для сопоставления
   - Точное совпадение нормализованного названия побеждает
   - Fallback: самый длинный элемент из списка, чьи токены всё содержатся в сыром имени
   - Для GPU типа "NVIDIA MX: MX450" также пытается матчить только часть после `:`
5. Scanner отправляет `log()` сигнал → обновляется label прогресса; отправляет `finished(dict)` → вызывает `on_scan_finished()`
6. `on_scan_finished()` заполняет комбо-боксы: находит совпадающий элемент списка, вызывает `setCurrentIndex()`

## Поток передачи результатов в Google Sheets

1. Пользователь заполняет страницу железа, отмечает тесты, нажимает "ОТПРАВИТЬ"
2. `finish_testing()` собирает все данные формы в dict
3. Если включена группа второй батареи, добавляет `Bat2_Cyc`/`Bat2_Cap`
4. Валидирует серийный номер (не пустой) — показывает warning если пуст
5. Создаёт `SheetManager(url, cfg)` → подключается к таблице (service account или OAuth)
6. Вызывает `send_test_results(data_dict)`:
   - Ищет строку по серийному номеру в `cfg.serial_column`
   - Если найдена: обновляет; если не найдена: добавляет после последней заполненной
   - Итерирует столбцы из конфига: для каждого ключа в `cfg.columns` пишет соответствующее значение
7. Возвращает сообщение статуса, показывает в QMessageBox

## Добавление нового теста железа

1. Отредактируй `sheet_config.example.json` раздел `lists.gpus` (или другой список)
2. Добавь алиас бренда если нужно: `brand_aliases: {"Сырое имя": "Каноническое"}`
3. Перезапусти приложение — scanner использует новые списки

Чтобы добавить _новый тип_ проверки (например, WiFi):

1. Добавь в `sheet_config.example.json` столбец: `"WiFi": 51` (выбери свободный номер)
2. Добавь в `tester.py` функцию `init_tests_ui()`:
   ```python
   add(17, "WiFi", ["+", "-", "Нет инфы"], "🌐", None)
   ```
3. Добавь в `finish_testing()` в data dict:
   ```python
   "WiFi": self.checks["WiFi"].currentText(),
   ```
4. Обнови example-конфиг чтобы включить в `columns` — тогда будет писаться в таблицу

## Добавление нового определения железа

1. Добавь поле в `scanner.py` метод `HardwareScanner.run()`:
   ```python
   self.log.emit("New hardware...")
   data["NewField"] = self.detect_new_field()
   ```
2. Добавь соответствующий столбец в `sheet_config.example.json`
3. Добавь комбо-бокс или текстовое поле в `tester.py` страницу железа
4. Добавь в data dict в `finish_testing()`

## Хитрости

- **WMI имена грязные:** "NVIDIA GeForce RTX 3060" vs конфиг "NVIDIA RTX: 3060". Токенный матчинг это решает, но списки конфига нужно тщательно курировать (убирать дубликаты как "GeForce GT 620M" и "NVIDIA GT: GT 620M" одновременно).
- **Размеры SSD:** Диски报告ют десятичный GB (1 TB = 1e12 байт), но старый `int(bytes / 1024**3)` давал двоичный GiB. Теперь матчим по ближайшему размеру ±7%, так что 240 GB при 256e9 байт находит "240 GB" корректно.
- **AMD Ryzen формат:** WMI говорит "Ryzen 5 3500U", конфиг-списки используют "R5 3500U". Scanner нормализует "Ryzen X" → "RX" перед матчингом.
- **Порядок столбцов важен:** `sheet_config.json` ключи `columns` — это 1-индексированные номера столбцов Google Sheets. Столбец серийника — `serial_column` (используется для поиска/обновления), отдельно от карты `columns`.
- **Рескан:** Запущенный `HardwareScanner` поток блокирует UI до завершения. Если пользователь кликнет Рескан до конца, старый поток продолжает работать (potential race). Проверь `scanner.isRunning()` перед стартом нового, или заблокируй клик кнопки сигналом.
- **Сброс пароля:** `net accounts /maxpwage:unlimited` изменяет _состояние системы_. Выполняется молча в фоне; returncode 0 = успех. Нужны права админа или падает молча.
- **Пустой серийник:** `sheet_manager` проверяет на непустоту; если пуст, возвращает строку-ошибку (не пишется в таблицу). Вызывающий код (`tester.py`) должен валидировать перед вызовом.

## Формат конфигурации

Структура `sheet_config.json`:
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

Пустая строка в списке GPU = "нет дискретной видеокарты" (матчится с Intel/AMD встроенными).
