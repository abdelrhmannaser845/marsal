import os
import sys
from pathlib import Path
from dataclasses import dataclass, field
from dotenv import load_dotenv


def _resolve_base_dir() -> Path:
    """Resolve writable base directory whether running from source or frozen PyInstaller .exe."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent.parent


def _load_env_files() -> Path:
    """Load .env from executable dir, working dir, source root, or PyInstaller bundle."""
    base_dir = _resolve_base_dir()
    candidates = [
        base_dir / ".env",
        Path.cwd() / ".env",
        Path(__file__).resolve().parent.parent.parent / ".env",
    ]
    if hasattr(sys, "_MEIPASS"):
        candidates.append(Path(sys._MEIPASS) / ".env")

    for env_path in candidates:
        if env_path.exists():
            load_dotenv(dotenv_path=env_path, override=False)
            break
    return base_dir


# Load .env file from project root or executable directory
BASE_DIR = _load_env_files()


@dataclass
class SMTPConfig:
    host: str = field(default_factory=lambda: os.getenv("SMTP_HOST", "smtp.gmail.com"))
    port: int = field(default_factory=lambda: int(os.getenv("SMTP_PORT", "587")))
    user: str = field(default_factory=lambda: os.getenv("SMTP_USER", ""))
    password: str = field(default_factory=lambda: os.getenv("SMTP_PASSWORD", ""))
    from_email: str = field(default_factory=lambda: os.getenv("SMTP_FROM_EMAIL", os.getenv("SMTP_USER", "")))
    from_name: str = field(default_factory=lambda: os.getenv("SMTP_FROM_NAME", "Academic Notification"))
    use_tls: bool = field(default_factory=lambda: os.getenv("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes"))


@dataclass
class WhatsAppConfig:
    provider: str = field(default_factory=lambda: os.getenv("WA_PROVIDER", "pywhatkit").lower())
    meta_phone_number_id: str = field(default_factory=lambda: os.getenv("META_WA_PHONE_NUMBER_ID", ""))
    meta_access_token: str = field(default_factory=lambda: os.getenv("META_WA_ACCESS_TOKEN", ""))
    meta_api_version: str = field(default_factory=lambda: os.getenv("META_WA_API_VERSION", "v20.0"))


@dataclass
class ThrottleConfig:
    min_delay_seconds: float = field(default_factory=lambda: float(os.getenv("MIN_DELAY_SECONDS", "5.0")))
    max_delay_seconds: float = field(default_factory=lambda: float(os.getenv("MAX_DELAY_SECONDS", "12.0")))


@dataclass
class AppConfig:
    smtp: SMTPConfig = field(default_factory=SMTPConfig)
    whatsapp: WhatsAppConfig = field(default_factory=WhatsAppConfig)
    throttle: ThrottleConfig = field(default_factory=ThrottleConfig)
    db_path: Path = field(default_factory=lambda: BASE_DIR / os.getenv("DB_PATH", "data/dispatches.db"))
    base_dir: Path = BASE_DIR


def get_config() -> AppConfig:
    """Returns application configuration instance."""
    return AppConfig()
