import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
VAULT_PATH = Path(os.getenv("VAULT_PATH", "C:/Users/oscar/ObsidianBrain"))
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
CLAUDE_MODEL = "claude-sonnet-4-6"
EMBED_MODEL = "all-MiniLM-L6-v2"
EMBEDDINGS_INDEX = VAULT_PATH / "sales" / ".embeddings.jsonl"

VAULT_DIRS = {
    "videos":     VAULT_PATH / "sales/videos",
    "tactics":    VAULT_PATH / "sales/tactics",
    "hooks":      VAULT_PATH / "sales/hooks",
    "objections": VAULT_PATH / "sales/objections",
    "scripts":    VAULT_PATH / "sales/scripts",
    "creators":   VAULT_PATH / "sales/creators",
    "calls":      VAULT_PATH / "sales/calls",
    "research":   VAULT_PATH / "sales/research",
}

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
DB_PATH = Path(os.getenv("DB_PATH", "sales_pro.db"))

def ensure_vault():
    for d in VAULT_DIRS.values():
        d.mkdir(parents=True, exist_ok=True)
    (VAULT_PATH / "sales/_Index.md").touch(exist_ok=True)
