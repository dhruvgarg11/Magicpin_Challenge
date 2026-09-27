const $ = (selector) => document.querySelector(selector);
const numberFormat = new Intl.NumberFormat(undefined, { maximumFractionDigits: 1 });
const dateFormat = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' });

const apiBase = '';
let workspaceData = null;
let selectedMerchantId = null;
let workspaceRequest;
let toastTimer;
let scenarioRecords = [];
let activeScenarioId = null;
let scenarioRequestVersion = 0;

function apiUrl(path) {
  return `${apiBase}${path}`;
}

async function requestJson(path, options = {}) {
  const controller = new AbortController();
  const timeoutMs = options.timeoutMs || 8000;
  const externalSignal = options.signal;
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  const abortFromCaller = () => controller.abort(externalSignal.reason);
  externalSignal?.addEventListener('abort', abortFromCaller, { once: true });

  try {
    const response = await fetch(apiUrl(path), {
      ...options,
      signal: controller.signal,
      headers: { Accept: 'application/json', ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...options.headers },
    });
    let data;
    try {
      data = await response.json();
    } catch {
      throw new Error(`The service returned an unreadable response (${response.status}).`);
    }
    if (!response.ok) throw new Error(data.error || `Request failed (${response.status}).`);
    return data;
  } catch (error) {
    if (externalSignal?.aborted) throw error;
    if (controller.signal.aborted) throw new Error(`The API request timed out after ${Math.round(timeoutMs / 1000)} seconds.`);
    throw new Error(`Could not reach the API: ${error.message}`);
  } finally {
    clearTimeout(timeout);
    externalSignal?.removeEventListener('abort', abortFromCaller);
  }
}

function setApiStatus(state, label) {
  const status = $('#api-status');
  status.className = `api-indicator ${state}`;
  status.querySelector('span').textContent = label;
  $('#sidebar-status').textContent = state === 'online' ? 'Bot online' : state === 'offline' ? 'Bot unavailable' : 'Checking status';
  $('#sidebar-status-dot').classList.toggle('offline', state === 'offline');
}

function toast(message, type = 'info') {
  const region = $('#toast-region');
  const item = document.createElement('div');
  item.className = `toast ${type}`;
  item.textContent = message;
  region.replaceChildren(item);
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => item.remove(), 4200);
}

function text(element, value, empty = '—') {
  element.textContent = value === null || value === undefined || value === '' ? empty : value;
}

function formatNumber(value) {
  return typeof value === 'number' ? numberFormat.format(value) : '—';
}

function formatPercent(value) {
  return typeof value === 'number' ? `${(value * 100).toFixed(value * 100 % 1 ? 1 : 0)}%` : '—';
}

function formatLabel(value) {
  return String(value || '').replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatTimestamp(value) {
  if (!value) return 'Time not recorded';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : dateFormat.format(date);
}

function make(tag, className, content) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (content !== undefined) element.textContent = content;
  return element;
}

function payloadFacts(payload = {}) {
  return Object.entries(payload)
    .filter(([key, value]) => !['placeholder', 'merchant_last_message'].includes(key) && value !== null && value !== '' && typeof value !== 'object')
    .slice(0, 3)
    .map(([key, value]) => `${formatLabel(key)}: ${typeof value === 'boolean' ? (value ? 'Yes' : 'No') : value}`);
}

function scenarioLabel(scenario) {
  return `${scenario.test_id} · ${scenario.merchant_name} · ${formatLabel(scenario.kind)}${scenario.city ? ` · ${scenario.city}` : ''}`;
}

