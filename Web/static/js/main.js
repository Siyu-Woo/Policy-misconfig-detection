const state = {
    mode: 'run',
    manageTab: 'files',
    fileType: 'policy',
    policyView: 'excel',
    checkView: 'static',
    container: { status: 'unknown' },
    context: { user: 'admin', project: 'admin' },
    files: { policy: [], log: [] },
    current: { policy: null, log: null },
    policyParse: {},
    logParse: {},
    checks: { static: {}, dynamic: {} },
    envOptions: { ready: false, users: [], domains: [], projects: [] },
    terminalHistory: [],
    commandHistory: [],
    historyIndex: 0,
    graph: { network: null, nodes: null, edges: null, data: null, baseColors: {} },
    focus: { type: null, value: null, line: null },
    focusColor: null,
    selectedErrorIdx: null,
};

const els = {};

const ERROR_COLORS = ['#f97316', '#ef4444', '#f59e0b', '#22c55e', '#38bdf8', '#8b5cf6', '#ec4899', '#94a3b8'];

function getErrorColor(typeStr) {
    const match = (typeStr || '').match(/\d+/);
    let idx = 0;
    if (match) {
        idx = parseInt(match[0], 10) - 1;
    } else if (typeStr) {
        idx = typeStr.length % ERROR_COLORS.length;
    }
    if (idx < 0 || idx >= ERROR_COLORS.length) idx = 0;
    return ERROR_COLORS[idx];
}

function $(id) {
    return document.getElementById(id);
}

async function fetchJson(url, options = {}) {
    const res = await fetch(url, options);
    let data = null;
    try {
        data = await res.json();
    } catch (err) {
        data = null;
    }
    if (!res.ok) {
        const message = data && data.error ? data.error : `HTTP ${res.status}`;
        throw new Error(message);
    }
    return data;
}

function showOverlay(text) {
    els.overlayText.textContent = text;
    els.overlay.classList.add('active');
}

function hideOverlay() {
    els.overlay.classList.remove('active');
}

function setMode(mode) {
    state.mode = mode;
    document.querySelectorAll('#mode-toggle button').forEach((btn) => {
        btn.classList.toggle('active', btn.dataset.mode === mode);
    });
    els.runView.classList.toggle('active', mode === 'run');
    els.manageView.classList.toggle('active', mode === 'manage');
    if (mode === 'manage') {
        setManageTab(state.manageTab);
    }
    if (mode === 'run') {
        loadContextOptions(false);
    }
}

function setManageTab(tab) {
    state.manageTab = tab;
    document.querySelectorAll('#manage-tabs button').forEach((btn) => {
        btn.classList.toggle('active', btn.dataset.tab === tab);
    });
    document.querySelectorAll('.page').forEach((page) => {
        page.classList.toggle('active', page.id === `page-${tab}`);
    });
    if (tab === 'policy') {
        ensurePolicyParsed();
    }
    if (tab === 'log') {
        ensureLogParsed();
    }
    if (tab === 'checks') {
        renderChecks();
    }
    updateManageActions();
}

function updateManageActions() {
    els.openImportModal.style.display = state.manageTab === 'files' ? 'inline-flex' : 'none';
    els.manageImportPolicyWrap.style.display = state.manageTab === 'policy' ? 'inline-flex' : 'none';
    els.manageImportLogWrap.style.display = state.manageTab === 'log' ? 'inline-flex' : 'none';
    const showChecks = state.manageTab === 'checks';
    els.runStaticCheck.style.display = showChecks ? 'inline-flex' : 'none';
    els.runDynamicCheck.style.display = showChecks ? 'inline-flex' : 'none';
}

function setFileType(type) {
    state.fileType = type;
    document.querySelectorAll('#file-type-tabs button').forEach((btn) => {
        btn.classList.toggle('active', btn.dataset.type === type);
    });
    renderFileSelect();
    loadFileContent();
}

function setPolicyView(view) {
    state.policyView = view;
    document.querySelectorAll('#policy-view-tabs button').forEach((btn) => {
        btn.classList.toggle('active', btn.dataset.view === view);
    });
    els.policyTable.style.display = view === 'excel' ? 'block' : 'none';
    els.graphPanel.style.display = view === 'graph' ? 'block' : 'none';
    if (view === 'graph') {
        loadGraph();
    }
}

