import os
from pathlib import Path
from typing import Iterable


def _iter_env_lines(path: Path) -> Iterable[str]:
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").splitlines()


def _apply_env_lines(lines: Iterable[str]) -> None:
    for line in lines:
        entry = line.strip()
        if not entry or entry.startswith("#") or "=" not in entry:
            continue
        key, value = entry.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


def load_env() -> None:
    root = Path(__file__).resolve().parents[1]
    candidates = [
        root / ".env",
        root / ".env.local",
    ]

    for path in candidates:
        _apply_env_lines(_iter_env_lines(path))