function renderScenarioOptions() {
  const query = $('#scenario-search').value.trim().toLowerCase();
  const category = $('#scenario-category').value;
  const matching = scenarioRecords.filter((scenario) => {
    const searchable = `${scenario.test_id} ${scenario.merchant_name} ${scenario.kind} ${scenario.city} ${scenario.category}`.toLowerCase();
    return (category === 'all' || scenario.category === category) && searchable.includes(query);
  });
  const select = $('#scenario-select');
  select.replaceChildren();
  if (!matching.length) {
    select.append(new Option('No matching scenarios', ''));
    select.disabled = true;
    $('#scenario-feedback').hidden = false;
    $('#scenario-feedback').textContent = 'No challenge scenarios match these filters.';
    $('#scenario-result').hidden = true;
    return;
  }

  for (const scenario of matching) {
    const option = new Option(scenarioLabel(scenario), scenario.test_id);
    option.selected = scenario.test_id === activeScenarioId;
    select.append(option);
  }
  select.disabled = false;
  $('#scenario-total').textContent = `${matching.length} / ${scenarioRecords.length}`;
  if (!activeScenarioId || !matching.some((scenario) => scenario.test_id === activeScenarioId)) {
    activeScenarioId = matching[0].test_id;
    select.value = activeScenarioId;
    loadScenarioPreview(activeScenarioId);
  }
}

async function loadScenarioRecords() {
  const feedback = $('#scenario-feedback');
  feedback.hidden = false;
  feedback.className = 'scenario-feedback';
  feedback.replaceChildren(make('span', 'spinner'), document.createTextNode('Loading scenario records from the API'));
  $('#scenario-select').disabled = true;
  try {
    const data = await requestJson('/v1/demo/scenarios');
    scenarioRecords = Array.isArray(data.scenarios) ? data.scenarios : [];
    const categories = [...new Set(scenarioRecords.map((scenario) => scenario.category).filter(Boolean))].sort();
    const categorySelect = $('#scenario-category');
    categorySelect.replaceChildren(new Option('All categories', 'all'));
    for (const category of categories) categorySelect.append(new Option(formatLabel(category), category));
    if (!scenarioRecords.length) {
      feedback.className = 'scenario-feedback empty';
      feedback.textContent = 'No challenge scenarios are available from the API.';
      $('#scenario-total').textContent = '0';
      return;
    }
    feedback.hidden = true;
    renderScenarioOptions();
  } catch (error) {
    feedback.className = 'scenario-feedback error';
    const message = make('span', '', `Scenario records could not be loaded: ${error.message}`);
    const retry = make('button', 'scenario-retry', 'Retry');
    retry.type = 'button';
    retry.addEventListener('click', loadScenarioRecords);
    feedback.replaceChildren(message, retry);
    $('#scenario-total').textContent = 'Unavailable';
    $('#scenario-select').disabled = true;
  }
}

async function loadScenarioPreview(testId) {
  const version = ++scenarioRequestVersion;
  activeScenarioId = testId;
  const feedback = $('#scenario-feedback');
  feedback.hidden = false;
  feedback.className = 'scenario-feedback';
  feedback.replaceChildren(make('span', 'spinner'), document.createTextNode('Loading selected merchant and trigger context'));
  $('#scenario-result').hidden = true;
  $('#copy-preview').disabled = true;
  try {
    const result = await requestJson('/v1/demo/compose', {
      method: 'POST',
      body: JSON.stringify({ test_id: testId }),
    });
    if (version !== scenarioRequestVersion) return;
    const scenario = scenarioRecords.find((item) => item.test_id === testId);
    if (!scenario) throw new Error('The selected scenario is no longer available.');
    $('#preview-avatar').textContent = scenario.merchant_name.trim().charAt(0).toUpperCase();
    $('#preview-merchant').textContent = scenario.merchant_name;
    $('#preview-context-line').textContent = [scenario.category, scenario.city, scenario.customer_name && `Customer · ${scenario.customer_name}`].filter(Boolean).map(formatLabel).join(' · ');
    $('#preview-message').textContent = result.message?.body || 'No message body was returned.';
    $('#preview-cta').textContent = result.message?.cta ? formatLabel(result.message.cta) : 'No data available';
    $('#preview-send-as').textContent = result.message?.send_as ? formatLabel(result.message.send_as) : 'No data available';
    $('#preview-suppression').textContent = result.message?.suppression_key || 'No data available';
    $('#preview-rationale').textContent = result.message?.rationale || 'No rationale was returned for this scenario.';
    const context = {
      category: result.category,
      merchant: result.merchant,
      trigger: result.trigger,
      customer: result.customer,
    };
    const contextSummary = [
      result.category?.display_name || scenario.category,
      result.merchant?.identity?.name || scenario.merchant_name,
      formatLabel(result.trigger?.kind || scenario.kind),
      result.customer?.identity?.name || scenario.customer_name,
    ].filter(Boolean);
    $('#preview-context-summary').textContent = contextSummary.join(' · ');
    $('#preview-context-data').textContent = JSON.stringify(context, null, 2);
    $('#scenario-result').hidden = false;
    $('#copy-preview').disabled = !result.message?.body;
    feedback.hidden = true;
  } catch (error) {
    if (version !== scenarioRequestVersion) return;
    feedback.className = 'scenario-feedback error';
    feedback.textContent = `Message preview could not be loaded: ${error.message}`;
    $('#scenario-result').hidden = true;
  }
}