function setCheckView(view) {
    state.checkView = view;
    state.selectedErrorIdx = null;
    state.focusColor = null;
    document.querySelectorAll('#check-view-tabs button').forEach((btn) => {
        btn.classList.toggle('active', btn.dataset.check === view);
    });
    renderChecks();
}

function updateStatus() {
    const dot = els.statusDot;
    const status = state.container.status || 'unknown';
    const detail = state.container.error ? ` (${state.container.error})` : '';
    dot.classList.remove('warn', 'danger');
    if (status === 'running') {
        els.statusText.textContent = `Docker: running${detail}`;
    } else if (status === 'exited' || status === 'dead') {
        dot.classList.add('danger');
        els.statusText.textContent = `Docker: ${status}${detail}`;
    } else {
        dot.classList.add('warn');
        els.statusText.textContent = `Docker: ${status}${detail}`;
    }
}

function updateContext() {
    if (els.contextHost) {
        els.contextHost.textContent = state.container.status === 'running' ? 'Docker' : 'Host';
    }
    els.contextUser.textContent = state.context.user || 'admin';
    els.contextDomain.textContent = state.context.domain || 'Default';
    els.terminalPrompt.textContent = `${state.context.user || 'admin'}@docker:$`;
}

function appendTerminalLine(text, type = 'output') {
    const line = document.createElement('div');
    line.className = `terminal-line ${type}`;
    line.textContent = text;
    els.terminalOutput.appendChild(line);
    els.terminalOutput.scrollTop = els.terminalOutput.scrollHeight;
}

async function sendTerminalCommand() {
    const command = els.terminalInput.value.trim();
    if (!command) return;
    els.terminalInput.value = '';
    state.commandHistory.push(command);
    state.historyIndex = state.commandHistory.length;
    appendTerminalLine(`$ ${command}`, 'command');

    try {
        const res = await fetchJson('/api/terminal', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ command }),
        });
        if (res.stdout) appendTerminalLine(res.stdout);
        if (res.stderr) appendTerminalLine(res.stderr, 'error');
    } catch (err) {
        appendTerminalLine(`Error: ${err.message}`, 'error');
    }
}

function handleHistoryNav(e) {
    if (e.key === 'ArrowUp') {
        if (state.historyIndex > 0) {
            state.historyIndex -= 1;
            els.terminalInput.value = state.commandHistory[state.historyIndex] || '';
        }
        e.preventDefault();
    }
    if (e.key === 'ArrowDown') {
        if (state.historyIndex < state.commandHistory.length - 1) {
            state.historyIndex += 1;
            els.terminalInput.value = state.commandHistory[state.historyIndex] || '';
        } else {
            state.historyIndex = state.commandHistory.length;
            els.terminalInput.value = '';
        }
        e.preventDefault();
    }
}

async function refreshState() {
    const data = await fetchJson('/api/state');
    state.container = data.container || {};
    state.context = data.context || {};
    state.files = data.files || { policy: [], log: [] };
    state.current = data.current || { policy: null, log: null };
    state.policyParse = data.policy_parse || {};
    state.logParse = data.log_parse || {};
    state.checks = data.checks || { static: {}, dynamic: {} };
    state.envOptions = data.env_options || state.envOptions;
    updateStatus();
    updateContext();
    if (state.envOptions.ready) {
        renderContextOptions();
    }
    renderFileSelect();
    if (state.manageTab === 'files') {
        loadFileContent();
    }
}

async function loadContextOptions(force) {
    if (state.envOptions.ready && !force) {
        renderContextOptions();
        return;
    }
    try {
        const data = await fetchJson(`/api/context/options?refresh=${force ? '1' : '0'}`);
        state.envOptions = data;
        renderContextOptions();
    } catch (err) {
        console.error(err);
    }
}

