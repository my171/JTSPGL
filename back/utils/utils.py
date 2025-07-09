# Project Structure:
# ```
# backend/
# ├── db/
# │   ├── __init__.py
# │   ├── pool.py         # FixedDBPool, SQLiteConnectionPool, MySQLConnectionPoolWrapper
# │   └── schemas.py      # get_schema_and_samples, print_schema
# ├── indexer/
# │   ├── __init__.py
# │   └── vector_indexer.py  # UniversalDbVectorIndexer
# ├── nlp/
# │   ├── __init__.py
# │   └── manager.py      # NLDatabaseManager
# ├── generator/
# │   ├── __init__.py
# │   └── script_generator.py  # generate_script
# ├── utils.py              # common helpers, e.g., timestamp, backups
# ├── cli.py              # init_db_pool, main entrypoint
# └── README.md          # project overview, setup, and usage
# ```

# ---

# Example: **utils.py**
# ```python
import os
import shutil
import json
import datetime
import logging
from pathlib import Path
from typing import Any, Optional

import yaml


def get_timestamp(fmt: str = "%Y%m%d_%H%M%S") -> str:
    """
    Return current timestamp as a formatted string.
    """
    return datetime.datetime.now().strftime(fmt)


def ensure_dir(directory: str) -> None:
    """
    Create directory if it does not exist.
    """
    Path(directory).mkdir(parents=True, exist_ok=True)


def backup_file(src_path: str, backup_dir: str) -> str:
    """
    Copy a file to a backup directory with a timestamp prefix.
    Returns the destination path.
    """
    if not os.path.isfile(src_path):
        raise FileNotFoundError(f"Source file not found: {src_path}")

    ensure_dir(backup_dir)
    filename = os.path.basename(src_path)
    timestamp = get_timestamp()
    dest_path = os.path.join(backup_dir, f"{timestamp}_{filename}")
    shutil.copy2(src_path, dest_path)
    return dest_path


def read_json(path: str) -> Any:
    """
    Load JSON data from a file.
    """
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def write_json(data: Any, path: str) -> None:
    """
    Write data as JSON to a file, creating directories as needed.
    """
    directory = os.path.dirname(path)
    if directory:
        ensure_dir(directory)

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_yaml(path: str) -> Any:
    """
    Load YAML data from a file.
    """
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def setup_logging(log_file: Optional[str] = None, level: int = logging.INFO) -> None:
    """
    Configure root logger with console and optional file handlers.
    """
    handlers = [logging.StreamHandler()]

    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir:
            ensure_dir(log_dir)
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=level,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=handlers
    )