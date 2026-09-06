# Nova Health Bot

A working prototype for **SIH25049 — AI-Driven Public Health Chatbot for Disease
Awareness** (Government of Odisha). Built as a real Flask server (not a static
page) with a SQLite database, user accounts, a RAG pipeline over a verified
disease knowledge base, a rule-based safety/emergency layer, a symptom
risk-awareness guide, a misinformation checker, and an admin analytics
dashboard — following the modules laid out in the hackathon blueprint.

> **Core principle carried through the whole app:** Public health awareness ≠
> medical diagnosis. The system never claims to diagnose, prescribe, or
> replace a doctor.

## What's implemented

| Blueprint module | Implementation |
|---|---|
| Module 1 — AI Health Assistant | `/api/chat` — safety filter → intent → RAG retrieval → LLM (Groq) → output safety → response |
| Module 2 — Symptom risk-awareness guide | `/api/risk-assessment` — rule-based GREEN/YELLOW/RED classifier, non-diagnostic |
| Module 3 — Disease knowledge base | `knowledge_base.py` — 10 diseases (Dengue, Malaria, TB, COVID-19, Cholera, Typhoid, Influenza, Japanese encephalitis, Hepatitis, Chikungunya) with overview/symptoms/warning signs/transmission/prevention/myths/facts/source |
| Module 4 — RAG | `rag.py` — TF-IDF vector retrieval (scikit-learn) over the knowledge base, feeding grounded context into the LLM prompt instead of `Question → LLM → Answer` |
| Module 5 — Multilingual | English / Hindi / Odia selector; language is passed to the LLM system prompt |
| Module 7 — Misinformation checker | `/api/misinformation` — **AI-powered, evidence-grounded fact-checker** (`claim_checker.py`): claim extraction → live web search (trusted-domain filtered) → Groq structured-output analysis → cited verdict. The old local myth table remains as an offline fast path. See "AI Health Claim Fact-Checker" below. |
| Module 8 — Emergency escalation | `safety.py` — regex-based emergency & crisis detection that **overrides** the normal chatbot flow before the LLM is even called |
| Module 9 — Public health dashboard | `/admin` — anonymized, aggregated analytics (no free-text content stored in analytics events) |
| Module 11 — Safety architecture | Input safety filter and output safety checks live **outside** the LLM call, so the model can't be prompted around them |
| User accounts | Simple email/phone + password registration and login (Werkzeug password hashing, Flask session cookies) |
| Guest mode | Anyone can chat without registering; guest messages are processed but never written to the database |
| Admin | Separate `/admin` login using `ADMIN_EMAIL` / `ADMIN_PASSWORD` from `.env` |

## Tech stack actually used

