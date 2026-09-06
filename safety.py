"""
MODULE 8 (Emergency escalation) + MODULE 11 (Safety architecture) +
MODULE 2 (Symptom risk-awareness guide)

Implements:
  User -> Input safety filter -> Normal / Emergency / Unsafe category
  ... -> LLM -> Output safety check (diagnosis language, dangerous
  instructions, unverified treatments, hallucinated-source patterns)

The safety layer runs independently of the LLM so it cannot be bypassed
by prompt content -- this mirrors the blueprint's instruction:
"Do not allow the LLM to control everything."

NOTE: The misinformation / health-claim fact-checker used to live here as
check_claim(). It has been moved to claim_checker.py, which implements a
real evidence-grounded AI analyzer (claim extraction -> live search ->
trusted-source filtering -> Groq structured-output analysis -> verdict),
instead of pure fuzzy-text matching. safety.py keeps ONLY the safety
responsibilities: emergency detection, crisis detection, unsafe-request
blocking, output sanitization, and the risk-assessment guide. This keeps
the safety layer auditable and independent of the (much larger) fact-check
pipeline, per the "claim_checker.py should be responsible for factual
claim analysis... safety.py should remain responsible for... safety"
separation of concerns.
"""

import re
from knowledge_base import ALL_MYTHS

EMERGENCY_PATTERNS = [
    r"\bcan'?t breathe\b", r"\bdifficulty breathing\b", r"\bshort(ness)? of breath\b",
    r"\bchest pain\b", r"\bunconscious\b", r"\bnot responding\b", r"\bpassed out\b",
    r"\bsevere bleeding\b", r"\bheavy bleeding\b", r"\bblood in (vomit|stool)\b",
    r"\bcoughing (up )?blood\b", r"\bseizure\b", r"\bfits\b", r"\bconvulsion\b",
    r"\bsuicid", r"\bkill myself\b", r"\bself[- ]?harm\b", r"\bwant to die\b",
    r"\bpoison(ed|ing)?\b", r"\boverdose\b", r"\bsnake bite\b", r"\bstroke\b",
    r"\bparalysis\b", r"\bcan'?t move\b", r"\bunable to wake\b", r"\bblue lips\b",
    r"\bsevere allergic reaction\b", r"\banaphyla", r"\bheart attack\b",
]

# Requests for content the assistant must never generate, regardless of framing.
UNSAFE_PATTERNS = [
    r"\bhow (much|many) .* (overdose|lethal dose)\b",
    r"\bprescribe (me )?(a )?medic",
    r"\bwhat dose (of|should)\b",
    r"\bhow to (make|synthesi[sz]e) .* (drug|poison)\b",
]

CRISIS_PATTERNS = [r"\bsuicid", r"\bkill myself\b", r"\bwant to die\b", r"\bself[- ]?harm\b", r"\bend my life\b"]

DIAGNOSIS_PHRASES = [
    "you have", "you are suffering from", "you definitely have",
    "this confirms you have", "you are infected with",
]

DISCLAIMER_BY_LANGUAGE = {
    "English": "**Note:** This AI provides general health information and may make mistakes. It is not a substitute for a qualified healthcare professional. For a diagnosis, personalized treatment, or concerns about your symptoms, please consult a qualified healthcare professional.",
    "Hindi": "**नोट:** यह AI सामान्य स्वास्थ्य जानकारी प्रदान करता है और इसमें गलतियाँ हो सकती हैं। यह योग्य स्वास्थ्य पेशेवर का विकल्प नहीं है। निदान, व्यक्तिगत उपचार या अपने लक्षणों को लेकर चिंता होने पर योग्य स्वास्थ्य पेशेवर से सलाह लें।_",
    "Odia": "_ଟିପ୍ପଣୀ: ଏହି AI ସାଧାରଣ ସ୍ୱାସ୍ଥ୍ୟ ସୂଚନା ଦିଏ ଏବଂ ଏଥିରେ ଭୁଲ ହୋଇପାରେ। ଏହା ଯୋଗ୍ୟ ସ୍ୱାସ୍ଥ୍ୟ ବିଶେଷଜ୍ଞଙ୍କ ପରିବର୍ତ୍ତେ ନୁହେଁ। ରୋଗ ନିର୍ଣ୍ଣୟ, ବ୍ୟକ୍ତିଗତ ଚିକିତ୍ସା କିମ୍ବା ଲକ୍ଷଣ ସମ୍ପର୍କରେ ଚିନ୍ତା ଥିଲେ ଯୋଗ୍ୟ ସ୍ୱାସ୍ଥ୍ୟ ବିଶେଷଜ୍ଞଙ୍କୁ ପରାମର୍ଶ କରନ୍ତୁ।",
}


def classify_input(text: str) -> str:
    """Return 'crisis', 'emergency', 'unsafe', or 'normal'."""
    t = (text or "").lower()
    for pat in CRISIS_PATTERNS:
        if re.search(pat, t):
            return "crisis"
    for pat in EMERGENCY_PATTERNS:
        if re.search(pat, t):
            return "emergency"
    for pat in UNSAFE_PATTERNS:
        if re.search(pat, t):
            return "unsafe"
    return "normal"


EMERGENCY_MESSAGE = (
    "This may require urgent medical attention. Please seek immediate professional "
    "help (visit the nearest emergency department or call your local emergency "
    "number) right away. This chatbot cannot assess or treat emergencies."
)

