import os
import uuid
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, send_from_directory, url_for
from werkzeug.utils import secure_filename

from config import (
    ALLOWED_EXTENSIONS,
    DB_FOLDER,
    MAX_CONTENT_LENGTH,
    SQLALCHEMY_DATABASE_URI,
    SQLALCHEMY_TRACK_MODIFICATIONS,
    UPLOAD_FOLDER,
)
from database import db
from image_processing import extract_features
from models import ImageReport
from risk_scoring import calculate_risk_score
from rule_engine import classify_image


def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = SQLALCHEMY_TRACK_MODIFICATIONS
    app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)
    app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

    # SQLite can create the .db file, but not the parent folders.
    Path(DB_FOLDER).mkdir(parents=True, exist_ok=True)
    Path(UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)

    db.init_app(app)

    with app.app_context():
        db.create_all()

    return app


app = create_app()


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def home():
    return redirect(url_for("citoyen_app"))


@app.route("/citoyen")
def citoyen_app():
    return render_template("citoyen.html", active="citoyen")


@app.route("/agent")
def agent_app():
    return render_template("agent.html", active="agent")


@app.route("/dashboard")
def dashboard_app():
    return render_template("dashboard.html", active="dashboard")



@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


@app.route("/api/upload", methods=["POST"])
def upload_image():
    if "image" not in request.files:
        return jsonify({"error": "Aucune image envoyée"}), 400

    file = request.files["image"]

    if file.filename == "":
        return jsonify({"error": "Aucun fichier sélectionné"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Format non autorisé. Utilise PNG, JPG, JPEG ou WEBP."}), 400

    original_name = secure_filename(file.filename)
    extension = original_name.rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{extension}"
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    lat = request.form.get("lat") or request.form.get("latitude")
    lng = request.form.get("lng") or request.form.get("longitude")
    tags = request.form.get("tags", "")

    features = extract_features(filepath)
    prediction, confidence, reasons = classify_image(features)
    risk_score, risk_level, risk_explanation = calculate_risk_score(
        prediction=prediction,
        confidence=confidence,
        tags=tags,
        features=features,
    )

    report = ImageReport(
        stored_filename=filename,
        filepath=f"/uploads/{filename}",
        lat=float(lat) if lat else None,
        lng=float(lng) if lng else None,
        citizen_tags=tags,
        file_size_kb=features["file_size_kb"],
        width=features["width"],
        height=features["height"],
        avg_color_hex=features["avg_color_hex"],
        brightness=features["brightness"],
        contrast_level=features["contrast_level"],
        quality_score=features["quality_score"],
        quality_warning=features["quality_warning"],
        ai_prediction=prediction,
        ai_confidence=confidence,
        risk_score=risk_score,
        risk_level=risk_level,
        risk_explanation=f"{' | '.join(reasons)} | {risk_explanation}",
    )

    db.session.add(report)
    db.session.commit()

    return jsonify({"success": True, "report": report.to_dict()})


@app.route("/api/images", methods=["GET"])
def get_all_images():
    reports = ImageReport.query.order_by(ImageReport.timestamp.desc()).all()
    return jsonify([report.to_dict() for report in reports])

@app.route("/api/map-reports", methods=["GET"])
def get_map_reports():
    """Return geolocated reports for the Leaflet maps."""
    reports = (
        ImageReport.query.filter(ImageReport.lat.isnot(None), ImageReport.lng.isnot(None))
        .order_by(ImageReport.timestamp.desc())
        .all()
    )
    return jsonify([report.to_dict() for report in reports])


@app.route("/api/images/pending", methods=["GET"])
def get_pending_images():
    reports = (
        ImageReport.query.filter_by(status="Pending")
        .order_by(ImageReport.timestamp.desc())
        .all()
    )
    return jsonify([report.to_dict() for report in reports])


@app.route("/api/images/<int:report_id>", methods=["GET"])
def get_image(report_id):
    report = ImageReport.query.get_or_404(report_id)
    return jsonify(report.to_dict())


@app.route("/api/images/<int:report_id>/annotate", methods=["POST"])
def annotate_image(report_id):
    data = request.get_json(silent=True) or request.form
    annotation = data.get("annotation")

    report = ImageReport.query.get_or_404(report_id)

    if annotation in ["Pleine", "Vide", "Débordante"]:
        report.status = "Validated"
        report.agent_annotation = annotation
    elif annotation in ["Ignored", "Skip", "Passer"]:
        report.status = "Ignored"
        report.agent_annotation = None
    else:
        return jsonify({"error": "Annotation invalide"}), 400

    db.session.commit()
    return jsonify({"success": True, "report": report.to_dict()})


@app.route("/api/stats", methods=["GET"])
def get_stats():
    reports = ImageReport.query.all()
    total = len(reports)
    pending = sum(1 for report in reports if report.status == "Pending")
    validated = sum(1 for report in reports if report.status == "Validated")
    ignored = sum(1 for report in reports if report.status == "Ignored")
    full_count = sum(1 for report in reports if report.ai_prediction in ["Pleine", "Débordante"])
    empty_count = sum(1 for report in reports if report.ai_prediction == "Vide")
    high_risk = sum(1 for report in reports if report.risk_level == "Élevé")
    avg_risk = round(sum((report.risk_score or 0) for report in reports) / total, 1) if total else 0

    return jsonify(
        {
            "total": total,
            "pending": pending,
            "validated": validated,
            "ignored": ignored,
            "full_count": full_count,
            "empty_count": empty_count,
            "high_risk": high_risk,
            "avg_risk": avg_risk,
        }
    )


@app.errorhandler(413)
def file_too_large(error):
    return jsonify({"error": "Image trop lourde. Limite : 5 Mo."}), 413


if __name__ == "__main__":
    app.run(debug=True, port=5000)
