import csv
import io
import os
import math
import uuid
from collections import defaultdict
from datetime import datetime, time, timedelta
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
from models import AgentActivity, AppSetting, BinLocation, ImageReport
from risk_scoring import calculate_risk_score
from rule_engine import classify_image

USERS = {
    "agent": {"password": "agent123", "role": "agent", "label": "Agent territorial"},
    "admin": {"password": "admin123", "role": "admin", "label": "Administrateur"},
}

DEFAULT_SETTINGS = {
    "min_quality_score": {
        "value": "35",
        "label": "Qualité minimale image",
        "description": "Score minimal accepté à l'upload. En dessous, l'image est refusée.",
        "category": "Qualité des données",
    },
    "min_width": {
        "value": "250",
        "label": "Largeur minimale",
        "description": "Largeur minimale en pixels pour éviter les images inexploitablement petites.",
        "category": "Qualité des données",
    },
    "min_height": {
        "value": "250",
        "label": "Hauteur minimale",
        "description": "Hauteur minimale en pixels pour éviter les images inexploitablement petites.",
        "category": "Qualité des données",
    },
    "brightness_threshold": {
        "value": "105",
        "label": "Seuil luminosité règle",
        "description": "Une image sous ce seuil ajoute un signal de poubelle potentiellement pleine.",
        "category": "Règles de classification",
    },
    "contrast_threshold": {
        "value": "50",
        "label": "Seuil contraste règle",
        "description": "Une image au-dessus de ce seuil ajoute un signal de poubelle potentiellement pleine.",
        "category": "Règles de classification",
    },
    "file_size_threshold_kb": {
        "value": "200",
        "label": "Seuil taille fichier",
        "description": "Taille en Ko au-dessus de laquelle la règle ajoute un signal visuel.",
        "category": "Règles de classification",
    },
    "decision_threshold": {
        "value": "50",
        "label": "Seuil décision pleine",
        "description": "Score interne minimal pour classer automatiquement une image comme pleine.",
        "category": "Règles de classification",
    },
    "risk_medium_threshold": {
        "value": "30",
        "label": "Seuil risque moyen",
        "description": "Score à partir duquel un signalement passe en risque moyen.",
        "category": "Scoring et priorisation",
    },
    "risk_high_threshold": {
        "value": "70",
        "label": "Seuil risque élevé",
        "description": "Score à partir duquel un signalement devient prioritaire.",
        "category": "Scoring et priorisation",
    },
    "map_max_points": {
        "value": "250",
        "label": "Nombre max de points carte",
        "description": "Limite de points renvoyés à la carte pour préserver les performances.",
        "category": "Performance carte",
    },
    "recurring_zone_min_count": {
        "value": "3",
        "label": "Seuil zone récurrente",
        "description": "Nombre de signalements nécessaires pour remonter une zone récurrente.",
        "category": "Alertes agent",
    },
    "recurring_zone_precision": {
        "value": "3",
        "label": "Précision regroupement zone",
        "description": "Nombre de décimales utilisées pour regrouper les signalements proches.",
        "category": "Alertes agent",
    },
    "nearest_bin_max_meters": {
        "value": "35",
        "label": "Distance max poubelle officielle",
        "description": "Distance maximale pour rattacher un signalement à une poubelle prédéfinie. Au-delà, il est considéré comme dépôt sauvage ou hors emplacement.",
        "category": "Poubelles prédéfinies",
    },
    "route_start_lat": {
        "value": "48.8566",
        "label": "Latitude départ tournée",
        "description": "Point de départ utilisé pour proposer une tournée optimisée.",
        "category": "Parcours de collecte",
    },
    "route_start_lng": {
        "value": "2.3522",
        "label": "Longitude départ tournée",
        "description": "Point de départ utilisé pour proposer une tournée optimisée.",
        "category": "Parcours de collecte",
    },
}


def seed_default_settings():
    for key, payload in DEFAULT_SETTINGS.items():
        existing = AppSetting.query.get(key)
        if existing is None:
            db.session.add(
                AppSetting(
                    key=key,
                    value=str(payload["value"]),
                    label=payload["label"],
                    description=payload["description"],
                    category=payload["category"],
                )
            )
    db.session.commit()



