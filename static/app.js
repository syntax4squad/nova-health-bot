const chatWindow = document.getElementById('chatWindow');
const chatInput = document.getElementById('chatInput');
const sendBtn = document.getElementById('sendBtn');
const languageSelect = document.getElementById('languageSelect');

let currentConversationId = null;

// ---------------------------------------------------------------------
// View switching
// ---------------------------------------------------------------------
const views = {
  chat: document.getElementById('viewChat'),
  risk: document.getElementById('viewRisk'),
  misinfo: document.getElementById('viewMisinfo'),
  diseases: document.getElementById('viewDiseases'),
};
function showView(name) {
  Object.values(views).forEach(v => v.style.display = 'none');
  views[name].style.display = 'block';
}
document.getElementById('navRisk')?.addEventListener('click', () => showView('risk'));
document.getElementById('navMisinfo')?.addEventListener('click', () => showView('misinfo'));
document.getElementById('navDiseases')?.addEventListener('click', () => { showView('diseases'); loadDiseases(); });

document.querySelectorAll('.quick-btn[data-q]').forEach(btn => {
  btn.addEventListener('click', () => {
    showView('chat');
    chatInput.value = btn.dataset.q;
    sendMessage();
  });
});

// ---------------------------------------------------------------------
// Chat
// ---------------------------------------------------------------------
function appendMessage(role, text, riskLevel, sources) {
  const div = document.createElement('div');
  div.className = `msg ${role}` + (riskLevel ? ` risk-${riskLevel}` : '');
  div.innerHTML = DOMPurify.sanitize(marked.parse(text));

  if (sources && sources.length) {
    const details = document.createElement('details');
    details.className = 'sources';
    const summary = document.createElement('summary');
    summary.textContent = 'View verified information';
    details.appendChild(summary);
    const ul = document.createElement('ul');
    sources.forEach(s => {
      const li = document.createElement('li');
      li.textContent = `${s.disease} — ${s.source} (last updated ${s.last_updated})`;
      ul.appendChild(li);
    });
    details.appendChild(ul);
    div.appendChild(details);
  }

  chatWindow.appendChild(div);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

async function sendMessage() {
  const message = chatInput.value.trim();
  if (!message) return;
  appendMessage('user', message);
  chatInput.value = '';
  sendBtn.disabled = true;

  const thinking = document.createElement('div');
  thinking.className = 'msg assistant';
  thinking.textContent = 'Thinking...';
  chatWindow.appendChild(thinking);
  chatWindow.scrollTop = chatWindow.scrollHeight;

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        language: languageSelect.value,
        conversation_id: currentConversationId,
      }),
    });
    const data = await res.json();
    thinking.remove();
    appendMessage('assistant', data.answer, data.risk_level, data.sources);
    if (data.conversation) {
      currentConversationId = data.conversation.id;
      loadConversations();
    }
  } catch (e) {
    thinking.remove();
    appendMessage('system', 'Something went wrong reaching the server. Please try again.');
  } finally {
    sendBtn.disabled = false;
  }
}

sendBtn.addEventListener('click', sendMessage);
chatInput.addEventListener('keydown', e => { if (e.key === 'Enter') sendMessage(); });

// ---------------------------------------------------------------------
// Conversation history (registered users)
// ---------------------------------------------------------------------
async function loadConversations() {
  const list = document.getElementById('convoList');
  if (!list) return;
  const res = await fetch('/api/conversations');
  if (!res.ok) return;
  const data = await res.json();
  list.innerHTML = '';
  data.conversations.forEach(c => {
    const el = document.createElement('div');
    el.className = 'convo-item' + (c.id === currentConversationId ? ' active' : '');
    el.textContent = c.title || 'Conversation';
    el.addEventListener('click', () => openConversation(c.id));
    list.appendChild(el);
  });
}

async function openConversation(id) {
  const res = await fetch(`/api/conversations/${id}`);
  if (!res.ok) return;
  const data = await res.json();
  currentConversationId = id;
  chatWindow.innerHTML = '';
  data.conversation.messages.forEach(m => appendMessage(m.role, m.content, m.risk_level));
  showView('chat');
  loadConversations();
}

