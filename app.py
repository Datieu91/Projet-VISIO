from flask import Flask, request, jsonify, render_template, send_from_directory
from werkzeug.utils import secure_filename
import os
import uuid

from database import db
from models import ImageReport
from image_processing import extract_features
from rule_engine import classify_image

app = Flask(__name__)

# Config
BASE_DIR = os.path.abspath(os.path.dirname(__name__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(BASE_DIR, "data", "db", "wdp.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
UPLOAD_FOLDER = os.path.join(BASE_DIR, "data", "uploads")
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

db.init_app(app)

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Create tables
with app.app_context():
    db.create_all()

# --- ROUTES (Pages HTML) ---

@app.route('/')
def citoyen_app():
    return render_template('citoyen.html')

@app.route('/agent')
def agent_app():
    return render_template('agent.html')

# --- API ROUTES ---

@app.route('/api/upload', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({"error": "Aucune image envoyée"}), 400
        
    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "Nom de fichier vide"}), 400
        
    lat = request.form.get('lat')
    lng = request.form.get('lng')
    tags = request.form.get('tags', '')

    # Save file
    filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    # 1. Feature Extraction
    features = extract_features(filepath)
    
    # 2. Rule Engine Classification
    prediction, confidence = classify_image(features)

    # 3. Save to DB
    new_report = ImageReport(
        filepath=f"/data/uploads/{filename}",
        lat=float(lat) if lat else None,
        lng=float(lng) if lng else None,
        citizen_tags=tags,
        file_size_kb=features["file_size_kb"],
        width=features["width"],
        height=features["height"],
        avg_color_hex=features["avg_color_hex"],
        contrast_level=features["contrast_level"],
        ai_prediction=prediction,
        ai_confidence=confidence
    )
    
    db.session.add(new_report)
    db.session.commit()

    return jsonify({
        "success": True,
        "report_id": new_report.id,
        "prediction": prediction,
        "confidence": confidence
    })

@app.route('/api/images/pending', methods=['GET'])
def get_pending_images():
    reports = ImageReport.query.filter_by(status="Pending").order_by(ImageReport.timestamp.desc()).all()
    return jsonify([r.to_dict() for r in reports])

@app.route('/api/images/<int:id>/annotate', methods=['POST'])
def annotate_image(id):
    data = request.json
    annotation = data.get('annotation') # "Pleine", "Vide", "Skip"
    
    report = ImageReport.query.get_or_404(id)
    
    if annotation in ["Pleine", "Vide"]:
        report.status = "Validated"
        report.agent_annotation = annotation
    else:
        report.status = "Ignored"
        
    db.session.commit()
    return jsonify({"success": True, "new_status": report.status})

@app.route('/data/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
