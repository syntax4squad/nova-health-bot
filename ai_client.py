"""Groq client and health/non-health classification for SwasthyaSaathi."""

import re

from groq import Groq
from config import Config

_client = Groq(api_key=Config.GROQ_API_KEY) if Config.GROQ_API_KEY else None

SYSTEM_PROMPT = """You are SwasthyaSaathi, a public health awareness assistant.
Provide useful, clear, evidence-informed general health information. You are not
a substitute for a qualified healthcare professional.

Rules:
1. Answer health-related questions directly and helpfully, even when the local VERIFIED CONTEXT does not cover the topic. The verified context is supporting evidence, not a hard knowledge boundary.
2. Use general medical knowledge for gaps in the verified context. Never pretend unsupported information came from the knowledge base.
3. Do not claim certainty that a user has a particular disease. Discuss possibilities and explain when testing or medical evaluation may be appropriate.
4. You may discuss common self-care, prevention, treatment approaches, and over-the-counter medicines in general terms. Do not give individualized prescriptions, personalized dosing, or instructions that could create significant risk.
5. Never provide instructions for self-harm, poisoning, dangerous drug use, or other unsafe activity. The application separately blocks these requests.
6. If symptoms could represent an emergency, prioritize urgent professional help.
7. Be honest about uncertainty. Do not invent citations, sources, studies, or claims of verification.
8. Respond in the user's selected language ({language}).
9. Keep answers practical, readable, and appropriately detailed. Do not refuse merely because the knowledge base lacks the topic.
"""

HEALTH_KEYWORDS = {
    "health", "medical", "medicine", "doctor", "symptom", "symptoms", "disease",
    "illness", "condition", "pain", "fever", "cold", "cough", "flu", "headache",
    "migraine", "sore throat", "runny nose", "blocked nose", "congestion", "fatigue",
    "tired", "dizzy", "dizziness", "nausea", "vomit", "vomiting", "diarrhea",
    "constipation", "rash", "itch", "swelling", "infection", "wound", "injury",
    "blood", "bleeding", "breathing", "chest", "heart", "blood pressure", "sugar",
    "diabetes", "thyroid", "cancer", "tumor", "kidney", "liver", "stomach",
    "pregnant", "pregnancy", "period", "menstrual", "fertility", "sexual health",
    "contraception", "baby", "child", "infant", "mental health", "anxiety", "depression",
    "stress", "sleep", "insomnia", "diet", "nutrition", "vitamin", "mineral", "weight",
    "exercise", "workout", "vaccine", "vaccination", "antibiotic", "paracetamol",
    "acetaminophen", "ibuprofen", "tablet", "capsule", "dose", "dosage", "side effect",
    "allergy", "allergic", "dengue", "malaria", "tuberculosis", "tb", "covid", "covid-19",
    "hiv", "aids", "typhoid", "cholera", "hepatitis", "jaundice", "asthma", "arthritis",
    "ulcer", "acidity", "acid reflux", "blood sugar", "cholesterol", "immunity", "immune",
    "dehydration", "first aid", "home remedy", "remedy", "recover", "recovery", "heal",
    "healing", "prevent", "prevention", "transmission", "contagious", "treatment", "therapy",
}

NON_HEALTH_HINTS = {
    "python", "javascript", "java", "programming", "code", "coding", "html", "css", "sql",
    "linux", "flask", "django", "react", "telegram bot", "api", "debug", "movie", "movies",
    "film", "films", "song", "songs", "music", "game", "games", "gaming", "football", "cricket",
    "basketball", "anime", "manga", "travel", "weather", "stock market", "crypto", "cryptocurrency",
    "bitcoin", "ethereum", "logo", "banner", "poster", "design", "photoshop", "canva", "essay", "poem",
}


def is_configured() -> bool:
    return _client is not None


def _heuristic_health_relevance(text: str):
    t = re.sub(r"[^a-z0-9\s-]", " ", (text or "").lower())
    t = re.sub(r"\s+", " ", t).strip()

    def hit(keyword):
        pattern = r"(?<![a-z0-9])" + re.escape(keyword) + r"(?![a-z0-9])"
        return bool(re.search(pattern, t))

    health_hits = sum(1 for k in HEALTH_KEYWORDS if hit(k))
    non_health_hits = sum(1 for k in NON_HEALTH_HINTS if hit(k))

    if health_hits and health_hits >= non_health_hits:
        return True
    if non_health_hits and non_health_hits > health_hits:
        return False
    return None