document.getElementById('newConvoBtn')?.addEventListener('click', async () => {
  const res = await fetch('/api/conversations', { method: 'POST' });
  const data = await res.json();
  currentConversationId = data.conversation.id;
  chatWindow.innerHTML = '';
  appendMessage('assistant', "New conversation started. What would you like to know?");
  loadConversations();
});

if (window.CURRENT_USER) loadConversations();

// ---------------------------------------------------------------------
// Risk assessment
// ---------------------------------------------------------------------
let selectedSymptoms = new Set();
let selectedDuration = '';

document.querySelectorAll('.symptom-chip').forEach(chip => {
  chip.addEventListener('click', () => {
    chip.classList.toggle('selected');
    const s = chip.dataset.symptom;
    if (selectedSymptoms.has(s)) selectedSymptoms.delete(s); else selectedSymptoms.add(s);
  });
});
document.querySelectorAll('.duration-chip').forEach(chip => {
  chip.addEventListener('click', () => {
    document.querySelectorAll('.duration-chip').forEach(c => c.classList.remove('selected'));
    chip.classList.add('selected');
    selectedDuration = chip.dataset.duration;
  });
});

document.getElementById('assessBtn')?.addEventListener('click', async () => {
  const resultDiv = document.getElementById('riskResult');
  resultDiv.innerHTML = '';
  if (selectedSymptoms.size === 0) {
    resultDiv.innerHTML = '<p style="color:var(--red)">Select at least one symptom.</p>';
    return;
  }
  const res = await fetch('/api/risk-assessment', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      symptoms: Array.from(selectedSymptoms),
      duration: selectedDuration,
      language: languageSelect.value,
    }),
  });
  const data = await res.json();
  const labelMap = { RED: 'RED — SEEK IMMEDIATE PROFESSIONAL HELP', YELLOW: 'YELLOW — NEEDS ATTENTION', GREEN: 'GREEN — GENERAL AWARENESS' };
  resultDiv.innerHTML = `<div class="risk-result ${data.level}">${labelMap[data.level]}<div style="font-weight:400; margin-top:8px;">${data.message}</div></div>`;
});

// ---------------------------------------------------------------------
// AI Health Claim Fact-Checker
// ---------------------------------------------------------------------

const VERDICT_META = {
  SUPPORTED:             { label: 'SUPPORTED',             cls: 'verdict-supported' },
  MOSTLY_SUPPORTED:      { label: 'MOSTLY SUPPORTED',       cls: 'verdict-mostly' },
  MISLEADING:            { label: 'MISLEADING',             cls: 'verdict-misleading' },
  UNSUPPORTED:           { label: 'UNSUPPORTED',            cls: 'verdict-unsupported' },
  INSUFFICIENT_EVIDENCE: { label: 'INSUFFICIENT EVIDENCE',  cls: 'verdict-insufficient' },
};

// Build a safe, https-only external link. Never trust raw AI/source text as HTML.
function buildSourceLink(url, label) {
  const a = document.createElement('a');
  a.textContent = label || url;
  if (typeof url === 'string' && /^https:\/\//i.test(url)) {
    a.href = url;
    a.target = '_blank';
    a.rel = 'noopener noreferrer';
  } else {
    a.removeAttribute('href');
    a.style.cursor = 'default';
    a.style.textDecoration = 'none';
  }
  return a;
}

function el(tag, opts = {}) {
  const node = document.createElement(tag);
  if (opts.className) node.className = opts.className;
  if (opts.text !== undefined) node.textContent = opts.text;
  return node;
}

