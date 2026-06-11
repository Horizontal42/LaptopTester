# Google Sheets access: service-account or OAuth auth, row upsert by serial number.
import os

import gspread
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from config import AppConfig, get_base_path

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# gspread < 6 raises CellNotFound, gspread >= 6 returns None from find()
CELL_NOT_FOUND = getattr(gspread.exceptions, "CellNotFound", ())


class SheetManager:
    def __init__(self, sheet_url: str, cfg: AppConfig):
        self.sheet_url = sheet_url
        self.cfg = cfg

        base = get_base_path()
        self.service_key = os.path.join(base, "service_key.json")
        self.creds_file = os.path.join(base, "credentials.json")
        self.token_file = os.path.join(base, "token.json")

        self.doc = self.connect()

    def connect(self):
        if os.path.exists(self.service_key):
            client = gspread.service_account(filename=self.service_key)
            return client.open_by_url(self.sheet_url)

        creds = None
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)

        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                self.save_token(creds)
            except Exception:
                creds = None

        if not creds or not creds.valid:
            creds = self.perform_login()

        client = gspread.authorize(creds)
        return client.open_by_url(self.sheet_url)

    def perform_login(self):
        if not os.path.exists(self.creds_file):
            raise FileNotFoundError(
                "No Google credentials found: put service_key.json (service account) "
                "or credentials.json (OAuth client) next to the program."
            )
        flow = InstalledAppFlow.from_client_secrets_file(self.creds_file, SCOPES)
        creds = flow.run_local_server(port=0)
        self.save_token(creds)
        return creds

    def save_token(self, creds):
        with open(self.token_file, "w") as f:
            f.write(creds.to_json())

    def send_test_results(self, data: dict) -> str:
        ws = self.doc.worksheet(self.cfg.worksheet)
        serial = data.get("Serial", "").strip()

        serial_col = self.cfg.serial_column
        try:
            cell = ws.find(serial, in_column=serial_col)
        except CELL_NOT_FOUND:
            cell = None

        if cell:
            row, status = cell.row, "Обновлен"
        else:
            row, status = len(ws.col_values(serial_col)) + 1, "Создан новый"

        cells = [
            gspread.Cell(row, col, str(data[key]).strip())
            for key, col in self.cfg.columns.items()
            if key in data
        ]
        ws.update_cells(cells)
        return f"Успех: {serial} -> строка {row} ({status})"
