"""Константы Realtor OS."""



PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"
CONFIG_PATH = PROJECT_ROOT / "config.yaml"
MANIFEST_PATH = PROJECT_ROOT / "buffy_manifest.json"
STATE_PATH = PROJECT_ROOT / "companion" / "state.json"

DEFAULT_CHUNK_SIZE = 512
DEFAULT_OVERLAP = 64
DEFAULT_MAX_RESULTS = 5
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LLM_TIMEOUT = 60
