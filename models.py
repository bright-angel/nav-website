from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

db = SQLAlchemy()


class Site(db.Model):
    __tablename__ = "sites"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    description = db.Column(db.String(200), default="")
    category = db.Column(db.String(50), nullable=False, default="Other")
    icon_url = db.Column(db.Text(), default="")
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "description": self.description,
            "category": self.category,
            "icon_url": self.icon_url,
            "sort_order": self.sort_order,
        }

    @staticmethod
    def from_dict(data):
        return Site(
            name=data.get("name", ""),
            url=data.get("url", ""),
            description=data.get("description", ""),
            category=data.get("category", "Other"),
            icon_url=data.get("icon_url", ""),
            sort_order=data.get("sort_order", 0),
        )
