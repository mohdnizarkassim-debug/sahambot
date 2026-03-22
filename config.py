import logging
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    bot_token: str
    log_file: str
    max_csv_size_bytes: int
    analysis_cooldown_seconds: int

    def validate(self, require_bot_token: bool = False):
        if require_bot_token and not self.bot_token:
            raise RuntimeError("BOT_TOKEN environment variable is required.")
        if self.max_csv_size_bytes <= 0:
            raise RuntimeError("MAX_CSV_SIZE_BYTES must be greater than 0.")
        if self.analysis_cooldown_seconds < 0:
            raise RuntimeError("ANALYSIS_COOLDOWN_SECONDS cannot be negative.")


@lru_cache(maxsize=1)
def get_settings():
    settings = Settings(
        bot_token=(os.environ.get("BOT_TOKEN") or "").strip(),
        log_file=(os.environ.get("SAHAMBOT_LOG_FILE") or "sahambot.log").strip() or "sahambot.log",
        max_csv_size_bytes=int(os.environ.get("MAX_CSV_SIZE_BYTES", str(1024 * 1024))),
        analysis_cooldown_seconds=int(os.environ.get("ANALYSIS_COOLDOWN_SECONDS", "5")),
    )
    settings.validate(require_bot_token=False)
    return settings


def setup_logging(settings: Settings):
    root_logger = logging.getLogger()

    log_path = Path(settings.log_file)
    if log_path.parent != Path("."):
        log_path.parent.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
    root_logger.setLevel(logging.INFO)

    existing_names = {handler.get_name() for handler in root_logger.handlers}

    if "sahambot_console" not in existing_names:
        console_handler = logging.StreamHandler()
        console_handler.set_name("sahambot_console")
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    if "sahambot_file" not in existing_names:
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.set_name("sahambot_file")
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)