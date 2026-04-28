from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
SECRETS_DIR = ROOT_DIR / "secrets"


def read_secret(filename: str) -> str:
    file_path = SECRETS_DIR / filename
    if not file_path.exists():
        raise FileNotFoundError(
            f"Secret file not found: {file_path}. "
            f"Please create it before starting the app."
        )

    value = file_path.read_text(encoding="utf-8").strip()
    if not value:
        raise ValueError(f"Secret file is empty: {file_path}")
    return value


def read_secret_optional(filename: str, default: str) -> str:
    file_path = SECRETS_DIR / filename
    if not file_path.exists():
        return default

    value = file_path.read_text(encoding="utf-8").strip()
    if not value:
        return default
    return value