function renderContextOptions() {
    const users = state.envOptions.users || [];
    const domains = state.envOptions.domains || [];
    els.userSelect.innerHTML = '';
    els.domainSelect.innerHTML = '';

    users.forEach((name) => {
        const option = document.createElement('option');
        option.value = name;
        option.textContent = name;
        if (name === state.context.user) option.selected = true;
        els.userSelect.appendChild(option);
    });

    domains.forEach((name) => {
        const option = document.createElement('option');
        option.value = name;
        option.textContent = name;
        if (name === state.context.domain) option.selected = true;
        els.domainSelect.appendChild(option);
    });

    if (!users.length) {
        const option = document.createElement('option');
        option.value = 'admin';
        option.textContent = 'admin';
        els.userSelect.appendChild(option);
    }
    if (!domains.length) {
        const option = document.createElement('option');
        option.value = 'Default';
        option.textContent = 'Default';
        els.domainSelect.appendChild(option);
    }
}

async function handleContextChange() {
    const selectedUser = els.userSelect.value;
    const selectedDomain = els.domainSelect.value;
    showOverlay('切换用户/域...');
    try {
        await loadContextOptions(true);
        if (selectedUser) els.userSelect.value = selectedUser;
        if (selectedDomain) els.domainSelect.value = selectedDomain;
        const data = await fetchJson('/api/context', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user: els.userSelect.value, domain: els.domainSelect.value }),
        });
        state.context = data;
        updateContext();
    } catch (err) {
        console.error(err);
    } finally {
        hideOverlay();
    }
}

function renderFileSelect() {
    const select = els.fileSelect;
    select.innerHTML = '';
    const list = state.files[state.fileType] || [];
    const current = state.current[state.fileType];
    list.forEach((name) => {
        const option = document.createElement('option');
        option.value = name;
        option.textContent = name;
        if (name === current) option.selected = true;
        select.appendChild(option);
    });
}

async function loadFileContent() {
    const filename = state.current[state.fileType];
    if (!filename) {
        els.fileCode.textContent = '当前无文件，请先导入。';
        return;
    }
    try {
        const data = await fetchJson(`/api/file/content?type=${state.fileType}&filename=${encodeURIComponent(filename)}`);
        els.fileCode.textContent = data.content || '';
        els.fileCode.className = state.fileType === 'policy' ? 'language-yaml' : 'language-log';
        if (window.Prism) Prism.highlightElement(els.fileCode);
    } catch (err) {
        els.fileCode.textContent = '加载失败。';
    }
}

async function ensurePolicyParsed() {
    if (!state.current.policy) return;
    if (state.policyParse.ready && state.policyParse.file === state.current.policy) {
        renderPolicy();
        return;
    }
    showOverlay('解析 policy...');
    try {
        const data = await fetchJson('/api/policy/parse', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ force: false }),
        });
        state.policyParse = data;
        renderPolicy();
        loadGraph(true);
    } catch (err) {
        console.error(err);
    } finally {
        hideOverlay();
    }
}

function renderPolicy() {
    const excel = state.policyParse.excel || [];
    let html = '<table><thead><tr><th>#</th><th>Policy</th><th>Rule</th></tr></thead><tbody>';
    excel.forEach((row) => {
        const focusValue = state.focus.value || '';
        const byApi = state.focus.type === 'api' && focusValue && row.name.includes(focusValue);
        const byRole = state.focus.type === 'role' && focusValue && row.rule.includes(focusValue);
        const byProject = state.focus.type === 'project' && focusValue && row.rule.includes(focusValue);
        const highlight = state.focus.line === row.line || byApi || byRole || byProject;
        const colorStyle = highlight && state.focusColor ? `style="box-shadow: inset 3px 0 0 ${state.focusColor}; background: ${state.focusColor}22;"` : '';
        html += `<tr class="${highlight ? 'highlight' : ''}" data-line="${row.line}" data-name="${row.name}" ${colorStyle}><td>${row.line}</td><td>${row.name}</td><td>${row.rule}</td></tr>`;
    });
    html += '</tbody></table>';
    els.policyTable.innerHTML = html;

    els.policyTable.querySelectorAll('tr[data-line]').forEach((row) => {
        row.addEventListener('click', () => {
            const name = row.dataset.name;
            const line = Number(row.dataset.line);
            setFocus({ type: 'api', value: name, line });
        });
    });

    renderPolicyStats();
}

function renderPolicyStats() {
    const stats = state.policyParse.stats || {};
    const items = [
        { label: 'API 数量', value: stats.api || 0 },
        { label: 'Rule 数量', value: stats.rule || 0 },
        { label: 'Role 数量', value: stats.role || 0 },
        { label: 'Project 数量', value: stats.project || 0 },
        { label: 'User 数量', value: stats.user || 0 },
    ];
    els.policyStats.innerHTML = items
        .map((item) => `<div class="stats-card"><b>${item.value}</b>${item.label}</div>`)
        .join('');
}