function renderMerchantOptions(merchants, selectedId) {
  const select = $('#merchant-select');
  select.replaceChildren();
  for (const merchant of merchants) {
    const option = make('option', '', `${merchant.name}${merchant.city ? ` · ${merchant.city}` : ''}`);
    option.value = merchant.merchant_id;
    option.selected = merchant.merchant_id === selectedId;
    select.append(option);
  }
  select.disabled = !merchants.length;
}

function renderMetrics(merchant) {
  const performance = merchant.performance || {};
  const windowDays = performance.window_days;
  const period = windowDays ? `Last ${windowDays} days` : 'Reporting period unavailable';
  const metrics = [
    ['views', 'views', performance.delta_7d?.views_pct],
    ['calls', 'calls', performance.delta_7d?.calls_pct],
    ['directions', 'directions', performance.delta_7d?.directions_pct],
    ['leads', 'leads', performance.delta_7d?.leads_pct],
  ];
  for (const [id, key, delta] of metrics) {
    const value = performance[key];
    text($(`#metric-${id}`), formatNumber(value), 'Not recorded');
    const footer = $(`#metric-${id}-foot`);
    if (typeof delta === 'number') {
      footer.replaceChildren(make('span', delta >= 0 ? 'trend positive' : 'trend negative', `${delta >= 0 ? '+' : ''}${formatPercent(delta)}`), document.createTextNode(` · ${period}`));
    } else {
      footer.textContent = period;
    }
  }
  const ctr = performance.ctr;
  $('#merchant-subtitle').textContent = [
    merchant.identity?.locality,
    merchant.identity?.city,
    merchant.category_slug ? formatLabel(merchant.category_slug) : null,
    typeof ctr === 'number' ? `${formatPercent(ctr)} profile CTR` : null,
  ].filter(Boolean).join(' · ') || 'Merchant profile and performance context';
}

function renderTriggers(triggers) {
  const list = $('#trigger-list');
  list.replaceChildren();
  $('#trigger-count').textContent = triggers.length;
  $('#insight-total').textContent = triggers.length;
  if (!triggers.length) {
    list.append(make('div', 'empty-state', 'No trigger data available yet.'));
    $('#trigger-footer').textContent = 'New merchant signals will appear here when available.';
    return;
  }

  for (const trigger of triggers.slice(0, 8)) {
    const row = make('article', 'trigger-item');
    const symbol = make('span', 'trigger-symbol', formatLabel(trigger.kind).slice(0, 1) || '•');
    const body = make('div', 'trigger-body');
    const titleRow = make('div', 'trigger-title-row');
    titleRow.append(make('h3', '', formatLabel(trigger.kind)));
    if (typeof trigger.urgency === 'number') titleRow.append(make('span', 'urgency-label', `Priority ${trigger.urgency}`));
    body.append(titleRow);
    const facts = payloadFacts(trigger.payload);
    if (facts.length) body.append(make('p', 'trigger-facts', facts.join(' · ')));
    if (trigger.customer?.identity?.name) body.append(make('span', 'trigger-customer', `Customer · ${trigger.customer.identity.name}`));
    const action = make('button', 'draft-button', 'Draft message');
    action.type = 'button';
    action.dataset.triggerId = trigger.id;
    action.addEventListener('click', () => draftTrigger(trigger));
    row.append(symbol, body, action);
    list.append(row);
  }
  $('#trigger-footer').textContent = triggers.length > 8 ? `Showing 8 of ${triggers.length} recorded triggers.` : `${triggers.length} recorded trigger${triggers.length === 1 ? '' : 's'} for this merchant.`;
}

