import csv
import io
import os
import uuid
from datetime import datetime, time
from functools import wraps
from pathlib import Path

from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    Response,
    session,
    url_for,
)
from werkzeug.utils import secure_filename
from sqlalchemy import and_, or_

from config import (
    ALLOWED_EXTENSIONS,
    DATA_DIR,
    DB_FOLDER,
    MAX_CONTENT_LENGTH,
    SECRET_KEY,
    SQLALCHEMY_DATABASE_URI,
    SQLALCHEMY_TRACK_MODIFICATIONS,
    UPLOAD_FOLDER,
)
from database import db
from image_processing import extract_features
from models import ImageReport
from risk_scoring import calculate_risk_score
from rule_engine import classify_image

USERS = {
    "agent": {"password": "agent123", "role": "agent", "label": "Agent territorial"},
    "admin": {"password": "admin123", "role": "admin", "label": "Administrateur"},
}


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = SECRET_KEY
    app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = SQLALCHEMY_TRACK_MODIFICATIONS
    app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)
    app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

    Path(DB_FOLDER).mkdir(parents=True, exist_ok=True)
    Path(UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)

    db.init_app(app)

    with app.app_context():
        db.create_all()

    return app


app = create_app()


def dev_bypass_enabled():
    return os.getenv("GREENBIN_DEV_BYPASS", "0") == "1"


def current_user():
    if dev_bypass_enabled():
        return {"username": "dev", "role": "admin", "label": "Mode développeur"}
    username = session.get("username")
    role = session.get("role")
    if not username or not role:
        return None
    return {"username": username, "role": role, "label": session.get("label", role)}


@app.context_processor
def inject_user():
    return {
        "current_user": current_user(),
        "dev_bypass": dev_bypass_enabled(),
    }


def login_required(roles=None):
    roles = roles or []

    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            user = current_user()
            if not user:
                return redirect(url_for("login", next=request.path))
            if roles and user["role"] not in roles:
                return redirect(url_for("citoyen_app"))
            return view_func(*args, **kwargs)

        return wrapped

    return decorator


def api_login_required(roles=None):
    roles = roles or []

    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            user = current_user()
            if not user:
                return jsonify({"error": "Authentification requise"}), 401
            if roles and user["role"] not in roles:
                return jsonify({"error": "Accès non autorisé"}), 403
            return view_func(*args, **kwargs)

        return wrapped

    return decorator


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None


def _normalise_risk(value):
    risk_map = {
        "faible": "Faible",
        "moyen": "Moyen",
        "eleve": "Élevé",
        "élevé": "Élevé",
        "elevé": "Élevé",
    }
    return risk_map.get((value or "").strip().lower())


def _apply_report_filters(query):
    """Apply dashboard/map filters without changing the database schema."""
    status = request.args.get("status", "").strip()
    label = request.args.get("label", "").strip()
    risk = _normalise_risk(request.args.get("risk", ""))
    date_from = _parse_date(request.args.get("date_from"))
    date_to = _parse_date(request.args.get("date_to"))
    zone = request.args.get("zone", "").strip()

    if status in {"Pending", "Validated", "Ignored"}:
        query = query.filter(ImageReport.status == status)

    if label in {"Vide", "Pleine"}:
        query = query.filter(
            or_(
                ImageReport.agent_annotation == label,
                and_(ImageReport.agent_annotation.is_(None), ImageReport.ai_prediction == label),
            )
        )

    if risk:
        query = query.filter(ImageReport.risk_level == risk)

    if date_from:
        query = query.filter(ImageReport.timestamp >= datetime.combine(date_from.date(), time.min))

    if date_to:
        query = query.filter(ImageReport.timestamp <= datetime.combine(date_to.date(), time.max))

    if zone:
        query = query.filter(ImageReport.citizen_tags.ilike(f"%{zone}%"))

    return query




def _normalise_label_value(value):
    label = (value or "").strip().lower()
    if label in {"vide", "empty", "clean"}:
        return "Vide"
    if label in {"pleine", "plein", "full", "dirty"}:
        return "Pleine"
    return None


def _final_label(report):
    return report.agent_annotation or report.ai_prediction


def _pct(part, total):
    return round((part / total) * 100, 1) if total else 0


def _compute_rule_metrics(pairs):
    """pairs = [(truth_label, predicted_label)]. Labels must be Vide/Pleine."""
    labels = ["Vide", "Pleine"]
    matrix = {truth: {pred: 0 for pred in labels} for truth in labels}
    valid_pairs = []

    for truth, pred in pairs:
        truth = _normalise_label_value(truth)
        pred = _normalise_label_value(pred)
        if truth in labels and pred in labels:
            matrix[truth][pred] += 1
            valid_pairs.append((truth, pred))

    total = len(valid_pairs)
    correct = sum(1 for truth, pred in valid_pairs if truth == pred)
    per_class = {}
    for label in labels:
        tp = matrix[label][label]
        fp = sum(matrix[truth][label] for truth in labels if truth != label)
        fn = sum(matrix[label][pred] for pred in labels if pred != label)
        per_class[label] = {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": _pct(tp, tp + fp),
            "recall": _pct(tp, tp + fn),
        }

    return {
        "total": total,
        "correct": correct,
        "accuracy": _pct(correct, total),
        "matrix": matrix,
        "per_class": per_class,
    }