DEFAULT_BIN_LOCATIONS = [
    {"name": "Poubelle Parc République", "lat": 48.78975, "lng": 2.36926, "zone": "Parc République", "bin_type": "classique", "capacity_l": 120},
    {"name": "Poubelle Avenue Louis Aragon", "lat": 48.78820, "lng": 2.37420, "zone": "Avenue Louis Aragon", "bin_type": "classique", "capacity_l": 120},
    {"name": "Poubelle Square Sud", "lat": 48.79115, "lng": 2.36605, "zone": "Square Sud", "bin_type": "recyclage", "capacity_l": 90},
    {"name": "Poubelle École Centre", "lat": 48.79245, "lng": 2.37125, "zone": "École Centre", "bin_type": "classique", "capacity_l": 120},
    {"name": "Poubelle Marché Nord", "lat": 48.79510, "lng": 2.36575, "zone": "Marché Nord", "bin_type": "classique", "capacity_l": 240},
    {"name": "Poubelle Canal", "lat": 48.78695, "lng": 2.37790, "zone": "Canal", "bin_type": "verre", "capacity_l": 180},
]


def seed_default_bin_locations():
    if BinLocation.query.count():
        return
    for item in DEFAULT_BIN_LOCATIONS:
        db.session.add(BinLocation(**item))
    db.session.commit()


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
        seed_default_settings()
        seed_default_bin_locations()

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


def safe_float(value, default=None):
    if value in (None, ""):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


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
        "critique": "Critique",
    }
    return risk_map.get((value or "").strip().lower())


def get_setting(key, default=None):
    setting = AppSetting.query.get(key)
    if setting is not None:
        return setting.value
    payload = DEFAULT_SETTINGS.get(key)
    if payload:
        return payload["value"]
    return default


def get_int_setting(key, default=0):
    try:
        return int(float(get_setting(key, default)))
    except (TypeError, ValueError):
        return default


def all_settings_grouped():
    settings = {setting.key: setting for setting in AppSetting.query.order_by(AppSetting.category, AppSetting.label).all()}
    for key, payload in DEFAULT_SETTINGS.items():
        settings.setdefault(
            key,
            AppSetting(
                key=key,
                value=str(payload["value"]),
                label=payload["label"],
                description=payload["description"],
                category=payload["category"],
            ),
        )
    grouped = defaultdict(list)
    for setting in sorted(settings.values(), key=lambda s: (s.category, s.label)):
        grouped[setting.category].append(setting)
    return dict(grouped)


def _classification_thresholds():
    return {
        "contrast_threshold": get_int_setting("contrast_threshold", 50),
        "brightness_threshold": get_int_setting("brightness_threshold", 105),
        "file_size_threshold_kb": get_int_setting("file_size_threshold_kb", 200),
        "quality_warning_threshold": 60,
        "decision_threshold": get_int_setting("decision_threshold", 50),
    }


def _risk_thresholds():
    return {
        "risk_medium_threshold": get_int_setting("risk_medium_threshold", 30),
        "risk_high_threshold": get_int_setting("risk_high_threshold", 70),
    }



def _haversine_m(lat1, lng1, lat2, lng2):
    if None in (lat1, lng1, lat2, lng2):
        return None
    radius = 6371000
    phi1, phi2 = math.radians(float(lat1)), math.radians(float(lat2))
    d_phi = math.radians(float(lat2) - float(lat1))
    d_lambda = math.radians(float(lng2) - float(lng1))
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * radius * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _nearest_bin_location(lat, lng):
    if lat is None or lng is None:
        return None, None
    bins = BinLocation.query.filter_by(is_active=True).all()
    best = None
    best_distance = None
    for bin_location in bins:
        distance = _haversine_m(lat, lng, bin_location.lat, bin_location.lng)
        if distance is None:
            continue
        if best_distance is None or distance < best_distance:
            best = bin_location
            best_distance = distance
    return best, best_distance


def _is_full_report(report):
    return (report.agent_annotation or report.ai_prediction) == "Pleine"


def _is_actionable_report(report):
    return (
        report.status not in {"Collected", "Ignored"}
        and report.lat is not None
        and report.lng is not None
        and (_is_full_report(report) or (report.risk_level in {"Élevé", "Critique"}))
    )