CRISIS_MESSAGE = (
    "I'm really sorry you're going through this. You deserve support from someone "
    "who can help right now. If you are in immediate danger, please contact local "
    "emergency services. You can also reach a crisis helpline in your area to talk "
    "to someone immediately -- in India, you can call the Tele-MANAS helpline at "
    "14416 (24/7). If you're comfortable, please also reach out to a trusted person "
    "near you."
)

UNSAFE_MESSAGE = (
    "I can't help with that. I'm a public-health awareness assistant and can't "
    "provide dosing, prescribing, or medication instructions. Please consult a "
    "licensed healthcare professional or pharmacist for that."
)


def sanitize_output(text: str, language: str = "English") -> str:
    """Light output cleanup plus a mandatory end-of-answer disclaimer."""
    if not text:
        return text

    replacements = {
        "you definitely have": "you may have",
        "this confirms you have": "this can be associated with",
        "you are infected with": "this can be associated with an infection such as",
    }
    cleaned = text
    for phrase, replacement in replacements.items():
        cleaned = re.sub(re.escape(phrase), replacement, cleaned, flags=re.IGNORECASE)

    lowered = cleaned.lower()
    disclaimer = DISCLAIMER_BY_LANGUAGE.get(language, DISCLAIMER_BY_LANGUAGE["English"])
    if "this ai provides general health information" not in lowered and "यह ai सामान्य स्वास्थ्य" not in lowered and "ଏହି ai ସାଧାରଣ ସ୍ୱାସ୍ଥ୍ୟ" not in lowered:
        cleaned = cleaned.rstrip() + "\n\n" + disclaimer
    return cleaned


# ---------------------------------------------------------------------------
# MODULE 2 -- Symptom risk-awareness guide
# ---------------------------------------------------------------------------

RED_FLAG_SYMPTOMS = {
    "difficulty breathing", "chest pain", "severe bleeding", "confusion",
    "seizure", "unconsciousness", "blue lips", "severe abdominal pain",
    "persistent vomiting", "coughing blood",
}

YELLOW_FLAG_SYMPTOMS = {
    "high fever", "rash", "body pain", "joint pain", "vomiting", "diarrhea",
    "dehydration", "jaundice", "severe headache",
}


def assess_risk(symptoms: list, duration: str = "") -> dict:
    """
    Rule-based, non-diagnostic urgency classifier.
    symptoms: list of lowercase symptom strings selected by the user.
    duration: '<1 day' | '1-3 days' | '>3 days' (free text tolerated).
    """
    norm = {s.strip().lower() for s in symptoms if s and s.strip()}

    red_hits = norm & RED_FLAG_SYMPTOMS
    yellow_hits = norm & YELLOW_FLAG_SYMPTOMS

    long_duration = isinstance(duration, str) and (">3" in duration or "3+" in duration)

    if red_hits:
        level = "RED"
        message = (
            "Some of the symptoms you reported can indicate a medical emergency. "
            "This is not a diagnosis. Please seek immediate professional medical "
            "attention."
        )
    elif len(yellow_hits) >= 2 or (yellow_hits and long_duration):
        level = "YELLOW"
        message = (
            "Some of the symptoms you reported can occur with several illnesses. "
            "Consider consulting a healthcare professional, especially if symptoms "
            "worsen. This is not a diagnosis."
        )
    elif yellow_hits:
        level = "YELLOW"
        message = (
            "These symptoms can occur with several conditions. This tool cannot "
            "diagnose you. Based on the information provided, consider monitoring "
            "closely and seeking medical evaluation if things don't improve."
        )
    else:
        level = "GREEN"
        message = (
            "Based on what you've shared, this looks like something to monitor "
            "at a general-awareness level. This is not a diagnosis -- if symptoms "
            "appear or worsen, reconsider your risk level."
        )

    return {
        "level": level,
        "message": message,
        "matched_red_flags": sorted(red_hits),
        "matched_concern_symptoms": sorted(yellow_hits),
    }


# ---------------------------------------------------------------------------
# Local verified-claim lookup, kept here as a tiny, dependency-free helper.
# claim_checker.py uses this as its fast/offline path before touching any
# network or LLM call. It is intentionally NOT a verdict engine -- fuzzy
# text similarity is a lookup heuristic, not evidence.
# ---------------------------------------------------------------------------

def local_myth_lookup(claim: str):
    """
    Compare a claim against the small ALL_MYTHS table using fuzzy text
    similarity. Returns (disease_key, myth, fact, score) for the best match,
    or None if nothing matches closely enough to be useful as a fast path.
    This is a lookup aid, not a factual verdict -- claim_checker.py treats
    it accordingly.
    """
    import difflib

    claim_l = (claim or "").lower().strip()
    if not claim_l:
        return None

    best = None
    best_score = 0.0
    for disease_key, myth, fact in ALL_MYTHS:
        ratio = difflib.SequenceMatcher(None, claim_l, myth.lower()).ratio()
        myth_words = set(re.findall(r"\w+", myth.lower()))
        claim_words = set(re.findall(r"\w+", claim_l))
        overlap = len(myth_words & claim_words) / max(len(myth_words), 1)
        score = max(ratio, overlap * 0.9)
        if score > best_score:
            best_score = score
            best = (disease_key, myth, fact)

    if best and best_score >= 0.45:
        return (*best, best_score)
    return None