async function loadGraph(force = false) {
    if (state.graph.network && !force) return;
    try {
        const data = await fetchJson('/api/graph');
        state.graph.data = data;
        state.graph.nodes = new vis.DataSet(data.nodes || []);
        state.graph.edges = new vis.DataSet(data.edges || []);
        state.graph.baseColors = {};
        (data.nodes || []).forEach((node) => {
            state.graph.baseColors[node.id] = node.color || '#a3bffa';
        });
        const options = {
            nodes: { shape: 'dot', size: 16, font: { size: 12 } },
            edges: { arrows: 'to', color: { color: '#94a3b8' } },
            physics: { stabilization: false, barnesHut: { gravitationalConstant: -2500, springLength: 90 } },
        };
        state.graph.network = new vis.Network(els.graph, { nodes: state.graph.nodes, edges: state.graph.edges }, options);
        state.graph.network.on('click', (params) => {
            if (!params.nodes.length) {
                clearFocus();
                return;
            }
            if (state.selectedErrorIdx !== null) {
                return;
            }
            const nodeId = params.nodes[0];
            const node = state.graph.nodes.get(nodeId);
            if (!node) return;
            setFocus({ type: 'api', value: node.label });
            highlightGraph(nodeId);
        });
        applyGraphFocus();
    } catch (err) {
        console.error(err);
    }
}

function highlightGraph(focusId, colorOverride = null) {
    if (!state.graph.network || !state.graph.nodes) return;
    const connected = new Set(state.graph.network.getConnectedNodes(focusId));
    connected.add(focusId);
    const updates = state.graph.nodes.get().map((node) => {
        const isFocus = connected.has(node.id);
        return {
            id: node.id,
            color: isFocus ? (colorOverride || state.graph.baseColors[node.id]) : '#e2e8f0',
            font: { color: isFocus ? '#0f172a' : '#cbd5f5' },
        };
    });
    state.graph.nodes.update(updates);
}

function applyGraphFocus() {
    if (!state.graph.nodes) return;
    if (!state.focus.value) {
        state.graph.nodes.update(
            state.graph.nodes.get().map((node) => ({
                id: node.id,
                color: state.graph.baseColors[node.id] || node.color,
                font: { color: '#0f172a' },
            }))
        );
        return;
    }
    const focusValue = state.focus.value.toLowerCase();
    const matched = state.graph.nodes.get().filter((node) => {
        if (!node.label) return false;
        if (state.focus.type === 'role') {
            return node.labels && node.labels.includes('ConditionNode') && node.cond_type === 'role' && node.label.toLowerCase().includes(focusValue);
        }
        if (state.focus.type === 'project') {
            return node.labels && node.labels.includes('ConditionNode') && ['project', 'project_id'].includes(node.cond_type) && node.label.toLowerCase().includes(focusValue);
        }
        return node.label.toLowerCase().includes(focusValue);
    });
    if (!matched.length) return;
    const focusId = matched[0].id;
    highlightGraph(focusId, state.focusColor);
}

function setFocus({ type, value, line = null, color = undefined }) {
    if (state.selectedErrorIdx !== null && color === undefined) {
        return;
    }
    state.focus = { type, value, line };
    if (color !== undefined) {
        state.focusColor = color;
    } else if (state.selectedErrorIdx === null) {
        state.focusColor = null;
    }
    if (type === 'api') {
        els.searchApi.value = value || '';
        els.searchRole.value = '';
        els.searchProject.value = '';
    }
    if (type === 'role') {
        els.searchApi.value = '';
        els.searchRole.value = value || '';
        els.searchProject.value = '';
    }
    if (type === 'project') {
        els.searchApi.value = '';
        els.searchRole.value = '';
        els.searchProject.value = value || '';
    }
    renderPolicy();
    applyGraphFocus();
    if (line) {
        const row = els.policyTable.querySelector(`tr[data-line='${line}']`);
        if (row) row.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}

function clearFocus() {
    if (state.selectedErrorIdx !== null) return;
    state.focus = { type: null, value: null, line: null };
    els.searchApi.value = '';
    els.searchRole.value = '';
    els.searchProject.value = '';
    renderPolicy();
    applyGraphFocus();
}

async function ensureLogParsed() {
    if (!state.current.log) return;
    if (state.logParse.ready && state.logParse.file === state.current.log) {
        renderLog();
        return;
    }
    showOverlay('解析 log...');
    try {
        const data = await fetchJson('/api/log/parse', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ force: false }),
        });
        state.logParse = data;
        renderLog();
    } catch (err) {
        console.error(err);
    } finally {
        hideOverlay();
    }
}