def _apply_location_context(report):
    max_distance = get_int_setting("nearest_bin_max_meters", 35)
    nearest, distance = _nearest_bin_location(report.lat, report.lng)

    if nearest and distance is not None and distance <= max_distance:
        report.bin_location_id = nearest.id
        report.location_type = "official_bin"
        if report.risk_level == "Élevé":
            report.priority_level = "Haute"
        elif _is_full_report(report):
            report.priority_level = "Moyenne"
        else:
            report.priority_level = "Normale"
        return

    report.bin_location_id = None
    report.location_type = "wild_dump"
    # A report far from any official bin is operationally more urgent.
    report.risk_score = min(100, int(report.risk_score or 0) + 25)
    if report.risk_score >= 90:
        report.risk_level = "Critique"
        report.priority_level = "Critique"
    elif report.risk_score >= get_int_setting("risk_high_threshold", 70):
        report.risk_level = "Élevé"
        report.priority_level = "Haute"
    else:
        report.priority_level = "Moyenne"
    addition = "hors emplacement officiel: +25"
    report.risk_explanation = f"{report.risk_explanation} | {addition}" if report.risk_explanation else addition


def _route_candidates():
    reports = (
        ImageReport.query
        .filter(ImageReport.lat.isnot(None), ImageReport.lng.isnot(None))
        .order_by(ImageReport.risk_score.desc(), ImageReport.timestamp.desc())
        .all()
    )
    return [report for report in reports if _is_actionable_report(report)]


def _nearest_neighbor_route(start_lat, start_lng, reports):
    remaining = list(reports)
    current_lat, current_lng = start_lat, start_lng
    ordered = []
    total_m = 0

    while remaining:
        def route_weight(report):
            distance = _haversine_m(current_lat, current_lng, report.lat, report.lng) or 0
            # Keep the route geographic but slightly favor critical points.
            priority_bonus = {"Critique": 250, "Haute": 120, "Moyenne": 40}.get(report.priority_level, 0)
            return max(distance - priority_bonus, 0)

        next_report = min(remaining, key=route_weight)
        distance = _haversine_m(current_lat, current_lng, next_report.lat, next_report.lng) or 0
        total_m += distance
        payload = next_report.to_dict()
        payload["distance_from_previous_m"] = round(distance)
        ordered.append(payload)
        current_lat, current_lng = next_report.lat, next_report.lng
        remaining.remove(next_report)

    return ordered, round(total_m)



def _apply_report_filters(query):
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


def _pct(part, total):
    return round((part / total) * 100, 1) if total else 0


def _compute_rule_metrics(pairs):
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


def _report_duplicate_key(report):
    if not report.file_size_kb or not report.width or not report.height:
        return None
    lat = round(report.lat or 0, 3) if report.lat is not None else None
    lng = round(report.lng or 0, 3) if report.lng is not None else None
    return (report.file_size_kb, report.width, report.height, report.avg_color_hex, lat, lng)


def _duplicate_keys(reports):
    counts = defaultdict(int)
    for report in reports:
        key = _report_duplicate_key(report)
        if key:
            counts[key] += 1
    return {key for key, count in counts.items() if count > 1}


def _conformity_issues(report, duplicate_keys=None):
    issues = []
    duplicate_keys = duplicate_keys or set()
    min_quality = get_int_setting("min_quality_score", 35)
    min_width = get_int_setting("min_width", 250)
    min_height = get_int_setting("min_height", 250)

    if report.lat is None or report.lng is None:
        issues.append({"type": "missing_gps", "severity": "high", "label": "GPS manquant"})

    if (report.width or 0) < min_width or (report.height or 0) < min_height:
        issues.append({"type": "invalid_image", "severity": "high", "label": "Image trop petite"})

    if (report.quality_score if report.quality_score is not None else 100) < min_quality:
        issues.append({"type": "low_quality", "severity": "medium", "label": "Qualité image faible"})

    if report.status == "Pending" or not report.agent_annotation:
        issues.append({"type": "missing_annotation", "severity": "medium", "label": "Annotation agent manquante"})

    if report.location_type == "wild_dump":
        issues.append({"type": "wild_dump", "severity": "high", "label": "Dépôt sauvage / hors emplacement"})

    upload_path = Path(UPLOAD_FOLDER) / report.stored_filename
    if report.stored_filename and not upload_path.exists():
        issues.append({"type": "missing_file", "severity": "high", "label": "Fichier image introuvable"})

    if _report_duplicate_key(report) in duplicate_keys:
        issues.append({"type": "possible_duplicate", "severity": "medium", "label": "Doublon possible"})

    return issues


