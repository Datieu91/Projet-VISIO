from datetime import datetime
from database import db


class ImageReport(db.Model):
    __tablename__ = "image_reports"

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # File and citizen information
    stored_filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(255), nullable=False)
    lat = db.Column(db.Float, nullable=True)
    lng = db.Column(db.Float, nullable=True)
    citizen_tags = db.Column(db.String(255), nullable=True)

    # Image features
    file_size_kb = db.Column(db.Integer, nullable=True)
    width = db.Column(db.Integer, nullable=True)
    height = db.Column(db.Integer, nullable=True)
    avg_color_hex = db.Column(db.String(7), nullable=True)
    brightness = db.Column(db.Float, nullable=True)
    contrast_level = db.Column(db.Float, nullable=True)
    quality_score = db.Column(db.Integer, nullable=True)
    quality_warning = db.Column(db.String(255), nullable=True)

    # Rule-based classification
    ai_prediction = db.Column(db.String(20), nullable=True)
    ai_confidence = db.Column(db.Integer, nullable=True)

    # Added value: risk scoring
    risk_score = db.Column(db.Integer, nullable=True)
    risk_level = db.Column(db.String(20), nullable=True)
    risk_explanation = db.Column(db.Text, nullable=True)

    # Agent validation
    status = db.Column(db.String(20), default="Pending", nullable=False)
    agent_annotation = db.Column(db.String(20), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "stored_filename": self.stored_filename,
            "filepath": self.filepath,
            "image_url": f"/uploads/{self.stored_filename}",
            "lat": self.lat,
            "lng": self.lng,
            "citizen_tags": self.citizen_tags or "",
            "file_size_kb": self.file_size_kb,
            "width": self.width,
            "height": self.height,
            "dimensions": f"{self.width}x{self.height}" if self.width and self.height else "--",
            "avg_color_hex": self.avg_color_hex,
            "brightness": self.brightness,
            "contrast_level": self.contrast_level,
            "quality_score": self.quality_score,
            "quality_warning": self.quality_warning,
            "ai_prediction": self.ai_prediction,
            "ai_confidence": self.ai_confidence,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "risk_explanation": self.risk_explanation,
            "status": self.status,
            "agent_annotation": self.agent_annotation,
        }