function renderLog() {
    const rows = state.logParse.rows || [];
    let html = '<table><thead><tr><th>Time</th><th>API</th><th>User</th><th>Project</th></tr></thead><tbody>';
    rows.forEach((row) => {
        html += `<tr><td>${row.timestamp || ''}</td><td>${row.api || ''}</td><td>${row.user_name || ''}</td><td>${row.project_name || ''}</td></tr>`;
    });
    html += '</tbody></table>';
    els.logTable.innerHTML = html;
}

function renderChecks() {
    const current = state.checks[state.checkView] || {};
    const errors = current.errors || [];
    if (state.selectedErrorIdx !== null && state.selectedErrorIdx >= errors.length) {
        state.selectedErrorIdx = null;
        state.focusColor = null;
    }
    if (!errors.length) {
        els.checkCards.innerHTML = '<div class="check-card">暂无检测结果</div>';
    } else {
        els.checkCards.innerHTML = errors
            .map((err, idx) => {
                const lines = (err.lines || []).join(', ');
                const color = getErrorColor(err.type);
                const selected = state.selectedErrorIdx === idx;
                const dimmed = state.selectedErrorIdx !== null && !selected;
                const classes = ['check-card', selected ? 'selected' : '', dimmed ? 'dimmed' : ''].join(' ');
                return `<div class="${classes}" data-index="${idx}" style="--accent-color:${color}">
                    <strong>${err.type || 'Unknown'}</strong>
                    <div><small>${lines ? `Line ${lines}` : ''}</small></div>
                    <div>${(err.policy || '').trim().replace(/\\n/g, ' ')}</div>
                    <div><small>${err.info || ''}</small></div>
                </div>`;
            })
            .join('');
    }

    els.checkCards.querySelectorAll('.check-card').forEach((card) => {
        card.addEventListener('click', () => {
            const idx = Number(card.dataset.index);
            const err = errors[idx];
            if (!err) return;
            const line = err.lines && err.lines.length ? err.lines[0] : null;
            let apiName = '';
            const match = (err.policy || '').match(/line\\s+\\d+\\s*:\\s*([^\\s]+)/);
            if (match) apiName = match[1];
            if (state.selectedErrorIdx === idx) {
                state.selectedErrorIdx = null;
                state.focusColor = null;
                clearFocus();
                renderChecks();
                return;
            }
            state.selectedErrorIdx = idx;
            state.focusColor = getErrorColor(err.type);
            setFocus({ type: 'api', value: apiName, line, color: state.focusColor });
            renderChecks();
        });
    });

    const summary = current.summary || {};
    const byType = summary.by_type || {};
    els.checkSummary.innerHTML = Object.keys(byType)
        .map((key) => `<span style="--accent-color:${getErrorColor(key)}; border-left:3px solid var(--accent-color)">${key}: ${byType[key]}</span>`)
        .join('');
}

async function handleFileSelectChange() {
    const filename = els.fileSelect.value;
    await fetchJson('/api/files/select', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type: state.fileType, filename }),
    });
    await refreshState();
    loadFileContent();
}

async function handleImport(file, type, endpoint) {
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    showOverlay('上传中...');
    try {
        await fetchJson(endpoint, { method: 'POST', body: formData });
        await refreshState();
        if (type === 'policy') {
            await ensurePolicyParsed();
        }
        if (type === 'log') {
            await ensureLogParsed();
        }
    } catch (err) {
        console.error(err);
    } finally {
        hideOverlay();
    }
}

async function handleApplyPolicy(file) {
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    showOverlay('导入 policy 并重启容器...');
    try {
        await fetchJson('/api/apply/policy', { method: 'POST', body: formData });
        await refreshState();
    } catch (err) {
        console.error(err);
    } finally {
        hideOverlay();
    }
}