def _conformity_overview(limit=80):
    all_reports = ImageReport.query.order_by(ImageReport.timestamp.desc()).all()
    dupes = _duplicate_keys(all_reports)
    rows = []
    counts = defaultdict(int)
    compliant_count = 0

    for report in all_reports[:limit]:
        issues = _conformity_issues(report, dupes)
        if not issues:
            compliant_count += 1
        for issue in issues:
            counts[issue["type"]] += 1
        payload = report.to_dict()
        payload["issues"] = issues
        payload["is_compliant"] = not issues
        rows.append(payload)

    total = len(all_reports)
    non_compliant_total = 0
    for report in all_reports:
        if _conformity_issues(report, dupes):
            non_compliant_total += 1

    return {
        "total": total,
        "compliant": total - non_compliant_total,
        "non_compliant": non_compliant_total,
        "counts": dict(counts),
        "reports": rows,
    }


def _zone_key(report):
    if report.lat is None or report.lng is None:
        return None
    precision = max(2, min(get_int_setting("recurring_zone_precision", 3), 5))
    return (round(report.lat, precision), round(report.lng, precision))


def _recurring_zones(reports):
    groups = defaultdict(list)
    for report in reports:
        key = _zone_key(report)
        if key is not None:
            groups[key].append(report)

    min_count = get_int_setting("recurring_zone_min_count", 3)
    zones = []
    for (lat, lng), items in groups.items():
        if len(items) < min_count:
            continue
        avg_risk = round(sum((item.risk_score or 0) for item in items) / len(items), 1)
        full_count = sum(1 for item in items if (item.agent_annotation or item.ai_prediction) == "Pleine")
        zones.append({
            "lat": lat,
            "lng": lng,
            "count": len(items),
            "full_count": full_count,
            "avg_risk": avg_risk,
            "last_report": max(item.timestamp for item in items).strftime("%Y-%m-%d %H:%M:%S"),
            "report_ids": [item.id for item in items[:8]],
        })
    zones.sort(key=lambda item: (item["avg_risk"], item["count"]), reverse=True)
    return zones[:8]


def _agent_priorities_payload():
    high_threshold = get_int_setting("risk_high_threshold", 70)
    since = datetime.utcnow() - timedelta(days=7)
    pending_query = ImageReport.query.filter_by(status="Pending")
    high_risk_pending = (
        pending_query.filter(ImageReport.risk_score >= high_threshold)
        .order_by(ImageReport.risk_score.desc(), ImageReport.timestamp.desc())
        .limit(8)
        .all()
    )

    recent_reports = ImageReport.query.filter(ImageReport.timestamp >= since).all()
    duplicate_keys = _duplicate_keys(recent_reports)
    conformity_alerts = []
    for report in pending_query.order_by(ImageReport.timestamp.desc()).limit(30).all():
        issues = _conformity_issues(report, duplicate_keys)
        serious_issues = [issue for issue in issues if issue["type"] in {"missing_gps", "invalid_image", "low_quality", "possible_duplicate"}]
        if serious_issues:
            payload = report.to_dict()
            payload["issues"] = serious_issues
            conformity_alerts.append(payload)

    return {
        "high_risk_pending": [report.to_dict() for report in high_risk_pending],
        "recurring_zones": _recurring_zones(recent_reports),
        "conformity_alerts": conformity_alerts[:8],
    }


def _log_activity(report, action, old_status=None, old_annotation=None, new_status=None, new_annotation=None, comment=None):
    user = current_user() or {"username": "anonymous", "role": "public"}
    db.session.add(
        AgentActivity(
            username=user["username"],
            role=user["role"],
            action=action,
            report_id=report.id,
            old_status=old_status,
            new_status=new_status,
            old_annotation=old_annotation,
            new_annotation=new_annotation,
            comment=comment,
        )
    )


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


@app.route("/route-planning")
@login_required(["agent", "admin"])
def route_planning_app():
    return render_template("route_planning.html", active="route")


@app.route("/bin-locations")
@login_required(["admin"])
def bin_locations_app():
    return render_template("bin_locations.html", active="bins")


@app.route("/dataset")
@login_required(["admin"])
def dataset_app():
    return render_template("dataset.html", active="dataset", stats=_dataset_page_stats())


