# Laptop QA wizard: scans hardware, collects test results, pushes them to Google Sheets.
import ctypes
import os
import subprocess
import sys

from PyQt5.QtCore import QSettings, Qt
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtWidgets import (
    QApplication, QComboBox, QFormLayout, QGridLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton, QScrollArea,
    QStackedWidget, QTextEdit, QVBoxLayout, QWidget,
)

from config import get_base_path, load_config
from scanner import HardwareScanner
from sheet_manager import SheetManager

# key (config column), label, options, optional tool button: text + command
CHECKS = [
    ("Sound", "Звук", ["+ / +", "+ / -", "- / +", "- / -"], "▶️", "sound_test.mp3"),
    ("Screen", "Экран", ["+", "-", "Нет инфы"], "🖥️", "IsMyLcdOK.exe"),
    ("Touchscreen", "Тачскрин", ["-", "+", "Его нет"], "👆", "IsMyTouchScreenOK_x64.exe"),
    ("Kbd", "Клавиатура", ["+", "-", "Нет инфы"], "⌨️", "KeyboardTest.exe"),
    ("Camera", "Камера", ["+", "-", "Нет инфы"], "📷", "Camera.exe"),
    ("Mic", "Микрофон", ["+", "-", "Нет инфы"], "🎤", "control mmsys.cpl sounds"),
    ("Touchpad_Sens", "Тачпад (Сенсор)", ["+", "-", "Нет инфы"], None, None),
    ("Touchpad_Btn", "Тачпад (Кнопки)", ["+", "-", "Их нет"], None, None),
    ("Ports", "Разъемы", ["+", "-", "Нет инфы"], None, None),
    ("Biometrics", "Сканер лица/пальца", ["- / -", "+ / +", "+ / -", "- / +"], "🔐", "devmgmt.msc"),
    ("CMOS", "Батарейка CMOS", ["+", "-", "Нет инфы"], None, None),
    ("Bios_Pass", "Пароль BIOS", ["Сброшен", "Не сброшен"], None, None),
    ("Win_Pass", "Срок пароля Win", ["Сброшен", "Не сброшен"], None, None),
    ("LTE", "LTE", ["LTE", "-"], None, None),
    ("Bat_Conn", "Подключение АКБ", ["Подключен", "Не подключен"], None, None),
    ("Drivers", "Драйверы", ["+", "-", "Нет инфы"], None, None),
    ("Colors", "Цвета", ["+", "-", "Нет инфы"], None, None),
]


def run_tool(filename: str):
    path = os.path.join(get_base_path(), "tools", filename)
    if os.path.exists(path):
        try:
            os.startfile(path)
        except OSError as e:
            QMessageBox.critical(None, "Ошибка", str(e))
    elif "Camera" in filename:
        subprocess.Popen("start microsoft.windows.camera:", shell=True)
    else:
        QMessageBox.critical(None, "Ошибка", f"Файл не найден:\n{path}")


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except OSError:
        return False


