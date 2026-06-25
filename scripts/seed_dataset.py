import argparse
import csv
import os
import shutil
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))
os.chdir(ROOT_DIR)

from app import app  # noqa: E402
from database import db  # noqa: E402
from models import ImageReport  # noqa: E402
from image_processing import extract_features  # noqa: E402
from rule_engine import classify_image  # noqa: E402
from risk_scoring import calculate_risk_score  # noqa: E402

ANNOTATIONS_CSV = Path("data/annotations.csv")
UPLOAD_FOLDER = Path("data/uploads")
DEFAULT_LAT = 48.8566
DEFAULT_LNG = 2.3522


def safe_float(value, default=None):
    if value is None or value == "":
        return default
    try:
        return float(value)
    except ValueError:
        return default


def normalize_label(label):
    label = (label or "").strip().lower()
    if label == "vide":
        return "Vide"
    if label == "pleine":
        return "Pleine"
    return None


def parse_args():
    parser = argparse.ArgumentParser(description="Importe annotations.csv dans SQLite.")
    parser.add_argument("--csv", default=str(ANNOTATIONS_CSV), help="Chemin du CSV d'annotations.")
    parser.add_argument("--reset", action="store_true", help="Vide les signalements existants avant import.")
    parser.add_argument(
        "--pending-count",
        type=int,
        default=0,
        help="Nombre d'images importées en Pending pour tester la modération. Défaut: 0.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    csv_path = Path(args.csv)

    if not csv_path.exists():
        raise FileNotFoundError("Le fichier data/annotations.csv est introuvable.")

    UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

    with app.app_context():
        if args.reset:
            print("Suppression des anciennes données...")
            ImageReport.query.delete()
            db.session.commit()

        with csv_path.open("r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            inserted_count = 0

            for index, row in enumerate(reader, start=1):
                manual_label = normalize_label(row.get("manual_label"))
                if manual_label is None:
                    print(f"Image ignorée : label invalide -> {row.get('manual_label')}")
                    continue

                source_path = Path(row["path"])
                if not source_path.exists():
                    print(f"Image introuvable : {source_path}")
                    continue

                extension = source_path.suffix.lower()
                stored_filename = f"dataset_{index:03d}{extension}"
                destination_path = UPLOAD_FOLDER / stored_filename
                shutil.copy2(source_path, destination_path)

                features = extract_features(str(destination_path))
                prediction, confidence, reasons = classify_image(features)
                tags = row.get("tags", "")
                risk_score, risk_level, risk_explanation = calculate_risk_score(
                    prediction=prediction,
                    confidence=confidence,
                    tags=tags,
                    features=features,
                )

                status = "Pending" if index <= args.pending_count else "Validated"
                agent_annotation = None if status == "Pending" else manual_label
                lat = safe_float(row.get("latitude"), DEFAULT_LAT + index * 0.001)
                lng = safe_float(row.get("longitude"), DEFAULT_LNG + index * 0.001)

                report = ImageReport(
                    stored_filename=stored_filename,
                    filepath=f"/uploads/{stored_filename}",
                    lat=lat,
                    lng=lng,
                    citizen_tags=tags,
                    file_size_kb=features.get("file_size_kb"),
                    width=features.get("width"),
                    height=features.get("height"),
                    avg_color_hex=features.get("avg_color_hex"),
                    brightness=features.get("brightness"),
                    contrast_level=features.get("contrast_level"),
                    quality_score=features.get("quality_score"),
                    quality_warning=features.get("quality_warning"),
                    ai_prediction=prediction,
                    ai_confidence=confidence,
                    risk_score=risk_score,
                    risk_level=risk_level,
                    risk_explanation=f"{' | '.join(reasons)} | {risk_explanation}",
                    status=status,
                    agent_annotation=agent_annotation,
                )
                db.session.add(report)
                inserted_count += 1

            db.session.commit()

        print(f"Import terminé : {inserted_count} signalements ajoutés.")
        print(f"Images en attente de modération : {args.pending_count}")


if __name__ == "__main__":
    main()
