import os
import re
from functools import wraps

from flask import Flask, request, jsonify, session, render_template, redirect, url_for

from config import Config
from models import db, User, Conversation, Message, AnalyticsEvent
import rag
import safety
import ai_client
import claim_checker

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

os.makedirs(os.path.join(Config.BASE_DIR, "instance"), exist_ok=True)

with app.app_context():
    db.create_all()

SUPPORTED_LANGUAGES = ["English", "Hindi", "Odia"]

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^\+?\d{7,15}$")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return db.session.get(User, uid)


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return jsonify({"error": "Authentication required."}), 401
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return wrapper


def log_event(category, disease_topic, language, risk_level, is_guest, **extra):
    try:
        db.session.add(AnalyticsEvent(
            query_category=category, disease_topic=disease_topic,
            language=language, risk_level=risk_level, is_guest=is_guest,
        ))
        db.session.commit()
    except Exception:
        db.session.rollback()


def client_ip():
    # Respect a single, trusted-proxy X-Forwarded-For hop if present;
    # otherwise fall back to the direct remote address.
    fwd = request.headers.get("X-Forwarded-For", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.remote_addr or "unknown"


# ---------------------------------------------------------------------------
# Page routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    user = current_user()
    return render_template("index.html", user=user.to_dict() if user else None,
                            languages=SUPPORTED_LANGUAGES)


@app.route("/register")
def register_page():
    if current_user():
        return redirect(url_for("index"))
    return render_template("register.html")


@app.route("/login")
def login_page():
    if current_user():
        return redirect(url_for("index"))
    return render_template("login.html")


@app.route("/admin")
def admin_login():
    if session.get("is_admin"):
        return redirect(url_for("admin_dashboard"))
    return render_template("admin_login.html")


@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    return render_template("admin.html")


# ---------------------------------------------------------------------------
# Auth API  (email/phone + password only, per spec)
# ---------------------------------------------------------------------------

@app.route("/api/auth/register", methods=["POST"])
def api_register():
    data = request.get_json(silent=True) or {}
    identifier = (data.get("identifier") or "").strip().lower()
    password = data.get("password") or ""

    if not identifier or not password:
        return jsonify({"error": "Email/phone and password are required."}), 400
    if not (EMAIL_RE.match(identifier) or PHONE_RE.match(identifier)):
        return jsonify({"error": "Enter a valid email address or phone number."}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400
    if User.query.filter_by(identifier=identifier).first():
        return jsonify({"error": "An account with this email/phone already exists."}), 409

    user = User(identifier=identifier)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    session["user_id"] = user.id
    return jsonify({"message": "Registered successfully.", "user": user.to_dict()}), 201


@app.route("/api/auth/login", methods=["POST"])
def api_login():
    data = request.get_json(silent=True) or {}
    identifier = (data.get("identifier") or "").strip().lower()
    password = data.get("password") or ""

    user = User.query.filter_by(identifier=identifier).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid email/phone or password."}), 401

    session["user_id"] = user.id
    return jsonify({"message": "Logged in.", "user": user.to_dict()})


@app.route("/api/auth/logout", methods=["POST"])
def api_logout():
    session.pop("user_id", None)
    return jsonify({"message": "Logged out."})


@app.route("/api/auth/me")
def api_me():
    user = current_user()
    return jsonify({"user": user.to_dict() if user else None})


# ---------------------------------------------------------------------------
# Conversation history API (registered users only)
# ---------------------------------------------------------------------------

@app.route("/api/conversations")
@login_required
def api_conversations():
    user = current_user()
    convos = Conversation.query.filter_by(user_id=user.id).order_by(Conversation.created_at.desc()).all()
    return jsonify({"conversations": [c.to_dict() for c in convos]})


@app.route("/api/conversations/<int:conv_id>")
@login_required
def api_conversation_detail(conv_id):
    user = current_user()
    convo = Conversation.query.filter_by(id=conv_id, user_id=user.id).first()
    if not convo:
        return jsonify({"error": "Not found."}), 404
    return jsonify({"conversation": convo.to_dict(include_messages=True)})


@app.route("/api/conversations", methods=["POST"])
@login_required
def api_new_conversation():
    user = current_user()
    convo = Conversation(user_id=user.id, title="New conversation")
    db.session.add(convo)
    db.session.commit()
    return jsonify({"conversation": convo.to_dict()}), 201


# ---------------------------------------------------------------------------
# MODULE 1 -- AI Health Assistant (core chat, RAG + safety pipeline)
# ---------------------------------------------------------------------------

@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json(silent=True) or {}
    user_message = (data.get("message") or "").strip()
    language = data.get("language") if data.get("language") in SUPPORTED_LANGUAGES else "English"
    conv_id = data.get("conversation_id")

    if not user_message:
        return jsonify({"error": "Message is required."}), 400

    user = current_user()
    is_guest = user is None

    # --- INPUT SAFETY FILTER: Crisis / Emergency / Unsafe / Normal ---
    category = safety.classify_input(user_message)

    if category == "crisis":
        answer = safety.sanitize_output(safety.CRISIS_MESSAGE, language)
        risk_level = "RED"
        query_category = "crisis"
        context_chunks = []
    elif category == "emergency":
        answer = safety.sanitize_output(safety.EMERGENCY_MESSAGE, language)
        risk_level = "RED"
        query_category = "emergency"
        context_chunks = []
    elif category == "unsafe":
        answer = safety.sanitize_output(safety.UNSAFE_MESSAGE, language)
        risk_level = None
        query_category = "unsafe_blocked"
        context_chunks = []
    else:
        # Health relevance is checked separately from the safety filter. This
        # keeps the assistant broad across medical topics while preventing it
        # from becoming a general-purpose assistant.
        is_health = ai_client.classify_health_question(user_message)
        if not is_health:
            answer = (
                "I’m designed to help with health and medical questions. "
                "Please ask me something related to health, symptoms, medicines, "
                "prevention, nutrition, wellbeing, or another medical topic."
            )
            risk_level = None
            query_category = "non_health"
            context_chunks = []
        else:
            # RAG is supporting evidence, not a hard knowledge boundary.
            context_chunks = rag.retrieve(user_message, top_k=4)
            history = []
            convo = None
            if user and conv_id:
                convo = Conversation.query.filter_by(id=conv_id, user_id=user.id).first()
                if convo:
                    history = [{"role": m.role, "content": m.content} for m in convo.messages]

            raw_answer = ai_client.generate_answer(user_message, context_chunks, language, history)
            answer = safety.sanitize_output(raw_answer, language)
            risk_level = None
            query_category = "health_qa"

    disease_topic = rag.detect_disease_topic(user_message) if category != "crisis" and category != "emergency" else None
    log_event(query_category, disease_topic, language, risk_level, is_guest)

    sources = []
    if category == "normal" and query_category == "health_qa":
        seen = set()
        for c in context_chunks:
            if c["disease"] not in seen:
                sources.append({"disease": c["disease"], "source": c["source"],
                                 "last_updated": c["last_updated"]})
                seen.add(c["disease"])

    conversation_out = None
    if user:
        convo = None
        if conv_id:
            convo = Conversation.query.filter_by(id=conv_id, user_id=user.id).first()
        if not convo:
            title = user_message[:60] + ("..." if len(user_message) > 60 else "")
            convo = Conversation(user_id=user.id, title=title or "New conversation")
            db.session.add(convo)
            db.session.flush()

        db.session.add(Message(conversation_id=convo.id, role="user", content=user_message,
                                language=language, query_category=query_category))
        db.session.add(Message(conversation_id=convo.id, role="assistant", content=answer,
                                language=language, query_category=query_category,
                                risk_level=risk_level))
        db.session.commit()
        conversation_out = convo.to_dict()

    return jsonify({
        "answer": answer,
        "category": category,
        "risk_level": risk_level,
        "sources": sources,
        "saved": user is not None,
        "conversation": conversation_out,
    })


# ---------------------------------------------------------------------------
# MODULE 2 -- Symptom risk-awareness guide
# ---------------------------------------------------------------------------

@app.route("/api/risk-assessment", methods=["POST"])
def api_risk_assessment():
    data = request.get_json(silent=True) or {}
    symptoms = data.get("symptoms") or []
    duration = data.get("duration") or ""
    language = data.get("language") if data.get("language") in SUPPORTED_LANGUAGES else "English"

    result = safety.assess_risk(symptoms, duration)
    user = current_user()
    log_event("risk_assessment", None, language, result["level"], user is None)

    return jsonify(result)


# ---------------------------------------------------------------------------
# MODULE 7 -- AI Health Claim Fact-Checker
#
# Real evidence-grounded analysis (claim_checker.py) instead of pure
# fuzzy-text matching against a static myth table:
#   safety filter -> claim validation -> local fast-path lookup
#   -> live evidence search (trusted-domain filtered) -> Groq structured
#   analysis -> verdict + confidence + cited sources
# ---------------------------------------------------------------------------

_fact_check_hits = {}  # very small in-memory rate limiter: ip -> [timestamps]


def _fact_check_rate_limited(ip: str) -> bool:
    import time
    window = 60.0
    limit = Config.FACT_CHECK_RATE_LIMIT_PER_MIN
    now = time.time()
    hits = [t for t in _fact_check_hits.get(ip, []) if now - t < window]
    hits.append(now)
    _fact_check_hits[ip] = hits
    return len(hits) > limit


@app.route("/api/misinformation", methods=["POST"])
def api_misinformation():
    data = request.get_json(silent=True) or {}
    claim = (data.get("claim") or "").strip()
    language = data.get("language") if data.get("language") in SUPPORTED_LANGUAGES else "English"

    if not claim:
        return jsonify({"status": "invalid", "message": "Please enter a health claim to check."}), 400
    if len(claim) > Config.FACT_CHECK_MAX_CLAIM_LENGTH:
        return jsonify({
            "status": "invalid",
            "message": f"That claim is too long (max {Config.FACT_CHECK_MAX_CLAIM_LENGTH} characters).",
        }), 400

    if _fact_check_rate_limited(client_ip()):
        return jsonify({
            "status": "rate_limited",
            "message": "You're checking claims a bit fast — please wait a minute and try again.",
        }), 429

    # Safety filter runs first and cannot be overridden by the fact-checker.
    category = safety.classify_input(claim)
    if category in ("crisis", "emergency"):
        message = safety.CRISIS_MESSAGE if category == "crisis" else safety.EMERGENCY_MESSAGE
        user = current_user()
        log_event("misinformation", None, language, "RED", user is None)
        return jsonify({
            "status": "safety_override",
            "verdict": None,
            "message": safety.sanitize_output(message, language),
        })

    try:
        result = claim_checker.analyze_claim(claim=claim, language=language)
    except claim_checker.ClaimCheckerError as e:
        user = current_user()
        log_event("misinformation", None, language, None, user is None)
        return jsonify({"status": e.status, "message": e.message}), e.http_status
    except Exception:
        user = current_user()
        log_event("misinformation", None, language, None, user is None)
        return jsonify({
            "status": "error",
            "message": "Something went wrong while fact-checking this claim. Please try again shortly.",
        }), 500

    user = current_user()
    log_event("misinformation", None, language, None, user is None)

    return jsonify(result)


# ---------------------------------------------------------------------------
# Disease library
# ---------------------------------------------------------------------------

@app.route("/api/diseases")
def api_diseases():
    return jsonify({"diseases": rag.list_diseases()})


@app.route("/api/diseases/<key>")
def api_disease_detail(key):
    d = rag.get_disease(key)
    if not d:
        return jsonify({"error": "Not found."}), 404
    return jsonify({"disease": d})


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------

@app.route("/api/admin/login", methods=["POST"])
def api_admin_login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if email == Config.ADMIN_EMAIL.strip().lower() and password == Config.ADMIN_PASSWORD:
        session["is_admin"] = True
        return jsonify({"message": "Admin logged in."})
    return jsonify({"error": "Invalid admin credentials."}), 401


@app.route("/api/admin/logout", methods=["POST"])
def api_admin_logout():
    session.pop("is_admin", None)
    return jsonify({"message": "Logged out."})


@app.route("/api/admin/analytics")
@admin_required
def api_admin_analytics():
    total_users = User.query.count()
    total_conversations = Conversation.query.count()
    total_messages = Message.query.count()
    total_queries = AnalyticsEvent.query.count()

    from sqlalchemy import func
    by_category = dict(
        db.session.query(AnalyticsEvent.query_category, func.count(AnalyticsEvent.id))
        .group_by(AnalyticsEvent.query_category).all()
    )
    by_language = dict(
        db.session.query(AnalyticsEvent.language, func.count(AnalyticsEvent.id))
        .group_by(AnalyticsEvent.language).all()
    )
    by_risk = dict(
        db.session.query(AnalyticsEvent.risk_level, func.count(AnalyticsEvent.id))
        .filter(AnalyticsEvent.risk_level.isnot(None))
        .group_by(AnalyticsEvent.risk_level).all()
    )
    by_disease = dict(
        db.session.query(AnalyticsEvent.disease_topic, func.count(AnalyticsEvent.id))
        .filter(AnalyticsEvent.disease_topic.isnot(None))
        .group_by(AnalyticsEvent.disease_topic).all()
    )
    guest_vs_registered = dict(
        db.session.query(AnalyticsEvent.is_guest, func.count(AnalyticsEvent.id))
        .group_by(AnalyticsEvent.is_guest).all()
    )

    return jsonify({
        "totals": {
            "users": total_users,
            "conversations": total_conversations,
            "messages": total_messages,
            "queries": total_queries,
        },
        "by_category": by_category,
        "by_language": by_language,
        "by_risk_level": by_risk,
        "by_disease_topic": by_disease,
        "guest_vs_registered": {("guest" if k else "registered"): v
                                 for k, v in guest_vs_registered.items()},
        "ai_configured": ai_client.is_configured(),
        "fact_check_live_search_configured": claim_checker.is_live_search_configured(),
        "fact_check_search_provider": claim_checker.current_search_provider_name(),
    })


if __name__ == "__main__":
    app.run(debug=Config.DEBUG, host="0.0.0.0", port=5000)