- **Backend:** Flask + Flask-SQLAlchemy (SQLite)
- **Auth:** Werkzeug password hashing + server-side sessions
- **AI:** [Groq](https://console.groq.com) free-tier LLM API (`openai/gpt-oss-120b` by default) via the official `groq` Python SDK
- **RAG:** scikit-learn TF-IDF + cosine similarity (no external vector DB needed for a 10-disease prototype)
- **Fact-checking search:** pluggable provider (Serper / SerpApi / Google Programmable Search / DuckDuckGo zero-config fallback) via `requests` — see "AI Health Claim Fact-Checker" below
- **Frontend:** Server-rendered Jinja templates + vanilla JS/CSS (no build step)
- **Secrets:** `.env` file (loaded with `python-dotenv`), never committed (see `.gitignore`)

## Project structure

```
healthdesk/
├── app.py                 # Flask app: routes, auth, chat pipeline, admin API
├── config.py               # Loads .env into a Config object
├── models.py                # SQLAlchemy models: User, Conversation, Message, AnalyticsEvent
├── knowledge_base.py        # Verified disease knowledge base (Module 3)
├── rag.py                   # TF-IDF retrieval layer (Module 4)
├── safety.py                 # Emergency/crisis detection, risk assessment, output safety, local myth lookup
├── claim_checker.py           # AI-powered evidence-grounded fact-checker (Module 7)
├── ai_client.py               # Groq LLM wrapper + system prompt + health classifier (Module 10)
├── templates/                # index.html, login.html, register.html, admin_login.html, admin.html
├── static/                   # style.css, app.js
├── requirements.txt
├── .env.example              # Copy to .env and fill in
└── instance/                 # SQLite DB gets created here at runtime
```


## Setup

```bash
cd nova-health-bot
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# then edit .env:
#   - set SECRET_KEY (python -c "import secrets; print(secrets.token_hex(32))")
#   - set GROQ_API_KEY (free key: https://console.groq.com/keys)
#   - set ADMIN_EMAIL / ADMIN_PASSWORD to whatever you want the admin login to be

python app.py
```

Visit `http://localhost:5000`.

- **Without a `GROQ_API_KEY`**, the chatbot still works — it falls back to
  returning the raw verified knowledge-base context it retrieved, so you can
  demo retrieval end-to-end for free before wiring up an API key.
- **With a `GROQ_API_KEY`** set, `/api/chat` calls Groq's free-tier LLM to
  turn that retrieved context into a natural, grounded answer.
- Visit `http://localhost:5000/admin` and log in with `ADMIN_EMAIL` /
  `ADMIN_PASSWORD` from `.env` to see the aggregated analytics dashboard.

## AI Health Claim Fact-Checker (`claim_checker.py`)

`/api/misinformation` no longer just fuzzy-matches text against a static myth
table. It runs a real evidence-grounded pipeline:

```
claim -> safety filter (app.py, before this module runs)
      -> validate_claim / normalize_claim
      -> extract_claims (Groq understands wording, does NOT judge truth)
      -> local fast-path lookup (existing myth/fact table, safety.py)
      -> generate_search_queries -> search via a pluggable provider (trusted-domain filtered)
      -> filter_sources / collect_evidence (dedup, tiered, capped)
      -> analyze_evidence (Groq, structured JSON, evidence-grounded)
      -> cross_check_result (second pass for high-risk / uncertain verdicts)
      -> confidence adjustment -> cited verdict
```

**Verdicts:** `SUPPORTED`, `MOSTLY_SUPPORTED`, `MISLEADING`, `UNSUPPORTED`,
`INSUFFICIENT_EVIDENCE` — never a bare TRUE/FALSE. Confidence (0–1) reflects
confidence in the *verdict*, not that the claim is true, and gets capped
automatically when evidence is weak, conflicting, or comes from too few
trusted (Tier 1/2) sources.

**Response statuses:**

| `status` | Meaning |
|---|---|
| `analyzed` | Full pipeline ran; `verdict`, `confidence`, `sources`, etc. are populated |
| `local_verified` | Live search is disabled (`SEARCH_PROVIDER=none`); matched the local myth table only |
| `evidence_unavailable` | No usable evidence found anywhere — **never** guessed from memory |
| `ai_unavailable` | Evidence was found but the Groq analysis step failed/returned invalid JSON — raw sources are still shown |
| `safety_override` | The claim tripped the emergency/crisis safety filter; routed there instead |
| `invalid` / `rate_limited` / `error` | Bad input, too many requests, or an unexpected failure |

### Search providers (no Tavily dependency)

Web search is pluggable via `SEARCH_PROVIDER` in `.env` (`claim_checker.py`
implements a small `SearchProvider` interface, so adding another one later is
a ~20-line class). Free-tier landscape as of mid/late 2026:

| Provider | `SEARCH_PROVIDER` value | Free tier | Card required? | Notes |
|---|---|---|---|---|
| **Serper** (serper.dev) | `serper` | 2,500 queries | No | One-time allowance, not recurring, but goes a long way for a prototype. Real Google results. **Recommended default if you want a key.** |
| **SerpApi** (serpapi.com) | `serpapi` | 250 queries/month | No | Smaller but recurring every month — better for a long-running demo. |
| **Google Programmable Search** | `google_cse` | 100 queries/day | No | Official Google API, recurring daily. Needs both an API key *and* a Search Engine ID (`cx`) configured to search the whole web (not just specific sites) at https://programmablesearchengine.google.com. |
| **DuckDuckGo Instant Answer** | `duckduckgo` (also the automatic fallback) | Unlimited, no signup at all | No | **Zero-config default** — the app uses this automatically if no other key is set, so the fact-checker works out of the box with zero setup. Meaningfully weaker: it only returns results for topics DuckDuckGo recognizes as an "instant answer" entity, not general web search, so coverage is thin for specific or oddly-phrased claims. |
| *(disabled)* | `none` | — | — | Fact-checker runs local-KB-only, never touches the network. |

Leave `SEARCH_PROVIDER=auto` (the default) to have it pick the best option
it has a key for, in the order above, falling back to DuckDuckGo if nothing
is configured. Brave Search and Bing's API were deliberately left out —
Brave now requires a card at signup and Bing's Search API was retired by
Microsoft in August 2025.

Without any provider set up beyond the automatic DuckDuckGo fallback, the
checker still works — it just won't silently fall back to "ask the LLM from
memory and call it verified" if DuckDuckGo comes up empty; it returns
`evidence_unavailable` instead.

**Safety and integrity guarantees:**
- Retrieved web content is wrapped in `<EVIDENCE>` blocks and explicitly
  labelled untrusted/non-instructional to the model, so a malicious page
  can't inject instructions into the analysis.
- Every URL in the final `sources` list comes from the search provider's
  actual results — the model can only reference evidence by `source_id`
  (E1, E2, ...); it can never invent a citation URL.
- Absolute-wording claims ("always", "cures", "100%", "guaranteed") get
  extra scrutiny and can't reach `SUPPORTED` on weak evidence.
- High-risk topics (cancer, pregnancy, children, medication changes,
  vaccines, overdose, etc.) automatically trigger a second, skeptical
  verification pass before the verdict is finalized.
- Emergency/crisis wording in a claim is intercepted by the existing safety
  layer in `app.py` **before** this module ever runs, and that decision

  can't be overridden by the fact-checker.
- Results are cached in-memory per normalized claim (`FACT_CHECK_CACHE_TTL`,
  default 6h) and a small per-IP rate limiter
  (`FACT_CHECK_RATE_LIMIT_PER_MIN`, default 6/min) protects the endpoint
  from being used to fire unlimited search + LLM calls.

## Notable design decisions / what's simplified for a prototype

- **RAG uses TF-IDF, not embeddings + FAISS/Chroma.** For a ~10-disease
  knowledge base this retrieves accurately, runs offline, and needs no paid
  embeddings API — but the retrieval interface (`rag.retrieve(query)`) is
  written so it could be swapped for a real vector DB later without touching
  the chat pipeline.
- **Voice input/output, full multilingual translation of the UI shell, and
  true ML-based intent classification are not implemented** — the blueprint
  marks these as optional/"nice to have," and the prototype focuses on the
  "must have" list (chatbot, RAG, safety layer, non-diagnostic risk guidance,
  clean UI) plus the "should have" items (multilingual chat responses,
  misinformation checker, source display, disease library).
- **Emergency/crisis/unsafe detection is regex/keyword-based**, not an ML
  classifier — deliberately, so it's fast, free, fully auditable, and cannot
  be bypassed by adversarial prompting of the LLM (it runs *before* the LLM
  is called).
- **Analytics events store no free-text or user identifiers** — only
  category, disease topic, language, risk level, and guest/registered flag —
  so the admin dashboard stays "anonymized and aggregated," as the blueprint
  requires.

## Security notes for going beyond a hackathon prototype

- Rotate `SECRET_KEY` and `ADMIN_PASSWORD` before any real deployment; the
  values in `.env` are prototype placeholders only.
- Add rate limiting and CSRF protection before exposing this publicly.
- Consider a proper vector DB (FAISS/Chroma) and a larger, clinician-reviewed
  knowledge base before treating any output as more than an awareness demo.
