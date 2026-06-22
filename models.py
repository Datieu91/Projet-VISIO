from database import db
from datetime import datetime

class ImageReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    filepath = db.Column(db.String(255), nullable=False)
    lat = db.Column(db.Float, nullable=True)
    lng = db.Column(db.Float, nullable=True)
    citizen_tags = db.Column(db.String(255), nullable=True)
    
    # Feature Extraction (Pillow/OpenCV)
    file_size_kb = db.Column(db.Integer, nullable=True)
    width = db.Column(db.Integer, nullable=True)
    height = db.Column(db.Integer, nullable=True)
    avg_color_hex = db.Column(db.String(7), nullable=True)
    contrast_level = db.Column(db.Float, nullable=True)
    
    # AI Pseudo-Classification
    ai_prediction = db.Column(db.String(20), nullable=True) # "Pleine" ou "Vide"
    ai_confidence = db.Column(db.Integer, nullable=True) # 0 to 100
    
    # Agent Validation
    status = db.Column(db.String(20), default="Pending") # "Pending", "Validated", "Ignored"
    agent_annotation = db.Column(db.String(20), nullable=True) # "Pleine", "Vide"

    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "filepath": self.filepath,
            "lat": self.lat,
            "lng": self.lng,
            "citizen_tags": self.citizen_tags,
            "file_size_kb": self.file_size_kb,
            "dimensions": f"{self.width}x{self.height}",
            "avg_color_hex": self.avg_color_hex,
            "ai_prediction": self.ai_prediction,
            "ai_confidence": self.ai_confidence,
            "status": self.status
        }
