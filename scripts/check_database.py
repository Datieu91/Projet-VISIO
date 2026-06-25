import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))
os.chdir(ROOT_DIR)

from app import app
from models import ImageReport
from config import DB_PATH

with app.app_context():
    count = ImageReport.query.count()
    pending = ImageReport.query.filter_by(status="Pending").count()
    validated = ImageReport.query.filter_by(status="Validated").count()
    ignored = ImageReport.query.filter_by(status="Ignored").count()
    print(f"Base : {DB_PATH}")
    print(f"Total signalements : {count}")
    print(f"En attente : {pending}")
    print(f"Validés : {validated}")
    print(f"Ignorés : {ignored}")
    for report in ImageReport.query.order_by(ImageReport.id.desc()).limit(5).all():
        print(report.id, report.stored_filename, report.status, report.ai_prediction, report.risk_score)
