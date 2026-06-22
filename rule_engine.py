def classify_image(features):
    """Simple conditional rule engine. No ML model is used."""
    contrast = float(features.get("contrast_level") or 0)
    brightness = float(features.get("brightness") or 0)
    file_size_kb = int(features.get("file_size_kb") or 0)
    quality_score = int(features.get("quality_score") or 0)

    score = 0
    reasons = []

    if contrast > 50:
        score += 35
        reasons.append("contraste élevé")

    if brightness < 100:
        score += 30
        reasons.append("luminosité faible")

    if file_size_kb > 200:
        score += 15
        reasons.append("fichier assez lourd")

    if quality_score < 60:
        score += 10
        reasons.append("qualité image incertaine")

    if score >= 75:
        return "Débordante", min(score + 10, 99), reasons
    if score >= 50:
        return "Pleine", min(score + 10, 99), reasons
    return "Vide", max(50, 95 - score), reasons or ["aucun signal fort de débordement"]