function renderContext(data) {
  const merchant = data.merchant;
  const identity = merchant.identity || {};
  const category = data.category;
  const body = $('#merchant-context-body');
  body.replaceChildren();
  $('#verified-badge').hidden = !identity.verified;
  const sidebarCard = make('div', 'sidebar-context-card');
  sidebarCard.append(
    make('strong', '', identity.name || 'Merchant'),
    make('span', '', [category?.display_name, identity.locality, identity.city].filter(Boolean).join(' · ') || 'No category or location recorded.'),
  );
  $('#sidebar-context').replaceChildren(make('span', 'section-kicker', 'CURRENT CONTEXT'), sidebarCard);

  const details = make('div', 'profile-details');
  const fields = [
    ['Owner', identity.owner_first_name],
    ['Location', [identity.locality, identity.city].filter(Boolean).join(', ')],
    ['Category', category?.display_name || formatLabel(merchant.category_slug)],
    ['Membership', merchant.subscription?.plan],
  ];
  for (const [label, value] of fields) {
    const item = make('div', 'profile-field');
    item.append(make('span', 'profile-label', label), make('strong', '', value || 'Not recorded'));
    details.append(item);
  }
  body.append(details);

  if (category?.voice?.tone) {
    const tone = make('div', 'voice-context');
    tone.append(make('span', 'profile-label', 'CATEGORY VOICE'), make('strong', '', formatLabel(category.voice.tone)));
    body.append(tone);
  }
  if (Array.isArray(merchant.offers) && merchant.offers.length) {
    const offers = make('div', 'offer-context');
    offers.append(make('span', 'profile-label', 'RECORDED OFFERS'));
    const list = make('ul', 'offer-list');
    for (const offer of merchant.offers.slice(0, 3)) {
      const item = make('li', '', offer.title || 'Untitled offer');
      if (offer.status) item.append(make('span', 'offer-status', formatLabel(offer.status)));
      list.append(item);
    }
    offers.append(list);
    body.append(offers);
  }
  const signals = Array.isArray(merchant.signals) ? merchant.signals : [];
  if (signals.length) {
    const tags = make('div', 'signal-tags');
    for (const signal of signals) tags.append(make('span', 'signal-tag', formatLabel(signal)));
    body.append(tags);
  }
  if (!category && !identity.owner_first_name && !merchant.subscription && !merchant.offers?.length && !signals.length) {
    body.append(make('div', 'empty-state', 'No additional merchant context available.'));
  }
  $('#assistant-context').textContent = `${identity.name || 'Selected merchant'}${identity.city ? ` · ${identity.city}` : ''}`;
}

function renderActivity(entries) {
  const list = $('#activity-list');
  list.replaceChildren();
  $('#activity-total').textContent = entries.length;
  if (!entries.length) {
    list.append(make('div', 'empty-state', 'No conversation history available for this merchant.'));
    return;
  }
  for (const entry of entries.slice(0, 5)) {
    const row = make('article', 'activity-item');
    row.append(make('span', `activity-marker ${entry.from === 'vera' ? 'vera' : 'merchant'}`, entry.from === 'vera' ? 'V' : 'M'));
    const content = make('div', 'activity-copy');
    content.append(make('div', 'activity-meta', `${entry.from === 'vera' ? 'Vera' : formatLabel(entry.from || 'Merchant')} · ${formatTimestamp(entry.ts)}`));
    content.append(make('p', '', entry.body || 'No message text recorded.'));
    if (entry.engagement) content.append(make('span', 'engagement-tag', formatLabel(entry.engagement)));
    row.append(content);
    list.append(row);
  }
}

function renderRecordedMessages(entries) {
  const list = $('#generated-list');
  list.replaceChildren();
  $('#message-total').textContent = entries.length;
  if (!entries.length) {
    list.append(make('div', 'empty-state', 'No Vera messages are recorded in this merchant’s history yet.'));
    return;
  }
  for (const entry of entries.slice(0, 4)) {
    const item = make('article', 'generated-item');
    item.append(make('p', '', entry.body || 'No message text recorded.'), make('time', '', formatTimestamp(entry.ts)));
    list.append(item);
  }
}

