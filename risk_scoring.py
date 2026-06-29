def calculate_risk_score(prediction, confidence, tags, features, thresholds=None):
    """Calculate a risk score from 0 to 100 and return score, level and explanation."""
    thresholds = thresholds or {}
    medium_threshold = int(thresholds.get("risk_medium_threshold", 30))
    high_threshold = int(thresholds.get("risk_high_threshold", 70))

    score = 0
    explanations = []
    tags_text = (tags or "").lower()

    if prediction == "Vide":
        score += 5
        explanations.append("état détecté comme vide: +5")
    elif prediction == "Pleine":
        score += 50
        explanations.append("état détecté comme pleine: +50")

    if confidence and confidence >= 80:
        score += 5
        explanations.append("confiance élevée de la règle: +5")

    if "dangereux" in tags_text:
        score += 20
        explanations.append("tag dangereux: +20")

    if "encombrant" in tags_text:
        score += 15
        explanations.append("tag encombrants: +15")

    if "odeur" in tags_text:
        score += 10
        explanations.append("tag odeur: +10")

    contrast = float(features.get("contrast_level") or 0)
    if contrast > 65:
        score += 10
        explanations.append("contraste très élevé: +10")

    quality_score = int(features.get("quality_score") or 100)
    if quality_score < 60:
        score += 10
        explanations.append("qualité image faible, intervention de vérification: +10")

    score = min(score, 100)

    if score < medium_threshold:
        level = "Faible"
    elif score < high_threshold:
        level = "Moyen"
    else:
        level = "Élevé"

    return score, level, " | ".join(explanations)
