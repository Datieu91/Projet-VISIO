def classify_image(features, thresholds=None):
    """Simple configurable conditional rule engine. No ML model is used."""
    thresholds = thresholds or {}
    contrast_threshold = float(thresholds.get("contrast_threshold", 50))
    brightness_threshold = float(thresholds.get("brightness_threshold", 105))
    file_size_threshold_kb = int(thresholds.get("file_size_threshold_kb", 200))
    quality_threshold = int(thresholds.get("quality_warning_threshold", 60))
    decision_threshold = int(thresholds.get("decision_threshold", 50))

    contrast = float(features.get("contrast_level") or 0)
    brightness = float(features.get("brightness") or 0)
    file_size_kb = int(features.get("file_size_kb") or 0)
    quality_score = int(features.get("quality_score") or 0)

    score = 0
    reasons = []

    if contrast > contrast_threshold:
        score += 35
        reasons.append(f"contraste élevé > {contrast_threshold}")

    if brightness < brightness_threshold:
        score += 30
        reasons.append(f"luminosité faible < {brightness_threshold}")

    if file_size_kb > file_size_threshold_kb:
        score += 15
        reasons.append(f"fichier > {file_size_threshold_kb} Ko")

    if quality_score < quality_threshold:
        score += 10
        reasons.append(f"qualité image < {quality_threshold}")

    if score >= decision_threshold:
        return "Pleine", min(score + 10, 95), reasons or ["signaux visuels de remplissage"]

    return "Vide", max(55, 95 - score), reasons or ["aucun signal fort de remplissage"]