function storedChat(merchantId) {
  try {
    const saved = JSON.parse(localStorage.getItem(`vera-chat:${merchantId}`) || '[]');
    return Array.isArray(saved) ? saved : [];
  } catch {
    return [];
  }
}

function saveChat() {
  if (!selectedMerchantId) return;
  try {
    localStorage.setItem(`vera-chat:${selectedMerchantId}`, JSON.stringify(chatMessages));
  } catch {
    toast('Chat history could not be saved in this browser.', 'error');
  }
}

let chatMessages = [];
let failedChatMessage = null;
let activeConversationId = null;
let chatEnded = false;

function newConversationId(merchantId) {
  const token = globalThis.crypto?.randomUUID?.() || `${Date.now()}_${Math.random().toString(36).slice(2)}`;
  return `web_${merchantId}_${token}`;
}

function conversationIdFor(merchantId, reset = false) {
  const key = `vera-conversation:${merchantId}`;
  try {
    if (!reset) {
      const current = localStorage.getItem(key);
      if (current) return current;
    }
    const conversationId = newConversationId(merchantId);
    localStorage.setItem(key, conversationId);
    return conversationId;
  } catch {
    return newConversationId(merchantId);
  }
}

function renderChat() {
  const history = $('#chat-history');
  history.replaceChildren();
  if (!chatMessages.length) {
    const empty = make('div', 'chat-empty');
    empty.append(make('span', 'chat-empty-mark', 'v.'), make('strong', '', 'Good to have you here.'), make('p', '', 'Ask about performance, offers, or what to focus on next.'));
    history.append(empty);
    return;
  }
  for (const message of chatMessages) {
    const item = make('article', `chat-message ${message.role}`);
    item.append(make('span', 'chat-sender', message.role === 'assistant' ? 'VERA' : 'YOU'));
    item.append(make('p', 'chat-text', message.body));
    if (message.cta) item.append(make('span', 'chat-cta', formatLabel(message.cta)));
    if (message.time) item.append(make('time', '', formatTimestamp(message.time)));
    history.append(item);
  }
  history.scrollTop = history.scrollHeight;
}

function addChatMessage(message) {
  chatMessages.push(message);
  saveChat();
  renderChat();
}

async function draftTrigger(trigger) {
  const button = [...document.querySelectorAll('.draft-button')].find((item) => item.dataset.triggerId === trigger.id);
  if (button) {
    button.disabled = true;
    button.textContent = 'Drafting…';
  }
  try {
    const result = await requestJson('/v1/compose', {
      method: 'POST',
      body: JSON.stringify({ merchant_id: selectedMerchantId, trigger_id: trigger.id, customer_id: trigger.customer_id || null }),
    });
    $('#draft-message').textContent = result.message.body;
    const details = [result.message.cta && `Action · ${formatLabel(result.message.cta)}`, result.message.send_as && `Voice · ${formatLabel(result.message.send_as)}`, result.message.rationale].filter(Boolean);
    $('#draft-details').replaceChildren(...details.map((item) => make('p', '', item)));
    $('#draft-dialog').showModal();
  } catch (error) {
    toast(`Could not draft this message: ${error.message}`, 'error');
  } finally {
    if (button) {
      button.disabled = false;
      button.textContent = 'Draft message';
    }
  }
}

