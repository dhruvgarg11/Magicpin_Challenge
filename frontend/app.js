const scenarioList = document.querySelector('#scenario-list');
const searchInput = document.querySelector('#scenario-search');
const apiStatus = document.querySelector('#api-status');
const previewTitle = document.querySelector('#preview-title');
const messageBody = document.querySelector('#message-body');
const copyButton = document.querySelector('#copy-button');
const contextToggle = document.querySelector('#context-toggle');
const contextJson = document.querySelector('#context-json');
const contextSummary = document.querySelector('#context-summary');
const replyResult = document.querySelector('#reply-result');

let scenarios = [];
let selectedId = null;
let activeCategory = 'all';
let selectedResult = null;

const titleCase = (value) => value
  .replaceAll('_', ' ')
  .replace(/\b\w/g, (letter) => letter.toUpperCase());

const categoryClasses = {
  restaurants: 'food',
  salons: 'salon',
  gyms: 'gym',
  dentists: 'dentist',
  pharmacies: 'pharmacy',
};

function setApiStatus(online) {
  apiStatus.className = `api-indicator ${online ? 'online' : 'offline'}`;
  apiStatus.innerHTML = `<i></i> ${online ? 'Engine connected' : 'Engine offline'}`;
}

function renderScenarios() {
  const query = searchInput.value.trim().toLowerCase();
  const visible = scenarios.filter((item) => {
    const matchesCategory = activeCategory === 'all' || item.category === activeCategory;
    const searchable = `${item.merchant_name} ${item.kind} ${item.category} ${item.city} ${item.test_id}`.toLowerCase();
    return matchesCategory && searchable.includes(query);
  });
  document.querySelector('#result-count').textContent = visible.length;
  scenarioList.replaceChildren();

  if (!visible.length) {
    const empty = document.createElement('div');
    empty.className = 'empty-list';
    empty.textContent = 'No scenarios match your search.';
    scenarioList.append(empty);
    return;
  }

  for (const item of visible) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = `scenario-option${item.test_id === selectedId ? ' selected' : ''}`;
    button.setAttribute('role', 'option');
    button.setAttribute('aria-selected', String(item.test_id === selectedId));
    const icon = document.createElement('span');
    icon.className = `scenario-icon ${categoryClasses[item.category] || ''}`;
    icon.textContent = item.category.slice(0, 1).toUpperCase();
    const copy = document.createElement('span');
    copy.className = 'scenario-copy';
    const name = document.createElement('strong');
    name.textContent = item.merchant_name;
    const meta = document.createElement('small');
    meta.textContent = `${titleCase(item.kind)} · ${item.city}`;
    copy.append(name, meta);
    const urgency = document.createElement('span');
    urgency.className = 'scenario-urgency';
    urgency.textContent = item.test_id;
    button.append(icon, copy, urgency);
    button.addEventListener('click', () => selectScenario(item.test_id));
    scenarioList.append(button);
  }
}

function showMessage(message) {
  messageBody.replaceChildren();
  messageBody.append(document.createTextNode(message.body || 'No message was generated.'));
  const time = document.createElement('span');
  time.className = 'message-time';
  time.innerHTML = 'now <b>✓✓</b>';
  messageBody.append(time);
}

async function selectScenario(testId) {
  selectedId = testId;
  const scenario = scenarios.find((item) => item.test_id === testId);
  renderScenarios();
  previewTitle.textContent = `${scenario.test_id} · ${titleCase(scenario.kind)}`;
  document.querySelector('#merchant-name').textContent = scenario.merchant_name;
  document.querySelector('#merchant-meta').textContent = `${scenario.category.replaceAll('_', ' ')} · ${scenario.city} · ${scenario.owner_name}`;
  document.querySelector('#merchant-avatar').textContent = scenario.merchant_name.trim().charAt(0).toUpperCase();
  document.querySelector('#message-status-text').textContent = 'Generating from project data';
  document.querySelector('.message-status').classList.remove('ready');
  copyButton.disabled = true;
  contextToggle.disabled = true;
  contextToggle.textContent = 'View data ↗';
  contextJson.hidden = true;

  try {
    const response = await fetch('/v1/demo/compose', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ test_id: testId }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Could not compose message');
    selectedResult = result;
    showMessage(result.message);
    document.querySelector('#rationale-text').textContent = result.message.rationale || 'No rationale was returned.';
    const tags = [scenario.category, scenario.kind, scenario.customer_name ? 'personalized' : 'merchant context'];
    const tagContainer = document.querySelector('#reason-tags');
    tagContainer.replaceChildren(...tags.map((text) => {
      const tag = document.createElement('span');
      tag.className = 'reason-tag';
      tag.textContent = text.replaceAll('_', ' ');
      return tag;
    }));
    const owner = scenario.owner_name ? `Owner: ${scenario.owner_name}` : 'Owner context available';
    const customer = scenario.customer_name ? ` · Customer: ${scenario.customer_name}` : ' · No customer record';
    contextSummary.textContent = `${scenario.merchant_name} · ${scenario.city} · ${titleCase(scenario.kind)} · ${owner}${customer}`;
    contextJson.textContent = JSON.stringify({
      category: result.merchant.category_slug,
      merchant: result.merchant,
      trigger: result.trigger,
      customer: result.customer,
    }, null, 2);
    copyButton.disabled = false;
    contextToggle.disabled = false;
    document.querySelector('#message-status-text').textContent = `Ready · ${result.message.send_as || 'vera'}`;
    document.querySelector('.message-status').classList.add('ready');
    setApiStatus(true);
  } catch (error) {
    showMessage({ body: error.message });
    document.querySelector('#message-status-text').textContent = 'Could not reach the message engine';
    setApiStatus(false);
  }
}