function renderClaimCard(container, data) {
  container.innerHTML = '';
  const card = el('div', { className: 'claim-card' });

  // --- Non-analyzed statuses: render a plain, honest message, no verdict badge ---
  if (data.status !== 'analyzed') {
    const toneClass = {
      invalid: 'claim-note-warn',
      rate_limited: 'claim-note-warn',
      safety_override: 'claim-note-warn',
      evidence_unavailable: 'claim-note-muted',
      ai_unavailable: 'claim-note-muted',
      error: 'claim-note-warn',
      local_verified: 'claim-note-info',
    }[data.status] || 'claim-note-muted';

    if (data.status === 'local_verified') {
      renderAnalyzedLikeCard(card, data, true);
    } else {
      const note = el('div', { className: `claim-note ${toneClass}` });
      note.appendChild(el('p', { text: data.message || 'Unable to check this claim right now.' }));
      if (Array.isArray(data.sources) && data.sources.length) {
        const srcTitle = el('p', { text: 'Sources found (not yet verified):' });
        srcTitle.style.fontWeight = '600';
        srcTitle.style.marginTop = '10px';
        note.appendChild(srcTitle);
        const list = el('ul');
        data.sources.forEach(s => {
          const li = el('li');
          li.appendChild(buildSourceLink(s.url, `${s.source_name || s.title || 'Source'}${s.title ? ' — ' + s.title : ''}`));
          list.appendChild(li);
        });
        note.appendChild(list);
      }
      card.appendChild(note);
    }
    container.appendChild(card);
    return;
  }

  renderAnalyzedLikeCard(card, data, false);
  container.appendChild(card);
}

function renderAnalyzedLikeCard(card, data, isLocalOnly) {
  const meta = VERDICT_META[data.verdict] || { label: data.verdict || 'UNKNOWN', cls: 'verdict-insufficient' };

  const badgeRow = el('div', { className: 'verdict-row' });
  const badge = el('span', { className: `verdict-badge ${meta.cls}`, text: meta.label });
  badgeRow.appendChild(badge);
  if (typeof data.confidence === 'number') {
    const conf = el('span', { className: 'confidence-pill', text: `${Math.round(data.confidence * 100)}% confidence` });
    badgeRow.appendChild(conf);
  }
  if (isLocalOnly) {
    badgeRow.appendChild(el('span', { className: 'source-type-pill', text: 'Local knowledge base' }));
  }
  if (data.high_risk_claim) {
    badgeRow.appendChild(el('span', { className: 'source-type-pill high-risk-pill', text: '⚠ High-risk topic' }));
  }
  card.appendChild(badgeRow);

  const claimBlock = el('div', { className: 'claim-block' });
  claimBlock.appendChild(el('h5', { text: 'Claim' }));
  claimBlock.appendChild(el('p', { className: 'claim-text', text: data.claim || '' }));
  card.appendChild(claimBlock);

  if (data.short_answer) {
    const ansBlock = el('div', { className: 'claim-block' });
    ansBlock.appendChild(el('h5', { text: 'AI assessment' }));
    ansBlock.appendChild(el('p', { text: data.short_answer }));
    card.appendChild(ansBlock);
  }

  if (data.explanation) {
    const expBlock = el('div', { className: 'claim-block' });
    expBlock.appendChild(el('h5', { text: 'Explanation' }));
    expBlock.appendChild(el('p', { text: data.explanation }));
    card.appendChild(expBlock);
  }

  if (data.evidence_strength || data.evidence_consistency) {
    const strengthRow = el('div', { className: 'evidence-meta-row' });
    if (data.evidence_strength) {
      strengthRow.appendChild(el('span', { className: 'meta-chip', text: `Evidence strength: ${data.evidence_strength}` }));
    }
    if (data.evidence_consistency) {
      strengthRow.appendChild(el('span', { className: 'meta-chip', text: `Consistency: ${data.evidence_consistency}` }));
    }
    card.appendChild(strengthRow);
  }

  if (Array.isArray(data.key_points) && data.key_points.length) {
    const kpBlock = el('div', { className: 'claim-block' });
    kpBlock.appendChild(el('h5', { text: 'Key findings' }));
    const ul = el('ul');
    data.key_points.forEach(p => ul.appendChild(el('li', { text: p })));
    kpBlock.appendChild(ul);
    card.appendChild(kpBlock);
  }

  if (Array.isArray(data.sources) && data.sources.length) {
    const srcBlock = el('div', { className: 'claim-block' });
    srcBlock.appendChild(el('h5', { text: 'Sources' }));
    const ul = el('ul', { className: 'source-list' });
    data.sources.forEach(s => {
      const li = el('li');
      const label = s.title ? `${s.source_name || 'Source'} — ${s.title}` : (s.source_name || 'Source');
      li.appendChild(buildSourceLink(s.url, label));
      ul.appendChild(li);
    });
    srcBlock.appendChild(ul);
    card.appendChild(srcBlock);
  }

  if (data.checked_at) {
    const checkedEl = el('p', { className: 'checked-at', text: `Checked: ${new Date(data.checked_at).toLocaleString()}` });
    card.appendChild(checkedEl);
  }

  const disclaimer = el('p', { className: 'claim-disclaimer', text: data.medical_disclaimer || '' });
  card.appendChild(disclaimer);
}