async function loadWorkspace(merchantId) {
  workspaceRequest?.abort();
  workspaceRequest = new AbortController();
  const select = $('#merchant-select');
  select.disabled = true;
  $('#global-error').hidden = true;
  $('#trigger-list').replaceChildren(make('div', 'loading-state', 'Loading merchant signals…'));
  try {
    const query = merchantId ? `?merchant_id=${encodeURIComponent(merchantId)}` : '';
    const data = await requestJson(`/v1/workspace${query}`, { signal: workspaceRequest.signal });
    workspaceData = data;
    selectedMerchantId = data.merchant.merchant_id;
    const identity = data.merchant.identity || {};
    $('#merchant-heading').replaceChildren(document.createTextNode(identity.name || 'Merchant workspace'), make('span', 'heading-period', '.'));
    $('#breadcrumb-merchant').textContent = identity.name || 'Merchant';
    $('#footer-model').textContent = 'VERA MERCHANT AI';
    renderMerchantOptions(data.merchants, selectedMerchantId);
    renderMetrics(data.merchant);
    renderTriggers(data.triggers || []);
    renderContext(data);
    renderActivity(data.activity || []);
    renderRecordedMessages(data.recent_ai_messages || []);
    chatMessages = storedChat(selectedMerchantId);
    activeConversationId = conversationIdFor(selectedMerchantId);
    chatEnded = chatMessages.at(-1)?.role === 'system' && chatMessages.at(-1)?.body.includes('conversation has been ended');
    failedChatMessage = null;
    renderChat();
    $('#chat-input').disabled = chatEnded;
    $('#chat-send').disabled = chatEnded;
    if (chatEnded) $('#assistant-presence').innerHTML = '<i></i> Conversation ended';
    return true;
  } catch (error) {
    if (error.name === 'AbortError') return;
    $('#global-error').querySelector('strong').textContent = 'Workspace unavailable';
    $('#global-error-text').textContent = error.message;
    $('#global-error').hidden = false;
    $('#trigger-list').replaceChildren(make('div', 'empty-state error-state', `Could not load merchant insights: ${error.message}`));
    $('#merchant-select').disabled = false;
    toast(error.message, 'error');
    return false;
  }
}

async function sendChat(event, retryMessage = null) {
  event.preventDefault();
  const input = $('#chat-input');
  if (chatEnded) return;
  const value = retryMessage || input.value.trim();
  if (!value || !selectedMerchantId) return;
  const message = value.slice(0, 1200);
  if (!retryMessage) {
    input.value = '';
    input.style.height = 'auto';
    addChatMessage({ role: 'user', body: message, time: new Date().toISOString() });
  }
  $('#chat-send').disabled = true;
  input.disabled = true;
  $('#chat-error').hidden = true;
  $('#chat-error').replaceChildren();

  const history = $('#chat-history');
  const typing = make('article', 'chat-message assistant typing-message');
  typing.append(make('span', 'chat-sender', 'VERA'), make('p', 'typing-dots', 'Vera is thinking…'));
  history.append(typing);
  history.scrollTop = history.scrollHeight;
  $('#assistant-presence').innerHTML = '<i></i> Thinking';

  try {
    const response = await requestJson('/v1/reply', {
      method: 'POST',
      body: JSON.stringify({
        conversation_id: activeConversationId,
        merchant_id: selectedMerchantId,
        from_role: 'merchant',
        message,
        received_at: new Date().toISOString(),
        turn_number: chatMessages.filter((item) => item.role === 'user').length,
      }),
    });
    typing.remove();
    if (response.action === 'send') {
      addChatMessage({ role: 'assistant', body: response.body, cta: response.cta, time: new Date().toISOString() });
    } else if (response.action === 'wait') {
      addChatMessage({ role: 'system', body: `Vera will follow up in ${Math.max(1, Math.round(response.wait_seconds / 60))} minutes.`, time: new Date().toISOString() });
    } else if (response.action === 'end') {
      chatEnded = true;
      addChatMessage({ role: 'system', body: 'This conversation has been ended. Vera will not send further messages.', time: new Date().toISOString() });
    } else {
      throw new Error('The assistant returned an unsupported response.');
    }
    failedChatMessage = null;
    $('#assistant-presence').innerHTML = '<i></i> Ready';
  } catch (error) {
    typing.remove();
    failedChatMessage = message;
    const errorText = make('span', '', `Vera could not respond: ${error.message}. Your message remains in the conversation.`);
    const retryButton = make('button', 'chat-retry', 'Retry');
    retryButton.type = 'button';
    retryButton.disabled = true;
    retryButton.addEventListener('click', (retryEvent) => sendChat(retryEvent, failedChatMessage));
    $('#chat-error').replaceChildren(errorText, retryButton);
    $('#chat-error').hidden = false;
    $('#assistant-presence').innerHTML = '<i></i> Connection issue';
  } finally {
    input.disabled = chatEnded;
    $('#chat-send').disabled = chatEnded;
    const retryButton = $('#chat-error .chat-retry');
    if (retryButton) retryButton.disabled = false;
    input.focus();
  }
}

