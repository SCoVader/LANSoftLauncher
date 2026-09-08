import json
from pathlib import Path
from typing import Any, Dict

DEFAULT_CONFIG: Dict[str, Any] = {
    "role": "standalone",
    "server_host": "",
    "port": 8765,
    "apps": [
        {"name": "Notepad", "cmd": "notepad.exe"},
        {"name": "Calculator", "cmd": "calc.exe"},
        {"name": "Paint", "cmd": "mspaint.exe"},
    ],
}


def load_config(config_path: str | Path) -> Dict[str, Any]:
    path = Path(config_path)
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                if isinstance(data, dict):
                    return {**DEFAULT_CONFIG, **data}
                if isinstance(data, list) and data:
                    config = dict(DEFAULT_CONFIG)
                    config["apps"] = data
                    return config
    except Exception:
        pass

    try:
        save_config(path, dict(DEFAULT_CONFIG))
    except Exception:
        pass

    return dict(DEFAULT_CONFIG)


def save_config(config_path: str | Path, config: Dict[str, Any]) -> None:
    path = Path(config_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(config, fh, indent=2)
