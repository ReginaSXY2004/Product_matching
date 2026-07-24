from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
OUTPUT_DIR = DATA_DIR / "output"
DEBUG_DIR = ROOT_DIR / "debug"
DEBUG_SCREENSHOTS_DIR = DEBUG_DIR / "screenshots"
DEBUG_HTML_DIR = DEBUG_DIR / "html"
STORAGE_STATE_PATH = DATA_DIR / "taobao_storage_state.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
DEBUG_SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
DEBUG_HTML_DIR.mkdir(parents=True, exist_ok=True)
