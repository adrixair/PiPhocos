from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
SITE_DIR = PROJECT_ROOT / "site"
CONFIG_PATH = DATA_DIR / "config.yml"
DB_PATH = DATA_DIR / "db.sqlite"
GRABBER_LOG_PATH = DATA_DIR / "grabber.log"
SERVER_LOG_PATH = DATA_DIR / "server.log"
