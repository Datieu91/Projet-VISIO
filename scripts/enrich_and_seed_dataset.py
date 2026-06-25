"""Enrichit data/annotations.csv puis importe éventuellement le dataset dans SQLite.

Usage :
    python scripts\enrich_and_seed_dataset.py
    python scripts\enrich_and_seed_dataset.py --seed-db --reset --pending-count 6

Le CSV de départ doit contenir au minimum : path, manual_label.
Les labels attendus sont : vide / pleine.
"""

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
from image_processing import extract_features  # noqa: E402
from models import ImageReport  # noqa: E402
from risk_scoring import calculate_risk_score  # noqa: E402
from rule_engine import classify_image  # noqa: E402

DEFAULT_CSV = Path("data/annotations.csv")
DEFAULT_OUTPUT = Path("data/annotations_enriched.csv")
UPLOAD_FOLDER = Path("data/uploads")
DEFAULT_LAT = 48.8566
DEFAULT_LNG = 2.3522

FIELDNAMES = [
    "image_id", "filename", "path", "manual_label", "latitude", "longitude",
    "zone_type", "capture_date", "source", "tags", "split",
    "width", "height", "file_size_kb", "avg_color_hex", "brightness",
    "contrast_level", "quality_score", "quality_warning", "auto_label",
    "ai_confidence", "risk_score", "risk_level", "risk_explanation",
]


def normalize_label(label):
    label = (label or "").strip().lower()
    if label in {"vide", "empty", "clean"}:
        return "vide"
    if label in {"pleine", "plein", "full", "dirty"}:
        return "pleine"
    return ""


def title_label(label):
    return "Pleine" if normalize_label(label) == "pleine" else "Vide"


def safe_float(value, default=None):
    if value in (None, ""):
        return default
    try:
        return float(value)
    except ValueError:
        return default


def read_rows(csv_path):
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV introuvable : {csv_path}")
    with csv_path.open("r", encoding="utf-8", newline="") as csvfile:
        return list(csv.DictReader(csvfile))


def enrich_rows(rows):
    enriched = []
    for index, row in enumerate(rows, start=1):
        path = Path(row.get("path", ""))
        if not path.is_absolute():
            path = ROOT_DIR / path
        if not path.exists():
            print(f"⚠️ Image introuvable ignorée : {path}")
            continue

        manual = normalize_label(row.get("manual_label"))
        if manual not in {"vide", "pleine"}:
            print(f"⚠️ Label invalide ignoré : {row.get('manual_label')} pour {path.name}")
            continue

        features = extract_features(str(path))
        prediction, confidence, reasons = classify_image(features)
        risk_score, risk_level, risk_explanation = calculate_risk_score(
            prediction=prediction,
            confidence=confidence,
            tags=row.get("tags", ""),
            features=features,
        )

        lat = row.get("latitude") or str(round(DEFAULT_LAT + index * 0.001, 6))
        lng = row.get("longitude") or str(round(DEFAULT_LNG + index * 0.001, 6))

        output_row = {key: row.get(key, "") for key in FIELDNAMES}
        output_row.update({
            "image_id": row.get("image_id") or f"IMG_{index:03d}",
            "filename": row.get("filename") or path.name,
            "path": str(path.relative_to(ROOT_DIR)).replace("\\", "/") if path.is_relative_to(ROOT_DIR) else str(path),
            "manual_label": manual,
            "latitude": lat,
            "longitude": lng,
            "tags": row.get("tags", ""),
            "split": row.get("split") or ("train" if index % 4 else "test"),
            "width": features.get("width"),
            "height": features.get("height"),
            "file_size_kb": features.get("file_size_kb"),
            "avg_color_hex": features.get("avg_color_hex"),
            "brightness": features.get("brightness"),
            "contrast_level": features.get("contrast_level"),
            "quality_score": features.get("quality_score"),
            "quality_warning": features.get("quality_warning"),
            "auto_label": prediction.lower(),
            "ai_confidence": confidence,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "risk_explanation": f"{' | '.join(reasons)} | {risk_explanation}",
        })
        enriched.append(output_row)
    return enriched


def write_csv(rows, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def seed_database(rows, reset=False, pending_count=0):
    UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
    with app.app_context():
        if reset:
            ImageReport.query.delete()
            db.session.commit()

        inserted = 0
        for index, row in enumerate(rows, start=1):
            source_path = Path(row["path"])
            if not source_path.is_absolute():
                source_path = ROOT_DIR / source_path
            extension = source_path.suffix.lower()
            stored_filename = f"dataset_{index:03d}{extension}"
            destination_path = UPLOAD_FOLDER / stored_filename
            shutil.copy2(source_path, destination_path)

            status = "Pending" if index <= pending_count else "Validated"
            agent_annotation = None if status == "Pending" else title_label(row["manual_label"])

            report = ImageReport(
                stored_filename=stored_filename,
                filepath=f"/uploads/{stored_filename}",
                lat=safe_float(row.get("latitude")),
                lng=safe_float(row.get("longitude")),
                citizen_tags=row.get("tags", ""),
                file_size_kb=int(float(row.get("file_size_kb") or 0)),
                width=int(float(row.get("width") or 0)),
                height=int(float(row.get("height") or 0)),
                avg_color_hex=row.get("avg_color_hex"),
                brightness=safe_float(row.get("brightness"), 0),
                contrast_level=safe_float(row.get("contrast_level"), 0),
                quality_score=int(float(row.get("quality_score") or 0)),
                quality_warning=row.get("quality_warning"),
                ai_prediction=title_label(row.get("auto_label")),
                ai_confidence=int(float(row.get("ai_confidence") or 0)),
                risk_score=int(float(row.get("risk_score") or 0)),
                risk_level=row.get("risk_level"),
                risk_explanation=row.get("risk_explanation"),
                status=status,
                agent_annotation=agent_annotation,
            )
            db.session.add(report)
            inserted += 1
        db.session.commit()
    return inserted


def parse_args():
    parser = argparse.ArgumentParser(description="Enrichit le dataset et peut l'importer en base.")
    parser.add_argument("--csv", default=str(DEFAULT_CSV))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--seed-db", action="store_true")
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--pending-count", type=int, default=0)
    return parser.parse_args()


def main():
    args = parse_args()
    rows = read_rows(Path(args.csv))
    enriched = enrich_rows(rows)
    write_csv(enriched, Path(args.output))
    print(f"✅ CSV enrichi : {args.output}")
    print(f"🖼️ Images enrichies : {len(enriched)}")

    if args.seed_db:
        inserted = seed_database(enriched, reset=args.reset, pending_count=args.pending_count)
        print(f"✅ Signalements importés dans SQLite : {inserted}")


if __name__ == "__main__":
    main()
