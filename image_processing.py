import os
from PIL import Image, ImageStat

try:
    import cv2
except Exception:  # OpenCV is optional at runtime.
    cv2 = None


def _safe_round(value, digits=2):
    try:
        return round(float(value), digits)
    except Exception:
        return 0.0


def extract_features(filepath):
    """Extract simple visual characteristics from an uploaded image."""
    features = {
        "file_size_kb": 0,
        "width": 0,
        "height": 0,
        "avg_color_hex": "#000000",
        "brightness": 0.0,
        "contrast_level": 0.0,
        "quality_score": 100,
        "quality_warning": "",
    }

    warnings = []

    if not os.path.exists(filepath):
        features["quality_score"] = 0
        features["quality_warning"] = "Fichier introuvable"
        return features

    features["file_size_kb"] = int(os.path.getsize(filepath) / 1024)

    try:
        with Image.open(filepath) as img:
            features["width"], features["height"] = img.size
            img_rgb = img.convert("RGB")
            stat = ImageStat.Stat(img_rgb)
            r, g, b = [int(v) for v in stat.mean]
            features["avg_color_hex"] = f"#{r:02x}{g:02x}{b:02x}"
            features["brightness"] = _safe_round(0.299 * r + 0.587 * g + 0.114 * b)

            gray = img.convert("L")
            gray_stat = ImageStat.Stat(gray)
            features["contrast_level"] = _safe_round(gray_stat.stddev[0])
    except Exception as exc:
        features["quality_score"] = 30
        features["quality_warning"] = f"Erreur d'analyse image : {exc}"
        return features

    if features["width"] < 300 or features["height"] < 300:
        features["quality_score"] -= 25
        warnings.append("image trop petite")

    if features["brightness"] < 45:
        features["quality_score"] -= 20
        warnings.append("image très sombre")

    if features["file_size_kb"] > 5000:
        features["quality_score"] -= 10
        warnings.append("image lourde")

    if cv2 is not None:
        try:
            cv_img = cv2.imread(filepath)
            if cv_img is not None:
                gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
                blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
                if blur_score < 50:
                    features["quality_score"] -= 15
                    warnings.append("image possiblement floue")
        except Exception:
            # Keep the Pillow-based result if OpenCV fails.
            pass

    features["quality_score"] = max(0, min(100, int(features["quality_score"])))
    features["quality_warning"] = ", ".join(warnings) if warnings else "OK"
    return features