def _db_evaluation_metrics():
    reports = ImageReport.query.filter(
        ImageReport.agent_annotation.in_(["Vide", "Pleine"]),
        ImageReport.ai_prediction.in_(["Vide", "Pleine"]),
    ).all()
    pairs = [(report.agent_annotation, report.ai_prediction) for report in reports]
    return _compute_rule_metrics(pairs)


def _read_csv_rows(path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as csvfile:
        return list(csv.DictReader(csvfile))


def _dataset_csv_summary(path):
    rows = _read_csv_rows(path)
    labels = {}
    splits = {}
    for row in rows:
        label = row.get("manual_label") or row.get("label") or "non_renseigne"
        split = row.get("split") or "non_renseigne"
        labels[label] = labels.get(label, 0) + 1
        splits[split] = splits.get(split, 0) + 1
    return {
        "exists": path.exists(),
        "path": str(path).replace("\\", "/"),
        "count": len(rows),
        "labels": labels,
        "splits": splits,
        "columns": list(rows[0].keys()) if rows else [],
    }


def _dataset_evaluation_metrics():
    enriched_path = Path(DATA_DIR) / "annotations_enriched.csv"
    rows = _read_csv_rows(enriched_path)
    pairs = [(row.get("manual_label"), row.get("auto_label")) for row in rows]
    metrics = _compute_rule_metrics(pairs)
    metrics["source_path"] = str(enriched_path).replace("\\", "/")
    metrics["source_exists"] = enriched_path.exists()
    return metrics


def _dataset_page_stats():
    annotations_path = Path(DATA_DIR) / "annotations.csv"
    enriched_path = Path(DATA_DIR) / "annotations_enriched.csv"
    db_total = ImageReport.query.count()
    return {
        "annotations": _dataset_csv_summary(annotations_path),
        "enriched": _dataset_csv_summary(enriched_path),
        "db_total": db_total,
        "db_pending": ImageReport.query.filter_by(status="Pending").count(),
        "db_validated": ImageReport.query.filter_by(status="Validated").count(),
    }

@app.route("/")
def home():
    return redirect(url_for("citoyen_app"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    next_url = request.args.get("next") or url_for("citoyen_app")

    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        user = USERS.get(username)

        if user and user["password"] == password:
            session["username"] = username
            session["role"] = user["role"]
            session["label"] = user["label"]

            if user["role"] == "admin":
                return redirect(request.form.get("next") or url_for("dashboard_app"))
            return redirect(request.form.get("next") or url_for("agent_app"))

        error = "Identifiants incorrects."

    return render_template("login.html", active="login", error=error, next_url=next_url)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("citoyen_app"))


@app.route("/citoyen")
def citoyen_app():
    return render_template("citoyen.html", active="citoyen")


@app.route("/agent")
@login_required(["agent", "admin"])
def agent_app():
    return render_template("agent.html", active="agent")


@app.route("/dashboard")
@login_required(["admin"])
def dashboard_app():
    return render_template("dashboard.html", active="dashboard")




@app.route("/dataset")
@login_required(["admin"])
def dataset_app():
    return render_template(
        "dataset.html",
        active="dataset",
        stats=_dataset_page_stats(),
    )


@app.route("/evaluation")
@login_required(["admin"])
def evaluation_app():
    return render_template(
        "evaluation.html",
        active="evaluation",
        db_eval=_db_evaluation_metrics(),
        dataset_eval=_dataset_evaluation_metrics(),
    )


@app.route("/exports/reports.csv", methods=["GET"])
@login_required(["admin"])
def export_reports_csv():
    reports = _apply_report_filters(ImageReport.query).order_by(ImageReport.timestamp.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow([
        "id",
        "timestamp",
        "status",
        "agent_annotation",
        "ai_prediction",
        "ai_confidence",
        "risk_score",
        "risk_level",
        "lat",
        "lng",
        "citizen_tags",
        "stored_filename",
        "image_url",
        "file_size_kb",
        "width",
        "height",
        "brightness",
        "contrast_level",
        "quality_score",
        "quality_warning",
    ])
    for report in reports:
        writer.writerow([
            report.id,
            report.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            report.status,
            report.agent_annotation or "",
            report.ai_prediction or "",
            report.ai_confidence if report.ai_confidence is not None else "",
            report.risk_score if report.risk_score is not None else "",
            report.risk_level or "",
            report.lat if report.lat is not None else "",
            report.lng if report.lng is not None else "",
            report.citizen_tags or "",
            report.stored_filename,
            f"/uploads/{report.stored_filename}",
            report.file_size_kb if report.file_size_kb is not None else "",
            report.width if report.width is not None else "",
            report.height if report.height is not None else "",
            report.brightness if report.brightness is not None else "",
            report.contrast_level if report.contrast_level is not None else "",
            report.quality_score if report.quality_score is not None else "",
            report.quality_warning or "",
        ])

    filename = f"greenbin_signalements_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )

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

    # Server-side quality gate: block images that cannot be exploited.
    # Warnings such as slightly dark or slightly blurry are still accepted and shown to the user.
    blocking_reasons = []
    if (features.get("width") or 0) < 250 or (features.get("height") or 0) < 250:
        blocking_reasons.append("image trop petite")
    if (features.get("quality_score") or 0) < 35:
        blocking_reasons.append("qualité image trop faible")

    if blocking_reasons:
        try:
            os.remove(filepath)
        except OSError:
            pass
        return jsonify({
            "error": "Image refusée : " + ", ".join(blocking_reasons) + ".",
            "quality": features,
        }), 400

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
        status="Pending",
    )

    db.session.add(report)
    db.session.commit()

    return jsonify({"success": True, "report": report.to_dict()})


@app.route("/api/images", methods=["GET"])
@api_login_required(["admin"])
def get_all_images():
    try:
        limit = min(int(request.args.get("limit", 100)), 500)
    except ValueError:
        limit = 100

    query = _apply_report_filters(ImageReport.query)
    reports = query.order_by(ImageReport.timestamp.desc()).limit(limit).all()
    return jsonify([report.to_dict() for report in reports])


@app.route("/api/map-reports", methods=["GET"])
@api_login_required(["admin"])
def get_map_reports():
    try:
        limit = min(int(request.args.get("limit", 250)), 500)
    except ValueError:
        limit = 250

    query = _apply_report_filters(
        ImageReport.query.filter(ImageReport.lat.isnot(None), ImageReport.lng.isnot(None))
    )
    reports = query.order_by(ImageReport.timestamp.desc()).limit(limit).all()
    return jsonify([report.to_dict() for report in reports])


@app.route("/api/images/pending", methods=["GET"])
@api_login_required(["agent", "admin"])
def get_pending_images():
    reports = (
        ImageReport.query.filter_by(status="Pending")
        .order_by(ImageReport.timestamp.desc())
        .all()
    )
    return jsonify([report.to_dict() for report in reports])


@app.route("/api/images/<int:report_id>", methods=["GET"])
@api_login_required(["agent", "admin"])
def get_image(report_id):
    report = ImageReport.query.get_or_404(report_id)
    return jsonify(report.to_dict())


@app.route("/api/images/<int:report_id>/annotate", methods=["POST", "PATCH"])
@api_login_required(["agent", "admin"])
def annotate_image(report_id):
    data = request.get_json(silent=True) or request.form
    annotation = data.get("annotation")

    report = ImageReport.query.get_or_404(report_id)

    if annotation in ["Pleine", "Vide"]:
        report.status = "Validated"
        report.agent_annotation = annotation
    elif annotation in ["Ignored", "Skip", "Passer"]:
        report.status = "Ignored"
        report.agent_annotation = None
    else:
        return jsonify({"error": "Annotation invalide"}), 400

    db.session.commit()
    return jsonify({"success": True, "report": report.to_dict()})


@app.route("/api/images/<int:report_id>/reset-annotation", methods=["POST"])
@api_login_required(["agent", "admin"])
def reset_annotation(report_id):
    report = ImageReport.query.get_or_404(report_id)
    report.status = "Pending"
    report.agent_annotation = None
    db.session.commit()
    return jsonify({"success": True, "report": report.to_dict()})


@app.route("/api/images/recent-annotations", methods=["GET"])
@api_login_required(["agent", "admin"])
def recent_annotations():
    try:
        limit = min(int(request.args.get("limit", 8)), 30)
    except ValueError:
        limit = 8

    reports = (
        ImageReport.query.filter(ImageReport.status.in_(["Validated", "Ignored"]))
        .order_by(ImageReport.id.desc())
        .limit(limit)
        .all()
    )
    return jsonify([report.to_dict() for report in reports])


@app.route("/api/stats", methods=["GET"])
@api_login_required(["admin"])
def get_stats():
    reports = _apply_report_filters(ImageReport.query).all()
    total = len(reports)
    pending = sum(1 for report in reports if report.status == "Pending")
    validated = sum(1 for report in reports if report.status == "Validated")
    ignored = sum(1 for report in reports if report.status == "Ignored")
    full_count = sum(1 for report in reports if report.ai_prediction == "Pleine" or report.agent_annotation == "Pleine")
    empty_count = sum(1 for report in reports if report.ai_prediction == "Vide" or report.agent_annotation == "Vide")
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
