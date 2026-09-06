from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


def now():
    return datetime.now(timezone.utc)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    # "identifier" holds either an email address or a phone number.
    identifier = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    preferred_language = db.Column(db.String(20), default="English")
    created_at = db.Column(db.DateTime, default=now)

    conversations = db.relationship("Conversation", backref="user", lazy=True,
                                     cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {"id": self.id, "identifier": self.identifier,
                "preferred_language": self.preferred_language,
                "created_at": self.created_at.isoformat()}


class Conversation(db.Model):
    __tablename__ = "conversations"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(200), default="New conversation")
    created_at = db.Column(db.DateTime, default=now)

    messages = db.relationship("Message", backref="conversation", lazy=True,
                                cascade="all, delete-orphan", order_by="Message.timestamp")

    def to_dict(self, include_messages=False):
        d = {"id": self.id, "title": self.title, "created_at": self.created_at.isoformat()}
        if include_messages:
            d["messages"] = [m.to_dict() for m in self.messages]
        return d


class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey("conversations.id"), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'user' | 'assistant'
    content = db.Column(db.Text, nullable=False)
    language = db.Column(db.String(20), default="English")
    query_category = db.Column(db.String(30), default="health_qa")
    risk_level = db.Column(db.String(10), nullable=True)  # GREEN / YELLOW / RED
    timestamp = db.Column(db.DateTime, default=now)

    def to_dict(self):
        return {
            "id": self.id, "role": self.role, "content": self.content,
            "language": self.language, "query_category": self.query_category,
            "risk_level": self.risk_level, "timestamp": self.timestamp.isoformat(),
        }


class AnalyticsEvent(db.Model):
    """
    MODULE 9 -- PUBLIC HEALTH DASHBOARD
    Anonymized, aggregated-only records (no user_id, no free-text content)
    used purely to power the admin analytics dashboard.
    """
    __tablename__ = "analytics_events"

    id = db.Column(db.Integer, primary_key=True)
    query_category = db.Column(db.String(30))
    disease_topic = db.Column(db.String(60), nullable=True)
    language = db.Column(db.String(20))
    risk_level = db.Column(db.String(10), nullable=True)
    is_guest = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=now)