async function initialize() {
  $('#today-label').textContent = new Intl.DateTimeFormat(undefined, { weekday: 'short', month: 'short', day: 'numeric' }).format(new Date()).toUpperCase();
  setApiStatus('checking', 'Checking Vera AI…');
  $('#global-error').hidden = true;
  const [healthResult, metadataResult] = await Promise.allSettled([
    requestJson('/v1/healthz'),
    requestJson('/v1/metadata'),
  ]);
  if (healthResult.status === 'fulfilled' && healthResult.value.status === 'ok') {
    const storageMode = healthResult.value.context_store;
    setApiStatus('online', 'Vera AI · Connected');
    $('#sidebar-model').textContent = storageMode === 'instance-memory'
      ? 'Context storage · instance memory'
      : 'Context storage · shared';
  } else {
    setApiStatus('offline', 'Backend unavailable');
    $('#global-error').querySelector('strong').textContent = 'Backend unavailable';
    $('#global-error-text').textContent = healthResult.status === 'rejected'
      ? healthResult.reason.message
      : 'The /v1/healthz health check did not pass.';
    $('#global-error').hidden = false;
  }
  if (metadataResult.status === 'fulfilled') {
    const model = metadataResult.value.model || metadataResult.value.team_name;
    $('#sidebar-model').textContent = model || 'Merchant assistant';
    $('#footer-model').textContent = model || 'VERA MERCHANT AI';
  }
  const [workspaceLoaded] = await Promise.all([loadWorkspace(), loadScenarioRecords()]);
  if (healthResult.status === 'fulfilled' && healthResult.value.status === 'ok' && workspaceLoaded) {
    $('#global-error').hidden = true;
  }
}

$('#merchant-select').addEventListener('change', (event) => loadWorkspace(event.target.value));
$('#retry-button').addEventListener('click', initialize);
$('#scenario-search').addEventListener('input', renderScenarioOptions);
$('#scenario-category').addEventListener('change', renderScenarioOptions);
$('#scenario-select').addEventListener('change', (event) => {
  if (event.target.value) loadScenarioPreview(event.target.value);
});
$('#copy-preview').addEventListener('click', async () => {
  try {
    await navigator.clipboard.writeText($('#preview-message').textContent);
    toast('Scenario message copied.', 'success');
  } catch {
    toast('Clipboard access is unavailable in this browser.', 'error');
  }
});
$('#scenario-context-toggle').addEventListener('click', (event) => {
  const data = $('#preview-context-data');
  data.hidden = !data.hidden;
  const expanded = !data.hidden;
  event.currentTarget.setAttribute('aria-expanded', String(expanded));
  event.currentTarget.innerHTML = expanded ? 'Hide context <span>↙</span>' : 'View context <span>↗</span>';
});
$('#chat-form').addEventListener('submit', sendChat);
$('#chat-input').addEventListener('input', (event) => {
  event.target.style.height = 'auto';
  event.target.style.height = `${Math.min(event.target.scrollHeight, 112)}px`;
});
$('#clear-chat').addEventListener('click', () => {
  if (!selectedMerchantId) return;
  chatMessages = [];
  chatEnded = false;
  failedChatMessage = null;
  activeConversationId = conversationIdFor(selectedMerchantId, true);
  saveChat();
  renderChat();
  $('#chat-error').hidden = true;
  $('#chat-input').disabled = false;
  $('#chat-send').disabled = false;
  $('#assistant-presence').innerHTML = '<i></i> Ready';
  toast('This browser chat was cleared. Recorded merchant history is unchanged.');
});
$('#draft-close').addEventListener('click', () => $('#draft-dialog').close());
$('#draft-copy').addEventListener('click', async () => {
  try {
    await navigator.clipboard.writeText($('#draft-message').textContent);
    toast('Message copied to clipboard.', 'success');
  } catch {
    toast('Clipboard access is unavailable in this browser.', 'error');
  }
});

initialize();