import os
from functools import lru_cache


def _strip_wrapping_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def _project_env_path() -> str:
    return os.path.join(os.getcwd(), ".env")


@lru_cache(maxsize=16)
def _load_kv_file(path: str) -> dict[str, str]:
    data: dict[str, str] = {}
    if not os.path.exists(path):
        return data
    with open(path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = _strip_wrapping_quotes(value.strip())
            data[key] = value
    return data


def get_config(key: str, default: str | None = None) -> str | None:
    file_data = _load_kv_file(_project_env_path())
    if key in file_data and file_data[key] != "":
        return file_data[key]
    return default