@app.route("/evaluation")
@login_required(["admin"])
def evaluation_app():
    return render_template(
        "evaluation.html",
        active="evaluation",
        db_eval=_db_evaluation_metrics(),
        dataset_eval=_dataset_evaluation_metrics(),
    )


@app.route("/conformity")
@login_required(["admin"])
def conformity_app():
    return render_template("conformity.html", active="conformity", overview=_conformity_overview())


@app.route("/admin/settings", methods=["GET", "POST"])
@login_required(["admin"])
def admin_settings_app():
    saved = request.args.get("saved") == "1"
    if request.method == "POST":
        for key, payload in DEFAULT_SETTINGS.items():
            value = request.form.get(key)
            if value is None:
                continue
            setting = AppSetting.query.get(key)
            if setting is None:
                setting = AppSetting(
                    key=key,
                    value=str(value),
                    label=payload["label"],
                    description=payload["description"],
                    category=payload["category"],
                )
                db.session.add(setting)
            else:
                setting.value = str(value).strip()
                setting.label = payload["label"]
                setting.description = payload["description"]
                setting.category = payload["category"]
        db.session.commit()
        return redirect(url_for("admin_settings_app", saved=1))
    return render_template("settings.html", active="settings", grouped_settings=all_settings_grouped(), saved=saved)


