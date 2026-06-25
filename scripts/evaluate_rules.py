import csv
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))
os.chdir(ROOT_DIR)

from app import app, _compute_rule_metrics  # noqa: E402
from models import ImageReport  # noqa: E402


def print_metrics(title, metrics):
    print(f"\n=== {title} ===")
    print(f"Total évalué : {metrics['total']}")
    print(f"Correct : {metrics['correct']}")
    print(f"Accuracy : {metrics['accuracy']}%")
    print("Matrice :")
    print("           pred Vide | pred Pleine")
    print(f"truth Vide     {metrics['matrix']['Vide']['Vide']:>5} | {metrics['matrix']['Vide']['Pleine']:>5}")
    print(f"truth Pleine   {metrics['matrix']['Pleine']['Vide']:>5} | {metrics['matrix']['Pleine']['Pleine']:>5}")
    for label, values in metrics["per_class"].items():
        print(f"{label} : precision={values['precision']}% recall={values['recall']}%")


def evaluate_db():
    with app.app_context():
        reports = ImageReport.query.filter(
            ImageReport.agent_annotation.in_(["Vide", "Pleine"]),
            ImageReport.ai_prediction.in_(["Vide", "Pleine"]),
        ).all()
        return _compute_rule_metrics([(r.agent_annotation, r.ai_prediction) for r in reports])


def evaluate_csv(path=Path("data/annotations_enriched.csv")):
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8", newline="") as csvfile:
        rows = list(csv.DictReader(csvfile))
    return _compute_rule_metrics([(row.get("manual_label"), row.get("auto_label")) for row in rows])


if __name__ == "__main__":
    print_metrics("Base SQLite", evaluate_db())
    csv_metrics = evaluate_csv()
    if csv_metrics is None:
        print("\nCSV enrichi absent : lance python scripts\\enrich_and_seed_dataset.py")
    else:
        print_metrics("CSV enrichi", csv_metrics)
