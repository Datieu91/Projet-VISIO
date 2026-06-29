import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))
os.chdir(ROOT_DIR)

from app import app, seed_default_settings, seed_default_bin_locations
from database import db
from config import DB_PATH, UPLOAD_FOLDER


def main():
    with app.app_context():
        db.drop_all()
        db.create_all()
        seed_default_settings()
        seed_default_bin_locations()

    Path(UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)
    for item in Path(UPLOAD_FOLDER).iterdir():
        if item.name == ".gitkeep":
            continue
        if item.is_file():
            item.unlink()

    print("✅ Base réinitialisée.")
    print(f"📍 Base utilisée : {DB_PATH}")
    print(f"📁 Uploads vidés : {UPLOAD_FOLDER}")


if __name__ == "__main__":
    main()
