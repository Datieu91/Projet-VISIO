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

    # Operational location context
    bin_location_id = db.Column(db.Integer, db.ForeignKey("bin_locations.id"), nullable=True)
    location_type = db.Column(db.String(30), default="unmatched", nullable=False)
    priority_level = db.Column(db.String(20), default="Normale", nullable=False)
    collected_at = db.Column(db.DateTime, nullable=True)

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

    bin_location = db.relationship("BinLocation", backref="reports")

    def final_label(self):
        return self.agent_annotation or self.ai_prediction

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
            "bin_location_id": self.bin_location_id,
            "bin_location_name": self.bin_location.name if self.bin_location else None,
            "location_type": self.location_type,
            "priority_level": self.priority_level,
            "collected_at": self.collected_at.strftime("%Y-%m-%d %H:%M:%S") if self.collected_at else None,
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
            "final_label": self.final_label(),
        }


class BinLocation(db.Model):
    __tablename__ = "bin_locations"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    lat = db.Column(db.Float, nullable=False)
    lng = db.Column(db.Float, nullable=False)
    zone = db.Column(db.String(120), nullable=True)
    bin_type = db.Column(db.String(60), default="classique", nullable=False)
    capacity_l = db.Column(db.Integer, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self, include_stats=False):
        payload = {
            "id": self.id,
            "name": self.name,
            "lat": self.lat,
            "lng": self.lng,
            "zone": self.zone or "",
            "bin_type": self.bin_type,
            "capacity_l": self.capacity_l,
            "is_active": self.is_active,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else "",
        }
        if include_stats:
            active_reports = [r for r in self.reports if r.status != "Collected"]
            payload.update({
                "report_count": len(self.reports),
                "active_report_count": len(active_reports),
                "full_active_count": sum(1 for r in active_reports if (r.agent_annotation or r.ai_prediction) == "Pleine"),
                "last_report": max((r.timestamp for r in self.reports), default=None).strftime("%Y-%m-%d %H:%M:%S") if self.reports else None,
            })
        return payload


class AppSetting(db.Model):
    __tablename__ = "app_settings"

    key = db.Column(db.String(80), primary_key=True)
    value = db.Column(db.String(255), nullable=False)
    label = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(60), nullable=False, default="general")
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "key": self.key,
            "value": self.value,
            "label": self.label,
            "description": self.description or "",
            "category": self.category,
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else "",
        }


class AgentActivity(db.Model):
    __tablename__ = "agent_activities"

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    username = db.Column(db.String(80), nullable=False)
    role = db.Column(db.String(30), nullable=False)
    action = db.Column(db.String(40), nullable=False)
    report_id = db.Column(db.Integer, db.ForeignKey("image_reports.id"), nullable=False)
    old_status = db.Column(db.String(20), nullable=True)
    new_status = db.Column(db.String(20), nullable=True)
    old_annotation = db.Column(db.String(20), nullable=True)
    new_annotation = db.Column(db.String(20), nullable=True)
    comment = db.Column(db.String(255), nullable=True)

    report = db.relationship("ImageReport", backref="activities")

    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "username": self.username,
            "role": self.role,
            "action": self.action,
            "report_id": self.report_id,
            "old_status": self.old_status,
            "new_status": self.new_status,
            "old_annotation": self.old_annotation,
            "new_annotation": self.new_annotation,
            "comment": self.comment or "",
            "report": self.report.to_dict() if self.report else None,
        }
