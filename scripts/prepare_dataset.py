import csv
import shutil
from pathlib import Path
from datetime import date

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")
OUTPUT_CSV = Path("data/annotations.csv")
LABELS = ["vide", "pleine"]
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
TRAIN_RATIO = 0.7


def get_images(folder: Path):
    if not folder.exists():
        print(f"⚠️ Dossier introuvable : {folder}")
        return []
    return sorted([
        file for file in folder.iterdir()
        if file.is_file() and file.suffix.lower() in IMAGE_EXTENSIONS
    ])


def prepare_dataset():
    rows = []
    global_image_id = 1
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    for label in LABELS:
        input_folder = RAW_DIR / label
        output_folder = PROCESSED_DIR / label
        output_folder.mkdir(parents=True, exist_ok=True)
        images = get_images(input_folder)

        if not images:
            print(f"⚠️ Aucune image trouvée pour la classe : {label}")
            continue

        train_limit = int(len(images) * TRAIN_RATIO)

        for index, image_path in enumerate(images, start=1):
            extension = image_path.suffix.lower()
            new_filename = f"{label}_{index:03d}{extension}"
            new_path = output_folder / new_filename
            shutil.copy2(image_path, new_path)
            split = "train" if index <= train_limit else "test"

            rows.append({
                "image_id": f"IMG_{global_image_id:03d}",
                "filename": new_filename,
                "path": str(new_path).replace("\\", "/"),
                "manual_label": label,
                "latitude": "",
                "longitude": "",
                "zone_type": "",
                "capture_date": date.today().isoformat(),
                "source": "equipe",
                "tags": "",
                "split": split,
            })
            global_image_id += 1

    fieldnames = [
        "image_id", "filename", "path", "manual_label", "latitude", "longitude",
        "zone_type", "capture_date", "source", "tags", "split"
    ]

    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("✅ Dataset préparé avec succès.")
    print(f"📁 Images renommées dans : {PROCESSED_DIR}")
    print(f"📄 Fichier CSV créé : {OUTPUT_CSV}")
    print(f"🖼️ Nombre total d'images : {len(rows)}")


if __name__ == "__main__":
    prepare_dataset()
