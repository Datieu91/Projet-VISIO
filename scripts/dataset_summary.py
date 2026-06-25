import csv
from pathlib import Path

FILES = [Path("data/annotations.csv"), Path("data/annotations_enriched.csv")]


def summarize(path):
    print(f"\n=== {path} ===")
    if not path.exists():
        print("Fichier absent.")
        return
    with path.open("r", encoding="utf-8", newline="") as csvfile:
        rows = list(csv.DictReader(csvfile))
    labels = {}
    splits = {}
    for row in rows:
        labels[row.get("manual_label", "non_renseigne")] = labels.get(row.get("manual_label", "non_renseigne"), 0) + 1
        splits[row.get("split", "non_renseigne")] = splits.get(row.get("split", "non_renseigne"), 0) + 1
    print(f"Images : {len(rows)}")
    print(f"Labels : {labels}")
    print(f"Split : {splits}")
    if rows:
        print(f"Colonnes : {', '.join(rows[0].keys())}")


if __name__ == "__main__":
    for file in FILES:
        summarize(file)
