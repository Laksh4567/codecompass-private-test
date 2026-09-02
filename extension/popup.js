// CodeCompass - popup.js
const API_URL = 'http://localhost:5000';
let currentRepoUrl = null;

const repoInfoEl = document.getElementById('repo-info');
const statusPillEl = document.getElementById('status-pill');
const emptyStateEl = document.getElementById('empty-state');
const chatEl = document.getElementById('chat');
const inputEl = document.getElementById('input');
const sendBtn = document.getElementById('send-btn');

function getGitHubRepoUrl(tabUrl) {
  const match = tabUrl.match(/^https:\/\/github\.com\/([^\/]+)\/([^\/]+)/);
  if (!match) return null;
  const reserved = ['settings', 'notifications', 'marketplace', 'explore', 'topics', 'sponsors'];
  if (reserved.includes(match[1])) return null;
  return { url: `https://github.com/${match[1]}/${match[2]}`, label: `${match[1]}/${match[2]}` };
}

function setStatus(text, variant) {
  statusPillEl.textContent = text;
  statusPillEl.className = 'status-pill' + (variant ? ' ' + variant : '');
}

function showChat() {
  emptyStateEl.style.display = 'none';
  chatEl.classList.add('active');
}

// Turns "(see file.py, lines 10-20)" style citations into styled tags,
// and fenced code blocks into styled code boxes. Lightweight, not a full
// markdown renderer — matches what Gemini's answers typically contain.
function renderAssistantContent(text) {
  const container = document.createElement('div');

  // Split on fenced code blocks first
  const codeBlockRegex = /```[\w]*\n([\s\S]*?)```/g;
  let lastIndex = 0;
  let match;
  let hasCode = false;

  while ((match = codeBlockRegex.exec(text)) !== null) {
    hasCode = true;
    appendTextWithCitations(container, text.slice(lastIndex, match.index));
    const codeBox = document.createElement('div');
    codeBox.className = 'code-block';
    codeBox.textContent = match[1];
    container.appendChild(codeBox);
    lastIndex = codeBlockRegex.lastIndex;
  }
  appendTextWithCitations(container, text.slice(lastIndex));

  return container;
}

function appendTextWithCitations(container, text) {
  if (!text.trim()) return;
  const citationRegex = /\(see [^)]+\)/g;
  let lastIndex = 0;
  let match;
  const wrapper = document.createElement('span');

  while ((match = citationRegex.exec(text)) !== null) {
    wrapper.appendChild(document.createTextNode(text.slice(lastIndex, match.index)));
    const tag = document.createElement('span');
    tag.className = 'citation-tag';
    tag.textContent = match[0].replace(/^\(see /, '').replace(/\)$/, '');
    wrapper.appendChild(tag);
    lastIndex = citationRegex.lastIndex;
  }
  wrapper.appendChild(document.createTextNode(text.slice(lastIndex)));
  container.appendChild(wrapper);
}

function addUserMessage(text) {
  showChat();
  const div = document.createElement('div');
  div.className = 'msg-user';
  div.textContent = text;
  chatEl.appendChild(div);
  chatEl.scrollTop = chatEl.scrollHeight;
}

function addAssistantMessage(text, loading) {
  showChat();
  const div = document.createElement('div');
  div.className = 'msg-assistant' + (loading ? ' loading' : '');
  if (loading) {
    div.textContent = text;
  } else {
    div.appendChild(renderAssistantContent(text));
  }
  chatEl.appendChild(div);
  chatEl.scrollTop = chatEl.scrollHeight;
  return div;
}

async function init() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const repo = tab && tab.url ? getGitHubRepoUrl(tab.url) : null;

  if (!repo) {
    repoInfoEl.textContent = 'Not on a GitHub repo page';
    setStatus('N/A', 'error');
    sendBtn.disabled = true;
    return;
  }

  currentRepoUrl = repo.url;
  repoInfoEl.textContent = repo.label;
  setStatus('INDEXING', 'indexing');
  sendBtn.disabled = false;

  try {
    const res = await fetch(`${API_URL}/index`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ repo_url: currentRepoUrl })
    });
    const data = await res.json();

    if (data.status === 'indexed' || data.status === 'already_indexed') {
      setStatus('READY');
    } else if (data.status === 'no_content') {
      setStatus('NO CONTENT', 'error');
    } else {
      setStatus('READY');
    }
  } catch (err) {
    setStatus('OFFLINE', 'error');
  }
}

async function sendQuestion(question) {
  if (!question || !currentRepoUrl) return;

  inputEl.value = '';
  addUserMessage(question);
  sendBtn.disabled = true;

  const loadingMsg = addAssistantMessage('Thinking...', true);

  try {
    const res = await fetch(`${API_URL}/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, repo_url: currentRepoUrl })
    });
    const data = await res.json();
    loadingMsg.remove();
    addAssistantMessage(data.answer || data.error || 'No response.', false);
  } catch (err) {
    loadingMsg.remove();
    addAssistantMessage('Error: backend not reachable.', false);
  } finally {
    sendBtn.disabled = false;
  }
}

sendBtn.addEventListener('click', () => {
  const q = inputEl.value.trim();
  if (q) sendQuestion(q);
});

inputEl.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    const q = inputEl.value.trim();
    if (q) sendQuestion(q);
  }
});

document.querySelectorAll('.suggestion-card').forEach((card) => {
  card.addEventListener('click', () => {
    const q = card.getAttribute('data-question');
    sendQuestion(q);
  });
});

init();
