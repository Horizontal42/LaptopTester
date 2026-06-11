# Loads sheet_config.json: spreadsheet layout and hardware option lists.
import json
import os
import sys
from dataclasses import dataclass

CONFIG_NAME = "sheet_config.json"


def get_base_path() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


@dataclass(frozen=True)
class AppConfig:
    worksheet: str
    serial_column: int
    columns: dict
    brands: list
    models: list
    cpus: list
    ram: list
    ssd: list
    gpus: list
    brand_aliases: dict


def load_config() -> AppConfig:
    path = os.path.join(get_base_path(), CONFIG_NAME)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{CONFIG_NAME} not found next to the program.\n"
            f"Copy sheet_config.example.json to {CONFIG_NAME} and adjust it."
        )
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    required = ["worksheet", "serial_column", "columns", "lists"]
    missing = [k for k in required if k not in raw]
    if missing:
        raise ValueError(f"{CONFIG_NAME}: missing keys: {', '.join(missing)}")

    lists = raw["lists"]
    return AppConfig(
        worksheet=raw["worksheet"],
        serial_column=int(raw["serial_column"]),
        columns={k: int(v) for k, v in raw["columns"].items()},
        brands=lists.get("brands", []),
        models=lists.get("models", []),
        cpus=lists.get("cpus", []),
        ram=lists.get("ram", []),
        ssd=lists.get("ssd", []),
        gpus=lists.get("gpus", []),
        brand_aliases=raw.get("brand_aliases", {}),
    )