async function handleExport(url, message) {
    showOverlay(message);
    try {
        await fetchJson(url, { method: 'POST' });
        await refreshState();
    } catch (err) {
        console.error(err);
    } finally {
        hideOverlay();
    }
}

async function handleEnvOverview() {
    showOverlay('拉取环境信息...');
    try {
        const data = await fetchJson('/api/env/overview');
        renderOverview(data);
    } catch (err) {
        console.error(err);
    } finally {
        hideOverlay();
    }
}

function renderOverview(data) {
    const users = data.users || [];
    const projects = data.projects || [];
    const domains = data.domains || [];
    els.overviewPanel.innerHTML = `
        <div class="inline-card"><h4>Users (${users.length})</h4>${users.slice(0, 6).map((u) => `<div>${u.Name || ''}</div>`).join('')}</div>
        <div class="inline-card"><h4>Projects (${projects.length})</h4>${projects.slice(0, 6).map((p) => `<div>${p.Name || ''}</div>`).join('')}</div>
        <div class="inline-card"><h4>Domains (${domains.length})</h4>${domains.slice(0, 6).map((d) => `<div>${d.Name || ''}</div>`).join('')}</div>
    `;
}

function bindEvents() {
    document.querySelectorAll('#mode-toggle button').forEach((btn) => {
        btn.addEventListener('click', () => setMode(btn.dataset.mode));
    });

    document.querySelectorAll('#manage-tabs button').forEach((btn) => {
        btn.addEventListener('click', () => setManageTab(btn.dataset.tab));
    });

    document.querySelectorAll('#file-type-tabs button').forEach((btn) => {
        btn.addEventListener('click', () => setFileType(btn.dataset.type));
    });

    document.querySelectorAll('#policy-view-tabs button').forEach((btn) => {
        btn.addEventListener('click', () => setPolicyView(btn.dataset.view));
    });

    document.querySelectorAll('#check-view-tabs button').forEach((btn) => {
        btn.addEventListener('click', () => setCheckView(btn.dataset.check));
    });

    els.terminalSend.addEventListener('click', sendTerminalCommand);
    els.terminalInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') sendTerminalCommand();
        handleHistoryNav(e);
    });
    els.terminalClear.addEventListener('click', () => {
        els.terminalOutput.innerHTML = '';
    });

    els.fileSelect.addEventListener('change', handleFileSelectChange);

    els.exportPolicy.addEventListener('click', () => handleExport('/api/export/policy', '导出 policy...'));
    els.exportLog.addEventListener('click', () => handleExport('/api/export/log', '导出 log...'));
    els.importPolicy.addEventListener('change', (e) => handleApplyPolicy(e.target.files[0]));
    els.manageImportPolicy.addEventListener('change', (e) => handleImport(e.target.files[0], 'policy', '/api/import/policy'));
    els.manageImportLog.addEventListener('change', (e) => handleImport(e.target.files[0], 'log', '/api/import/log'));
    els.fetchOverview.addEventListener('click', handleEnvOverview);

    els.runStaticCheck.addEventListener('click', async () => {
        showOverlay('静态检测中...');
        try {
            const data = await fetchJson('/api/check/static', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ force: false }) });
            state.checks.static = data;
            state.selectedErrorIdx = null;
            state.focusColor = null;
            renderChecks();
        } catch (err) {
            console.error(err);
            alert(err.message);
        } finally {
            hideOverlay();
        }
    });

    els.runDynamicCheck.addEventListener('click', async () => {
        showOverlay('动态检测中...');
        try {
            const data = await fetchJson('/api/check/dynamic', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ force: false }) });
            state.checks.dynamic = data;
            state.selectedErrorIdx = null;
            state.focusColor = null;
            renderChecks();
        } catch (err) {
            console.error(err);
            alert(err.message);
        } finally {
            hideOverlay();
        }
    });

    els.userSelect.addEventListener('change', handleContextChange);
    els.domainSelect.addEventListener('change', handleContextChange);
    els.userSelect.addEventListener('click', () => loadContextOptions(true));
    els.domainSelect.addEventListener('click', () => loadContextOptions(true));

    els.containerRestart.addEventListener('click', async () => {
        showOverlay('重启容器中...');
        try {
            await fetchJson('/api/container/restart', { method: 'POST' });
            await refreshState();
        } catch (err) {
            console.error(err);
        } finally {
            hideOverlay();
        }
    });

    els.openImportModal.addEventListener('click', () => {
        els.importModal.classList.add('active');
    });
    els.modalImportPolicy.addEventListener('click', () => {
        els.importModal.classList.remove('active');
        els.manageImportPolicy.click();
    });
    els.modalImportLog.addEventListener('click', () => {
        els.importModal.classList.remove('active');
        els.manageImportLog.click();
    });
    els.modalClose.addEventListener('click', () => {
        els.importModal.classList.remove('active');
    });
    els.importModal.addEventListener('click', (e) => {
        if (e.target === els.importModal) {
            els.importModal.classList.remove('active');
        }
    });

    els.searchApi.addEventListener('input', () => {
        if (els.searchApi.value.trim()) setFocus({ type: 'api', value: els.searchApi.value.trim() });
        else clearFocus();
    });
    els.searchRole.addEventListener('input', () => {
        if (els.searchRole.value.trim()) setFocus({ type: 'role', value: els.searchRole.value.trim() });
        else clearFocus();
    });
    els.searchProject.addEventListener('input', () => {
        if (els.searchProject.value.trim()) setFocus({ type: 'project', value: els.searchProject.value.trim() });
        else clearFocus();
    });
}