let claimCheckInFlight = false;

async function runClaimCheck() {
  if (claimCheckInFlight) return; // prevent duplicate simultaneous requests
  const input = document.getElementById('claimInput');
  const btn = document.getElementById('checkClaimBtn');
  const claim = input.value.trim();
  const resultDiv = document.getElementById('claimResult');
  if (!claim) return;

  claimCheckInFlight = true;
  btn.disabled = true;
  const originalLabel = btn.textContent;
  btn.textContent = 'Checking evidence...';
  resultDiv.innerHTML = '<div class="claim-loading">Searching trusted medical sources and analyzing evidence…</div>';

  try {
    const res = await fetch('/api/misinformation', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ claim, language: languageSelect.value }),
    });
    let data;
    try {
      data = await res.json();
    } catch {
      data = { status: 'error', message: 'The server returned an unexpected response.' };
    }
    if (!res.ok && !data.status) {
      data = { status: 'error', message: data.message || `Request failed (${res.status}).` };
    }
    renderClaimCard(resultDiv, data);
  } catch (e) {
    renderClaimCard(resultDiv, { status: 'error', message: 'Could not reach the server. Please try again.' });
  } finally {
    claimCheckInFlight = false;
    btn.disabled = false;
    btn.textContent = originalLabel;
  }
}

document.getElementById('checkClaimBtn')?.addEventListener('click', runClaimCheck);
document.getElementById('claimInput')?.addEventListener('keydown', e => {
  if (e.key === 'Enter') runClaimCheck();
});

// ---------------------------------------------------------------------
// Disease library
// ---------------------------------------------------------------------
async function loadDiseases() {
  const grid = document.getElementById('diseaseGrid');
  if (grid.dataset.loaded) return;
  const res = await fetch('/api/diseases');
  const data = await res.json();
  grid.innerHTML = '';
  data.diseases.forEach(d => {
    const card = document.createElement('div');
    card.className = 'disease-card';
    card.innerHTML = `<h4>${d.name}</h4><span style="color:var(--muted); font-size:0.8rem;">View details →</span>`;
    card.addEventListener('click', () => loadDiseaseDetail(d.key));
    grid.appendChild(card);
  });
  grid.dataset.loaded = '1';
}

async function loadDiseaseDetail(key) {
  const res = await fetch(`/api/diseases/${key}`);
  const data = await res.json();
  const d = data.disease;
  const detail = document.getElementById('diseaseDetail');
  detail.innerHTML = `
    <h3>${d.name}</h3>
    <div class="field-block"><h4>Overview</h4><p>${d.overview}</p></div>
    <div class="field-block"><h4>Common symptoms</h4><ul>${d.symptoms.map(s=>`<li>${s}</li>`).join('')}</ul></div>
    <div class="field-block"><h4>Warning signs</h4><ul>${d.warning_signs.map(s=>`<li>${s}</li>`).join('')}</ul></div>
    <div class="field-block"><h4>Transmission</h4><p>${d.transmission}</p></div>
    <div class="field-block"><h4>Prevention</h4><ul>${d.prevention.map(s=>`<li>${s}</li>`).join('')}</ul></div>
    <div class="field-block"><h4>Myths & facts</h4><ul>${d.myths_facts.map(m=>`<li><strong>Myth:</strong> ${m.myth}<br><strong>Fact:</strong> ${m.fact}</li>`).join('')}</ul></div>
    <div class="field-block"><h4>When to seek care</h4><p>${d.when_to_seek_care}</p></div>
    <div class="field-block"><h4>Source</h4><p style="color:var(--muted); font-size:0.85rem;">${d.source} — last updated ${d.last_updated}</p></div>
  `;
  detail.scrollIntoView({ behavior: 'smooth' });
}

// ---------------------------------------------------------------------
// Logout
// ---------------------------------------------------------------------
document.getElementById('logoutBtn')?.addEventListener('click', async () => {
  await fetch('/api/auth/logout', { method: 'POST' });
  window.location.href = '/';
});
