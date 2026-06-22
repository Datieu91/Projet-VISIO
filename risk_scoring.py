def calculate_risk_score(prediction, confidence, tags, features):
    """Calculate a risk score from 0 to 100 and return score, level and explanation."""
    score = 0
    explanations = []
    tags_text = (tags or "").lower()

    if prediction == "Vide":
        explanations.append("état détecté comme vide: +0")
    elif prediction == "Pleine":
        score += 45
        explanations.append("état détecté comme pleine: +45")
    elif prediction == "Débordante":
        score += 65
        explanations.append("état détecté comme débordante: +65")

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

    if score < 30:
        level = "Faible"
    elif score < 70:
        level = "Moyen"
    else:
        level = "Élevé"

    return score, level, " | ".join(explanations)