@app.route("/exports/reports.csv", methods=["GET"])
@login_required(["admin"])
def export_reports_csv():
    reports = _apply_report_filters(ImageReport.query).order_by(ImageReport.timestamp.desc()).all()
    all_reports = ImageReport.query.all()
    duplicate_keys = _duplicate_keys(all_reports)
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow([
        "id", "timestamp", "status", "agent_annotation", "ai_prediction", "ai_confidence",
        "risk_score", "risk_level", "priority_level", "location_type", "bin_location_name", "collected_at",
        "lat", "lng", "citizen_tags", "stored_filename", "image_url",
        "file_size_kb", "width", "height", "brightness", "contrast_level", "quality_score",
        "quality_warning", "conformity_issues",
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
            report.priority_level or "",
            report.location_type or "",
            report.bin_location.name if report.bin_location else "",
            report.collected_at.strftime("%Y-%m-%d %H:%M:%S") if report.collected_at else "",
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
            " | ".join(issue["label"] for issue in _conformity_issues(report, duplicate_keys)),
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

    lat = safe_float(request.form.get("lat") or request.form.get("latitude"))
    lng = safe_float(request.form.get("lng") or request.form.get("longitude"))
    tags = request.form.get("tags", "")

    features = extract_features(filepath)

    blocking_reasons = []
    min_width = get_int_setting("min_width", 250)
    min_height = get_int_setting("min_height", 250)
    min_quality = get_int_setting("min_quality_score", 35)
    if (features.get("width") or 0) < min_width or (features.get("height") or 0) < min_height:
        blocking_reasons.append("image trop petite")
    if (features.get("quality_score") or 0) < min_quality:
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

    prediction, confidence, reasons = classify_image(features, _classification_thresholds())
    risk_score, risk_level, risk_explanation = calculate_risk_score(
        prediction=prediction,
        confidence=confidence,
        tags=tags,
        features=features,
        thresholds=_risk_thresholds(),
    )

    report = ImageReport(
        stored_filename=filename,
        filepath=f"/uploads/{filename}",
        lat=lat,
        lng=lng,
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

    _apply_location_context(report)

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
    default_limit = get_int_setting("map_max_points", 250)
    try:
        limit = min(int(request.args.get("limit", default_limit)), 500)
    except ValueError:
        limit = default_limit

    query = _apply_report_filters(
        ImageReport.query.filter(ImageReport.lat.isnot(None), ImageReport.lng.isnot(None))
    )
    reports = query.order_by(ImageReport.timestamp.desc()).limit(limit).all()

    # By default, the operational map only shows full/actionable bins.
    if request.args.get("show_all") not in {"1", "true", "True", "yes"}:
        reports = [report for report in reports if _is_actionable_report(report)]

    return jsonify([report.to_dict() for report in reports])


@app.route("/api/heatmap-reports", methods=["GET"])
@api_login_required(["admin"])
def get_heatmap_reports():
    high_threshold = get_int_setting("risk_high_threshold", 70)
    default_limit = get_int_setting("map_max_points", 250)
    try:
        limit = min(int(request.args.get("limit", default_limit)), 500)
    except ValueError:
        limit = default_limit

    query = _apply_report_filters(
        ImageReport.query.filter(ImageReport.lat.isnot(None), ImageReport.lng.isnot(None))
    )
    reports = query.order_by(ImageReport.timestamp.desc()).limit(limit).all()
    points = []
    for report in reports:
        intensity = max(0.15, min((report.risk_score or 0) / max(high_threshold, 1), 1.0))
        points.append({
            "lat": report.lat,
            "lng": report.lng,
            "intensity": intensity,
            "risk_score": report.risk_score or 0,
            "risk_level": report.risk_level or "",
        })
    return jsonify(points)


@app.route("/api/images/pending", methods=["GET"])
@api_login_required(["agent", "admin"])
def get_pending_images():
    high_threshold = get_int_setting("risk_high_threshold", 70)
    reports = (
        ImageReport.query.filter_by(status="Pending")
        .order_by(ImageReport.risk_score.desc(), ImageReport.timestamp.desc())
        .all()
    )
    payload = []
    for report in reports:
        item = report.to_dict()
        item["is_priority"] = (report.risk_score or 0) >= high_threshold
        payload.append(item)
    return jsonify(payload)


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
    old_status = report.status
    old_annotation = report.agent_annotation

    if annotation in ["Pleine", "Vide"]:
        report.status = "Validated"
        report.agent_annotation = annotation
        action = "correct" if old_annotation and old_annotation != annotation else "validate"
    elif annotation in ["Ignored", "Skip", "Passer"]:
        report.status = "Ignored"
        report.agent_annotation = None
        action = "ignore"
    else:
        return jsonify({"error": "Annotation invalide"}), 400

    _apply_location_context(report)

    _log_activity(
        report,
        action=action,
        old_status=old_status,
        old_annotation=old_annotation,
        new_status=report.status,
        new_annotation=report.agent_annotation,
    )
    db.session.commit()
    return jsonify({"success": True, "report": report.to_dict()})


@app.route("/api/images/<int:report_id>/reset-annotation", methods=["POST"])
@api_login_required(["agent", "admin"])
def reset_annotation(report_id):
    report = ImageReport.query.get_or_404(report_id)
    old_status = report.status
    old_annotation = report.agent_annotation
    report.status = "Pending"
    report.agent_annotation = None
    _log_activity(
        report,
        action="reset",
        old_status=old_status,
        old_annotation=old_annotation,
        new_status=report.status,
        new_annotation=None,
    )
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


@app.route("/api/activity/recent", methods=["GET"])
@api_login_required(["agent", "admin"])
def recent_activity():
    try:
        limit = min(int(request.args.get("limit", 10)), 50)
    except ValueError:
        limit = 10
    activities = AgentActivity.query.order_by(AgentActivity.timestamp.desc()).limit(limit).all()
    return jsonify([activity.to_dict() for activity in activities])


@app.route("/api/agent-priorities", methods=["GET"])
@api_login_required(["agent", "admin"])
def agent_priorities():
    return jsonify(_agent_priorities_payload())


@app.route("/api/conformity", methods=["GET"])
@api_login_required(["admin"])
def conformity_api():
    try:
        limit = min(int(request.args.get("limit", 80)), 300)
    except ValueError:
        limit = 80
    return jsonify(_conformity_overview(limit=limit))



@app.route("/api/bin-locations", methods=["GET", "POST"])
def bin_locations_api():
    if request.method == "POST":
        user = current_user()
        if not user or user["role"] != "admin":
            return jsonify({"error": "Seul un administrateur peut ajouter un emplacement officiel."}), 403
        data = request.get_json(silent=True) or request.form
        lat = safe_float(data.get("lat"))
        lng = safe_float(data.get("lng"))
        name = (data.get("name") or "").strip()
        if not name or lat is None or lng is None:
            return jsonify({"error": "Nom, latitude et longitude sont obligatoires."}), 400

        bin_location = BinLocation(
            name=name,
            lat=lat,
            lng=lng,
            zone=(data.get("zone") or "").strip(),
            bin_type=(data.get("bin_type") or "classique").strip(),
            capacity_l=int(data.get("capacity_l") or 0) or None,
            is_active=True,
        )
        db.session.add(bin_location)
        db.session.commit()
        return jsonify({"success": True, "bin_location": bin_location.to_dict(include_stats=True)}), 201

    bins = BinLocation.query.order_by(BinLocation.name.asc()).all()
    return jsonify([bin_location.to_dict(include_stats=True) for bin_location in bins])


@app.route("/api/bin-locations/<int:bin_id>/history", methods=["GET"])
@api_login_required(["agent", "admin"])
def bin_location_history_api(bin_id):
    bin_location = BinLocation.query.get_or_404(bin_id)
    reports = (
        ImageReport.query.filter_by(bin_location_id=bin_id)
        .order_by(ImageReport.timestamp.desc())
        .limit(50)
        .all()
    )
    return jsonify({
        "bin_location": bin_location.to_dict(include_stats=True),
        "reports": [report.to_dict() for report in reports],
    })


@app.route("/api/route-plan", methods=["GET"])
@api_login_required(["agent", "admin"])
def route_plan_api():
    start_lat = safe_float(request.args.get("start_lat"), safe_float(get_setting("route_start_lat", "48.8566")))
    start_lng = safe_float(request.args.get("start_lng"), safe_float(get_setting("route_start_lng", "2.3522")))
    try:
        limit = min(int(request.args.get("limit", 20)), 60)
    except ValueError:
        limit = 20

    candidates = _route_candidates()[:limit]
    ordered, total_m = _nearest_neighbor_route(start_lat, start_lng, candidates)
    return jsonify({
        "start": {"lat": start_lat, "lng": start_lng, "label": "Départ tournée"},
        "total_distance_m": total_m,
        "total_distance_km": round(total_m / 1000, 2),
        "stop_count": len(ordered),
        "stops": ordered,
    })


@app.route("/api/images/<int:report_id>/collect", methods=["POST"])
@api_login_required(["agent", "admin"])
def collect_report_api(report_id):
    report = ImageReport.query.get_or_404(report_id)
    old_status = report.status
    old_annotation = report.agent_annotation
    report.status = "Collected"
    report.collected_at = datetime.utcnow()
    if not report.agent_annotation and report.ai_prediction in ["Pleine", "Vide"]:
        report.agent_annotation = report.ai_prediction
    report.priority_level = "Traitée"
    _log_activity(
        report,
        action="collect",
        old_status=old_status,
        old_annotation=old_annotation,
        new_status=report.status,
        new_annotation=report.agent_annotation,
        comment="Signalement marqué comme collecté",
    )
    db.session.commit()
    return jsonify({"success": True, "report": report.to_dict()})


@app.route("/api/settings", methods=["GET"])
@api_login_required(["admin"])
def settings_api():
    return jsonify({setting.key: setting.to_dict() for group in all_settings_grouped().values() for setting in group})


@app.route("/api/stats", methods=["GET"])
@api_login_required(["admin"])
def get_stats():
    reports = _apply_report_filters(ImageReport.query).all()
    total = len(reports)
    pending = sum(1 for report in reports if report.status == "Pending")
    validated = sum(1 for report in reports if report.status == "Validated")
    ignored = sum(1 for report in reports if report.status == "Ignored")
    collected = sum(1 for report in reports if report.status == "Collected")
    full_count = sum(1 for report in reports if (report.agent_annotation or report.ai_prediction) == "Pleine")
    empty_count = sum(1 for report in reports if (report.agent_annotation or report.ai_prediction) == "Vide")
    high_threshold = get_int_setting("risk_high_threshold", 70)
    high_risk = sum(1 for report in reports if (report.risk_score or 0) >= high_threshold)
    avg_risk = round(sum((report.risk_score or 0) for report in reports) / total, 1) if total else 0

    return jsonify(
        {
            "total": total,
            "pending": pending,
            "validated": validated,
            "ignored": ignored,
            "collected": collected,
            "full_count": full_count,
            "empty_count": empty_count,
            "high_risk": high_risk,
            "avg_risk": avg_risk,
            "risk_high_threshold": high_threshold,
        }
    )


@app.errorhandler(413)
def file_too_large(error):
    return jsonify({"error": "Image trop lourde. Limite : 5 Mo."}), 413


if __name__ == "__main__":
    app.run(debug=True, port=5000)