class TesterApp(QMainWindow):
    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self.setWindowTitle("Laptop QA Wizard")
        self.resize(600, 800)

        base = get_base_path()
        self.settings = QSettings(os.path.join(base, "settings.ini"), QSettings.IniFormat)

        icon_path = os.path.join(base, "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        if not is_admin():
            QMessageBox.warning(self, "Внимание", "Запустите от Админа!")

        self.scanner = None
        self.init_ui()
        self.start_scan()

    def init_ui(self):
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.page_load = QWidget()
        l_load = QVBoxLayout(self.page_load)
        self.lbl_load = QLabel("Сканирование...")
        self.lbl_load.setAlignment(Qt.AlignCenter)
        self.lbl_load.setFont(QFont("Arial", 16))
        l_load.addWidget(self.lbl_load)
        self.stack.addWidget(self.page_load)

        self.page_hw = QWidget()
        self.init_hw_ui()
        self.stack.addWidget(self.page_hw)

        self.page_tests = QWidget()
        self.init_tests_ui()
        self.stack.addWidget(self.page_tests)

    def make_combo(self, items) -> QComboBox:
        cb = QComboBox()
        cb.addItems(items)
        return cb

    def init_hw_ui(self):
        layout = QVBoxLayout(self.page_hw)
        scroll = QScrollArea()
        content = QWidget()
        form = QFormLayout(content)

        self.inp_serial = QLineEdit()
        self.inp_brand = self.make_combo(self.cfg.brands)
        self.inp_model = self.make_combo(self.cfg.models)
        self.inp_cpu = self.make_combo(self.cfg.cpus)
        self.inp_ram = self.make_combo(self.cfg.ram)
        self.inp_ssd_vol = self.make_combo(self.cfg.ssd)
        self.inp_ssd_info = QLineEdit()
        self.inp_gpu = self.make_combo(self.cfg.gpus)

        hb_bat = QHBoxLayout()
        self.inp_bat1_cyc = QLineEdit()
        self.inp_bat1_cyc.setPlaceholderText("Циклы")
        self.inp_bat1_cap = QLineEdit()
        self.inp_bat1_cap.setPlaceholderText("Емкость")
        btn_bat = QPushButton("🔋 BatView")
        btn_bat.clicked.connect(lambda: run_tool("battery_view.exe"))
        hb_bat.addWidget(self.inp_bat1_cyc)
        hb_bat.addWidget(self.inp_bat1_cap)
        hb_bat.addWidget(btn_bat)

        self.grp_bat2 = QGroupBox("Вторая батарея")
        self.grp_bat2.setCheckable(True)
        self.grp_bat2.setChecked(False)
        hb_bat2 = QHBoxLayout(self.grp_bat2)
        self.inp_bat2_cyc = QLineEdit()
        self.inp_bat2_cyc.setPlaceholderText("Циклы 2")
        self.inp_bat2_cap = QLineEdit()
        self.inp_bat2_cap.setPlaceholderText("Емкость 2")
        hb_bat2.addWidget(self.inp_bat2_cyc)
        hb_bat2.addWidget(self.inp_bat2_cap)

        form.addRow("Серийный номер:", self.inp_serial)
        form.addRow("Бренд:", self.inp_brand)
        form.addRow("Модель:", self.inp_model)
        form.addRow("CPU:", self.inp_cpu)
        form.addRow("RAM:", self.inp_ram)
        form.addRow("SSD Объем:", self.inp_ssd_vol)
        form.addRow("SSD Инфо:", self.inp_ssd_info)
        form.addRow("GPU:", self.inp_gpu)
        form.addRow("АКБ 1:", hb_bat)
        form.addRow(self.grp_bat2)

        self.inp_url = QLineEdit()
        self.inp_url.setPlaceholderText("URL Таблицы")
        self.inp_url.setText(self.settings.value("sheet_url", ""))
        form.addRow("Google URL:", self.inp_url)

        scroll.setWidget(content)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)

        h_btns = QHBoxLayout()
        btn_rescan = QPushButton("🔄 Рескан")
        btn_rescan.clicked.connect(self.start_scan)
        btn_next = QPushButton("Далее ->")
        btn_next.setFixedHeight(40)
        btn_next.clicked.connect(lambda: self.stack.setCurrentIndex(2))
        h_btns.addWidget(btn_rescan)
        h_btns.addWidget(btn_next)
        layout.addLayout(h_btns)

    def init_tests_ui(self):
        layout = QVBoxLayout(self.page_tests)
        scroll = QScrollArea()
        content = QWidget()
        grid = QGridLayout(content)
        self.checks = {}

        for r, (key, label, opts, bt_txt, bt_cmd) in enumerate(CHECKS):
            cb = self.make_combo(opts)
            grid.addWidget(QLabel(label), r, 0)
            grid.addWidget(cb, r, 1)
            if bt_txt:
                b = QPushButton(bt_txt)
                if bt_cmd.endswith((".exe", ".mp3")):
                    b.clicked.connect(lambda _, c=bt_cmd: run_tool(c))
                else:
                    b.clicked.connect(lambda _, c=bt_cmd: subprocess.Popen(c, shell=True))
                grid.addWidget(b, r, 2)
            self.checks[key] = cb

        row = len(CHECKS)
        grid.addWidget(QLabel("Комментарий:"), row, 0)
        self.inp_comment = QTextEdit()
        self.inp_comment.setMaximumHeight(60)
        grid.addWidget(self.inp_comment, row, 1, 1, 2)

        scroll.setWidget(content)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)

        h_btns = QHBoxLayout()
        btn_back = QPushButton("<- Назад")
        btn_back.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        btn_fin = QPushButton("🚀 ОТПРАВИТЬ")
        btn_fin.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        btn_fin.setFixedHeight(40)
        btn_fin.clicked.connect(self.finish_testing)
        h_btns.addWidget(btn_back)
        h_btns.addWidget(btn_fin)
        layout.addLayout(h_btns)

    def start_scan(self):
        if self.scanner and self.scanner.isRunning():
            return
        self.stack.setCurrentIndex(0)
        self.scanner = HardwareScanner(self.cfg)
        self.scanner.log.connect(self.lbl_load.setText)
        self.scanner.finished.connect(self.on_scan_finished)
        self.scanner.start()

    def on_scan_finished(self, data):
        self.inp_serial.setText(data.get("Serial", ""))
        self.inp_ssd_info.setText(data.get("SSD_Info", ""))

        def set_combo(cb, val):
            if not val:
                return
            idx = cb.findText(val)
            if idx >= 0:
                cb.setCurrentIndex(idx)

        set_combo(self.inp_brand, data.get("Brand", ""))
        set_combo(self.inp_model, data.get("Model", ""))
        set_combo(self.inp_cpu, data.get("CPU", ""))
        set_combo(self.inp_ram, data.get("RAM", ""))
        set_combo(self.inp_ssd_vol, data.get("SSD_Vol", ""))
        set_combo(self.inp_gpu, data.get("GPU", ""))

        if data.get("Win_Pass") == "Сброшен":
            self.checks["Win_Pass"].setCurrentText("Сброшен")

        self.stack.setCurrentIndex(1)

    def finish_testing(self):
        serial = self.inp_serial.text().strip()
        if not serial:
            QMessageBox.warning(self, "Ошибка", "Пустой серийный номер!")
            return
        url = self.inp_url.text().strip()
        if not url:
            QMessageBox.warning(self, "Ошибка", "Укажите URL таблицы!")
            return

        data = {
            "Serial": serial,
            "Brand": self.inp_brand.currentText(),
            "Model": self.inp_model.currentText(),
            "CPU": self.inp_cpu.currentText(),
            "RAM": self.inp_ram.currentText(),
            "SSD_Vol": self.inp_ssd_vol.currentText(),
            "SSD_Info": self.inp_ssd_info.text(),
            "GPU": self.inp_gpu.currentText(),
            "Bat1_Cyc": self.inp_bat1_cyc.text(),
            "Bat1_Cap": self.inp_bat1_cap.text(),
            "Comment": self.inp_comment.toPlainText(),
        }
        for key, cb in self.checks.items():
            data[key] = cb.currentText()
        if self.grp_bat2.isChecked():
            data["Bat2_Cyc"] = self.inp_bat2_cyc.text()
            data["Bat2_Cap"] = self.inp_bat2_cap.text()

        self.settings.setValue("sheet_url", url)

        try:
            manager = SheetManager(url, self.cfg)
            res = manager.send_test_results(data)
            QMessageBox.information(self, "Готово", res)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка отправки", str(e))


def main():
    app = QApplication(sys.argv)
    try:
        cfg = load_config()
    except (FileNotFoundError, ValueError) as e:
        QMessageBox.critical(None, "Ошибка конфигурации", str(e))
        sys.exit(1)
    window = TesterApp(cfg)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