def classify_health_question(user_message: str) -> bool:
    """
    Determine whether a request belongs to the health/medical domain.
    Safety checks (crisis/emergency/unsafe) are performed separately before
    this function is called.

    We deliberately favor HEALTH for ambiguous questions so that an uncommon
    medical condition (for example, elephantiasis) is not rejected simply
    because its name is absent from HEALTH_KEYWORDS.
    """
    heuristic = _heuristic_health_relevance(user_message)
    # If the heuristic clearly identifies the request, trust it.
    if heuristic is not None:
        return heuristic

    # If Groq is available, use it for ambiguous requests.
    if is_configured():
        try:
            completion = _client.chat.completions.create(
                model=Config.GROQ_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Determine whether the user's request is related "
                            "to health or medicine.\n\n"
                            "Return exactly one word: HEALTH or NON_HEALTH.\n\n"
                            "HEALTH includes ANY topic involving human health, "
                            "medical conditions, diseases, symptoms, causes, "
                            "prevention, diagnosis information, treatment, "
                            "medicines, side effects, nutrition, fitness, "
                            "mental wellbeing, reproductive health, sexual "
                            "health, first aid, body functions, anatomy, "
                            "or general healthcare.\n\n"
                            "This includes uncommon diseases and medical "
                            "conditions even if their names are unfamiliar.\n\n"
                            "NON_HEALTH includes programming, coding, software, "
                            "technology, entertainment, films, music, games, "
                            "sports, travel, graphic design, finance, "
                            "cryptocurrency, and similar unrelated topics."
                        ),
                    },
                    {
                        "role": "user",
                        "content": user_message,
                    },
                ],
                temperature=0,
                max_tokens=5,
            )
            result = (
                completion.choices[0].message.content or ""
            ).strip().upper()
            if "HEALTH" in result and "NON_HEALTH" not in result:
                return True
            if "NON_HEALTH" in result:
                return False
        except Exception:
            # If classification fails, favor health rather than incorrectly
            # rejecting a potentially legitimate medical question.
            pass

    # IMPORTANT:
    # If classification is unavailable/ambiguous, default to HEALTH.
    # The separate safety layer has already handled dangerous requests.
    return True


def generate_answer(user_message: str, context_chunks: list, language: str = "English", history: list | None = None) -> str:
    if not is_configured():
        return "I don't have an AI model connected yet. Please configure GROQ_API_KEY in the .env file.\n\n" + _format_context_fallback(context_chunks)

    context_text = "\n".join(
        f"- [{c['disease']} / {c['field']}] {c['text']}" for c in context_chunks
    ) or "No directly relevant verified context was found. Use general medical knowledge for this question."

    messages = [{"role": "system", "content": SYSTEM_PROMPT.format(language=language)}]

    for turn in (history or [])[-6:]:
        messages.append({"role": turn["role"], "content": turn["content"]})

    messages.append({
        "role": "user",
        "content": (
            "VERIFIED CONTEXT (supporting information from the local health knowledge base):\n"
            f"{context_text}\n\nUSER QUESTION: {user_message}\n\n"
            f"Answer the health question in {language}. Use verified context where relevant, "
            "but do not refuse if it is incomplete or absent. Fill reasonable gaps using "
            "general medical knowledge."
        ),
    })

    try:
        completion = _client.chat.completions.create(
            model=Config.GROQ_MODEL, messages=messages, temperature=0.45, max_tokens=800
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        return "Sorry, I couldn't reach the AI model right now " + f"({type(e).__name__}).\n\n" + _format_context_fallback(context_chunks)


def translate_or_generate_simple(prompt: str, language: str = "English") -> str:
    if not is_configured():
        return prompt
    try:
        completion = _client.chat.completions.create(
            model=Config.GROQ_MODEL,
            messages=[
                {"role": "system", "content": f"Respond only in {language}. Be concise."},
                {"role": "user", "content": prompt},
            ], temperature=0.3, max_tokens=300,
        )
        return completion.choices[0].message.content.strip()
    except Exception:
        return prompt


def _format_context_fallback(context_chunks: list) -> str:
    if not context_chunks:
        return "No matching information was found in the knowledge base for this query."
    return "\n".join(f"- [{c['disease']}] {c['text']}" for c in context_chunks)