function cacheEls() {
    els.runView = $('run-view');
    els.manageView = $('manage-view');
    els.statusDot = $('status-dot');
    els.statusText = $('status-text');
    els.contextUser = $('context-user');
    els.contextDomain = $('context-domain');
    els.contextHost = $('context-host');
    els.userSelect = $('user-select');
    els.domainSelect = $('domain-select');
    els.terminalPrompt = $('terminal-prompt');
    els.terminalOutput = $('terminal-output');
    els.terminalInput = $('terminal-input');
    els.terminalSend = $('terminal-send');
    els.terminalClear = $('terminal-clear');
    els.fileSelect = $('file-select');
    els.fileCode = $('file-code');
    els.policyTable = $('policy-table');
    els.graphPanel = $('graph-panel');
    els.graph = $('graph');
    els.policyStats = $('policy-stats');
    els.logTable = $('log-table');
    els.checkCards = $('check-cards');
    els.checkSummary = $('check-summary');
    els.searchApi = $('search-api');
    els.searchRole = $('search-role');
    els.searchProject = $('search-project');
    els.exportPolicy = $('export-policy');
    els.exportLog = $('export-log');
    els.importPolicy = $('import-policy');
    els.manageImportPolicy = $('manage-import-policy');
    els.manageImportLog = $('manage-import-log');
    els.manageImportPolicyWrap = $('manage-import-policy-wrap');
    els.manageImportLogWrap = $('manage-import-log-wrap');
    els.openImportModal = $('open-import-modal');
    els.fetchOverview = $('fetch-overview');
    els.runStaticCheck = $('run-static-check');
    els.runDynamicCheck = $('run-dynamic-check');
    els.overlay = $('overlay');
    els.overlayText = $('overlay-text');
    els.containerRestart = $('container-restart');
    els.overviewPanel = $('overview-panel');
    els.importModal = $('import-modal');
    els.modalImportPolicy = $('modal-import-policy');
    els.modalImportLog = $('modal-import-log');
    els.modalClose = $('modal-close');
}

async function init() {
    cacheEls();
    bindEvents();
    await refreshState();
    await loadContextOptions(true);
    if (state.container.status !== 'running') {
        appendTerminalLine('容器未运行，请先启动 openstack-policy-detection。', 'error');
        showOverlay('容器未运行，请先启动 openstack-policy-detection');
        setTimeout(() => {
            hideOverlay();
        }, 3000);
    }
    setMode('run');
    setManageTab('files');
    setFileType('policy');
    setPolicyView('excel');
    setCheckView('static');
    await loadFileContent();
    setInterval(async () => {
        try {
            const status = await fetchJson('/api/status');
            state.container = status.container || {};
            state.context = status.context || state.context;
            updateStatus();
            updateContext();
        } catch (err) {
            console.error(err);
        }
    }, 15000);
}

window.addEventListener('DOMContentLoaded', init);
