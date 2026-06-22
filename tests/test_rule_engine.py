from rule_engine import classify_image
from risk_scoring import calculate_risk_score


def test_classify_image_returns_expected_labels():
    features = {
        "contrast_level": 80,
        "brightness": 60,
        "file_size_kb": 450,
        "quality_score": 90,
    }
    prediction, confidence, reasons = classify_image(features)
    assert prediction in ["Pleine", "Vide", "Débordante"]
    assert 0 <= confidence <= 100
    assert isinstance(reasons, list)


def test_risk_score_is_bounded():
    score, level, explanation = calculate_risk_score(
        "Débordante",
        95,
        "dangereux, encombrants",
        {"contrast_level": 90, "quality_score": 50},
    )
    assert 0 <= score <= 100
    assert level in ["Faible", "Moyen", "Élevé"]
    assert explanation