async function loadScenarios() {
  try {
    const response = await fetch('/v1/demo/scenarios');
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Scenario library unavailable');
    scenarios = data.scenarios;
    document.querySelector('#stat-scenarios').textContent = String(scenarios.length).padStart(2, '0');
    document.querySelector('#nav-count').textContent = scenarios.length;
    document.querySelector('#stat-customers').textContent = `${scenarios.filter((item) => item.customer_id).length} / ${scenarios.length}`;
    setApiStatus(true);
    renderScenarios();
    if (scenarios.length) selectScenario(scenarios[0].test_id);
  } catch (error) {
    scenarioList.innerHTML = '';
    const empty = document.createElement('div');
    empty.className = 'empty-list';
    empty.textContent = error.message;
    scenarioList.append(empty);
    setApiStatus(false);
  }
}

document.querySelectorAll('.filter-chip').forEach((button) => {
  button.addEventListener('click', () => {
    activeCategory = button.dataset.category;
    document.querySelectorAll('.filter-chip').forEach((chip) => chip.classList.toggle('selected', chip === button));
    renderScenarios();
  });
});

searchInput.addEventListener('input', renderScenarios);
document.addEventListener('keydown', (event) => {
  if (event.key === '/' && document.activeElement !== searchInput && !['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) {
    event.preventDefault();
    searchInput.focus();
  }
  if (event.key === 'Escape' && document.activeElement === searchInput) searchInput.blur();
});

document.querySelector('#refresh-button').addEventListener('click', () => {
  if (selectedId) selectScenario(selectedId);
});

copyButton.addEventListener('click', async () => {
  if (!selectedResult) return;
  try {
    await navigator.clipboard.writeText(selectedResult.message.body);
    copyButton.innerHTML = '<span>✓</span> Copied';
    setTimeout(() => { copyButton.innerHTML = '<span>▢</span> Copy message'; }, 1400);
  } catch {
    copyButton.innerHTML = '<span>!</span> Clipboard unavailable';
  }
});

contextToggle.addEventListener('click', () => {
  contextJson.hidden = !contextJson.hidden;
  contextToggle.innerHTML = contextJson.hidden ? 'View data <span>↗</span>' : 'Hide data <span>↙</span>';
});

document.querySelector('#reply-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const input = document.querySelector('#reply-input');
  const message = input.value.trim();
  if (!message) {
    input.focus();
    return;
  }
  const submit = document.querySelector('#reply-submit');
  submit.disabled = true;
  replyResult.className = 'reply-result';
  replyResult.lastElementChild.textContent = 'Checking reply…';
  try {
    const response = await fetch('/v1/reply', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
    });
    const result = await response.json();
    const copy = {
      end: ['warning', 'End conversation · Vera will stop messaging.'],
      send: ['success', `Send response · “${result.body}”`],
      wait: ['neutral', `Wait ${result.wait_seconds} seconds · No automatic reply yet.`],
    }[result.action] || ['neutral', 'No action returned.'];
    replyResult.className = `reply-result ${copy[0]}`;
    replyResult.lastElementChild.textContent = copy[1];
  } catch {
    replyResult.className = 'reply-result warning';
    replyResult.lastElementChild.textContent = 'Could not reach the reply endpoint.';
  } finally {
    submit.disabled = false;
  }
});

document.querySelector('#today-label').textContent = new Intl.DateTimeFormat('en', { weekday: 'short', month: 'short', day: 'numeric' }).format(new Date()).toUpperCase();
loadScenarios();