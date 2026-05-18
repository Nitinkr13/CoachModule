import json
from pathlib import Path

CONFIG_ROOT = Path(__file__).resolve().parent


def _resolve_path(folder: str, name: str, suffix: str) -> Path:
    path = CONFIG_ROOT / folder / name
    if path.suffix != suffix:
        path = path.with_suffix(suffix)
    return path


def load_json(folder: str, name: str) -> dict:
    path = _resolve_path(folder, name, ".json")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_text(folder: str, name: str) -> str:
    path = _resolve_path(folder, name, ".txt")
    return path.read_text(encoding="utf-8")


def load_json_collection(folder: str) -> list[dict]:
    path = CONFIG_ROOT / folder
    if not path.exists():
        return []

    items: list[dict] = []
    for file_path in sorted(path.glob("*.json")):
        with file_path.open("r", encoding="utf-8") as handle:
            items.append(json.load(handle))
    return items
