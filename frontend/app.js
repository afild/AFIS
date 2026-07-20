// AFIS System Client Logic — Dynamic UI, Chart.js & What-If Simulator

const API_BASE = "http://127.0.0.1:8000/api";
let cashflowChart = null;
let whatifChart = null;
let whatifDebounceTimer = null;
let _baseForecastCache = null;  // Cached base forecast to avoid re-fetching on slider moves

document.addEventListener("DOMContentLoaded", () => {
    initTabs();
    fetchDashboardData();
    fetchAuditData();
    initFileIngestion();
    initWhatIfSliders();
});

// ─── TAB SYSTEM ──────────────────────────────────────────────────────────────
function initTabs() {
    const tabs = document.querySelectorAll(".nav-btn");
    const panels = document.querySelectorAll(".tab-panel");
    const pageTitle = document.getElementById("page-title");
    const pageSubtitle = document.getElementById("page-subtitle");

    const meta = {
        "dashboard": { title: "Executive Dashboard", subtitle: "Overview of historical accounts and ML cash projections." },
        "chat":      { title: "AI CFO Analyst Agent", subtitle: "Interact with our cognitive financial assistant to audit ledger." },
        "audit":     { title: "NIST Audit & Ingestion", subtitle: "Audit logs console and raw data ETL pipeline ingestion." }
    };

    tabs.forEach(tab => {
        tab.addEventListener("click", () => {
            const target = tab.getAttribute("data-tab");

            tabs.forEach(t => t.classList.remove("active"));
            panels.forEach(p => p.classList.remove("active"));

            tab.classList.add("active");
            document.getElementById(`tab-${target}`).classList.add("active");

            pageTitle.textContent = meta[target].title;
            pageSubtitle.textContent = meta[target].subtitle;
        });
    });
}

// ─── FETCH DASHBOARD DATA ─────────────────────────────────────────────────────
async function fetchDashboardData() {
    try {
        // 1. Fetch KPIs
        const kpisRes = await fetch(`${API_BASE}/kpis`);
        const kpis = await kpisRes.json();
        renderKPIs(kpis);

        // 2. Fetch Transactions
        const txRes = await fetch(`${API_BASE}/transactions`);
        const transactions = await txRes.json();
        renderTransactions(transactions);

        // 3. Risk Advisory
        renderAdvisory(kpis);

        // 4. Fetch Forecasts and Build Chart
        const forecastRes = await fetch(`${API_BASE}/forecast`);
        const forecasts = await forecastRes.json();
        _baseForecastCache = forecasts;
        buildChart(transactions, forecasts);

        // 5. Build initial What-If chart (at 0% delta = mirrors base)
        buildWhatIfChart(forecasts, forecasts);

    } catch (err) {
        console.error("Failed to load dashboard data:", err);
    }
}

// ─── RENDER KPIs (4 cards) ────────────────────────────────────────────────────
function renderKPIs(kpis) {
    document.getElementById("kpi-cash").textContent =
        `$${kpis.current_cash.toLocaleString('en-US', { minimumFractionDigits: 2 })}`;

    document.getElementById("kpi-runway").textContent =
        typeof kpis.runway === 'number' ? `${kpis.runway} Months` : kpis.runway;

    document.getElementById("kpi-burnrate").textContent =
        kpis.burn_rate > 0
            ? `Burn: $${kpis.burn_rate.toLocaleString('en-US')}/mo`
            : `Cash Surplus: $${Math.abs(kpis.net_cash_flow_3m).toLocaleString('en-US')}/mo`;

    document.getElementById("kpi-margin").textContent = `${kpis.net_margin_percent}%`;
    document.getElementById("kpi-netprofit").textContent =
        `Net: $${kpis.net_profit.toLocaleString('en-US', { minimumFractionDigits: 2 })}`;

    // 4th KPI — Net Cash Flow (3m avg)
    const cashflowEl = document.getElementById("kpi-cashflow");
    const cashflowLabelEl = document.getElementById("kpi-cashflow-label");
    const ncf = kpis.net_cash_flow_3m || 0;
    cashflowEl.textContent = `${ncf >= 0 ? '+' : ''}$${ncf.toLocaleString('en-US', { minimumFractionDigits: 2 })}`;
    cashflowEl.style.color = ncf >= 0 ? 'var(--color-success)' : 'var(--color-danger)';
    cashflowLabelEl.textContent = ncf >= 0 ? 'Monthly surplus' : 'Monthly deficit';
}

// ─── RENDER TRANSACTIONS ──────────────────────────────────────────────────────
function renderTransactions(transactions) {
    const tbody = document.getElementById("transaction-rows");
    tbody.innerHTML = "";

    if (transactions.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" class="text-center text-secondary">No transaction records found. Upload a CSV ledger.</td></tr>`;
        return;
    }

    transactions.slice(0, 7).forEach(tx => {
        const row = document.createElement("tr");
        const typeClass = tx.type === "income" ? "text-success" : "text-danger";
        const prefix = tx.type === "income" ? "+" : "-";

        row.innerHTML = `
            <td>${tx.date}</td>
            <td><span class="badge badge-navy">${tx.category}</span></td>
            <td>${tx.description || '—'}</td>
            <td><span class="${typeClass}">${tx.type.toUpperCase()}</span></td>
            <td class="text-right ${typeClass}">${prefix}$${tx.amount.toLocaleString('en-US', { minimumFractionDigits: 2 })}</td>
        `;
        tbody.appendChild(row);
    });
}

// ─── RENDER ADVISORY ──────────────────────────────────────────────────────────
function renderAdvisory(kpis) {
    const container = document.getElementById("advisory-container");
    container.innerHTML = "";

    const items = [];

    if (typeof kpis.runway === 'number') {
        if (kpis.runway < 6) {
            items.push({ type: "red", icon: "fa-triangle-exclamation",
                text: `**Critical Runway Alert:** Cash will run out in **${kpis.runway} months**. Pause new hires immediately.` });
        } else if (kpis.runway < 12) {
            items.push({ type: "orange", icon: "fa-circle-exclamation",
                text: `**Caution Runway:** Runway sits at **${kpis.runway} months**. Monitor expansion costs.` });
        } else {
            items.push({ type: "green", icon: "fa-circle-check",
                text: `**Healthy Cash Position:** Cash reserves project **${kpis.runway} months** of runway.` });
        }
    } else {
        items.push({ type: "green", icon: "fa-circle-check",
            text: `**Cash Flow Positive:** Net income is positive. Runway is infinite under stable operations.` });
    }

    if (kpis.net_margin_percent < 15) {
        items.push({ type: "orange", icon: "fa-chart-line-down",
            text: `**Low Margin Warning:** Net margin is **${kpis.net_margin_percent}%**. Review infrastructure costs.` });
    } else {
        items.push({ type: "green", icon: "fa-piggy-bank",
            text: `**Leverage Stable:** Net margin is **${kpis.net_margin_percent}%**, ensuring robust margin retention.` });
    }

    items.forEach(item => {
        const div = document.createElement("div");
        div.className = `advisory-alert alert-${item.type}`;
        const parsedText = item.text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        div.innerHTML = `<i class="fa-solid ${item.icon}" style="margin-top:2px;"></i><div>${parsedText}</div>`;
        container.appendChild(div);
    });
}

// ─── BUILD MAIN FORECAST CHART ────────────────────────────────────────────────
function buildChart(historical, forecasts) {
    const ctx = document.getElementById("cashflowChart").getContext("2d");

    const monthlyHist = {};
    historical.forEach(tx => {
        const m = tx.date.substring(0, 7);
        if (!monthlyHist[m]) monthlyHist[m] = { income: 0, expense: 0 };
        if (tx.type === 'income') monthlyHist[m].income += tx.amount;
        else monthlyHist[m].expense += tx.amount;
    });

    const sortedHistMonths = Object.keys(monthlyHist).sort();
    const labels = [], actualIncome = [], actualExpense = [], predIncome = [], predExpense = [];

    sortedHistMonths.forEach(m => {
        labels.push(m);
        actualIncome.push(monthlyHist[m].income);
        actualExpense.push(monthlyHist[m].expense);
        predIncome.push(null);
        predExpense.push(null);
    });

    if (labels.length > 0) {
        const lastMonth = labels[labels.length - 1];
        predIncome[labels.length - 1] = monthlyHist[lastMonth].income;
        predExpense[labels.length - 1] = monthlyHist[lastMonth].expense;
    }

    forecasts.forEach(f => {
        labels.push(f.month);
        actualIncome.push(null);
        actualExpense.push(null);
        predIncome.push(f.income);
        predExpense.push(f.expense);
    });

    if (cashflowChart) cashflowChart.destroy();

    const gradientInc = ctx.createLinearGradient(0, 0, 0, 400);
    gradientInc.addColorStop(0, 'rgba(16, 185, 129, 0.4)');
    gradientInc.addColorStop(1, 'rgba(16, 185, 129, 0.0)');

    const gradientExp = ctx.createLinearGradient(0, 0, 0, 400);
    gradientExp.addColorStop(0, 'rgba(244, 63, 94, 0.4)');
    gradientExp.addColorStop(1, 'rgba(244, 63, 94, 0.0)');

    cashflowChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [
                { label: 'Actual Income', data: actualIncome, borderColor: '#10b981', backgroundColor: gradientInc, borderWidth: 3, fill: true, tension: 0.35, spanGaps: false },
                { label: 'Actual Expense', data: actualExpense, borderColor: '#f43f5e', backgroundColor: gradientExp, borderWidth: 3, fill: true, tension: 0.35, spanGaps: false },
                { label: 'Predicted Income', data: predIncome, borderColor: '#10b981', borderDash: [5, 5], borderWidth: 2, pointRadius: 2, fill: false, tension: 0.35, spanGaps: true },
                { label: 'Predicted Expense', data: predExpense, borderColor: '#f43f5e', borderDash: [5, 5], borderWidth: 2, pointRadius: 2, fill: false, tension: 0.35, spanGaps: true }
            ]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } },
                y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8', callback: v => '$' + v.toLocaleString() } }
            }
        }
    });
}

// ─── WHAT-IF SIMULATOR ────────────────────────────────────────────────────────
function initWhatIfSliders() {
    const incomeSlider = document.getElementById("income-slider");
    const expenseSlider = document.getElementById("expense-slider");
    const incomeDisplay = document.getElementById("income-delta-display");
    const expenseDisplay = document.getElementById("expense-delta-display");

    function updateSliderTrack(slider) {
        const val = slider.value;
        const min = slider.min || -50;
        const max = slider.max || 50;
        const pct = ((val - min) / (max - min)) * 100;
        slider.style.background = `linear-gradient(to right, var(--color-primary) ${pct}%, rgba(255,255,255,0.1) ${pct}%)`;
    }

    function updateDisplay(slider, displayEl) {
        const val = parseFloat(slider.value);
        const prefix = val > 0 ? '+' : '';
        displayEl.textContent = `${prefix}${val}%`;
        displayEl.className = 'slider-value' + (val < 0 ? ' negative' : val > 0 ? ' positive' : '');
        updateSliderTrack(slider);
    }

    incomeSlider.addEventListener("input", () => {
        updateDisplay(incomeSlider, incomeDisplay);
        clearTimeout(whatifDebounceTimer);
        whatifDebounceTimer = setTimeout(runWhatIfSimulation, 300);
    });

    expenseSlider.addEventListener("input", () => {
        updateDisplay(expenseSlider, expenseDisplay);
        clearTimeout(whatifDebounceTimer);
        whatifDebounceTimer = setTimeout(runWhatIfSimulation, 300);
    });

    // Initialize tracks
    updateSliderTrack(incomeSlider);
    updateSliderTrack(expenseSlider);
}

async function runWhatIfSimulation() {
    const incomeDelta = parseFloat(document.getElementById("income-slider").value);
    const expenseDelta = parseFloat(document.getElementById("expense-slider").value);
    const statusEl = document.getElementById("whatif-status");

    statusEl.textContent = "Running simulation...";

    try {
        const res = await fetch(`${API_BASE}/forecast/whatif`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ income_delta_pct: incomeDelta, expense_delta_pct: expenseDelta })
        });
        const data = await res.json();
        buildWhatIfChart(_baseForecastCache || [], data.scenario || []);

        const netImpact = (data.scenario || []).reduce((acc, m) => acc + m.net, 0);
        const prefix = netImpact >= 0 ? '+' : '';
        statusEl.textContent = `Simulated 12-month net: ${prefix}$${netImpact.toLocaleString('en-US', { minimumFractionDigits: 2 })}`;
        statusEl.style.color = netImpact >= 0 ? 'var(--color-success)' : 'var(--color-danger)';
    } catch (err) {
        statusEl.textContent = "Simulation failed — check backend status.";
        statusEl.style.color = 'var(--color-danger)';
    }
}

function resetWhatIf() {
    document.getElementById("income-slider").value = 0;
    document.getElementById("expense-slider").value = 0;
    document.getElementById("income-delta-display").textContent = "0%";
    document.getElementById("expense-delta-display").textContent = "0%";
    document.getElementById("income-delta-display").className = "slider-value";
    document.getElementById("expense-delta-display").className = "slider-value";
    document.getElementById("whatif-status").textContent = "";

    // Reset slider tracks
    ["income-slider", "expense-slider"].forEach(id => {
        const s = document.getElementById(id);
        s.style.background = `linear-gradient(to right, var(--color-primary) 50%, rgba(255,255,255,0.1) 50%)`;
    });

    if (_baseForecastCache) buildWhatIfChart(_baseForecastCache, _baseForecastCache);
}

function buildWhatIfChart(base, scenario) {
    const ctx = document.getElementById("whatifChart").getContext("2d");
    const labels = (scenario.length > 0 ? scenario : base).map(m => m.month);

    const baseNet = base.map(m => m.net);
    const scenarioNet = scenario.map(m => m.net);

    if (whatifChart) whatifChart.destroy();

    whatifChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [
                {
                    label: 'Base Forecast (Net)',
                    data: baseNet,
                    backgroundColor: 'rgba(6, 182, 212, 0.25)',
                    borderColor: '#06b6d4',
                    borderWidth: 1.5,
                    borderRadius: 4
                },
                {
                    label: 'Scenario (Net)',
                    data: scenarioNet,
                    backgroundColor: scenarioNet.map(v => v >= 0 ? 'rgba(16, 185, 129, 0.35)' : 'rgba(244, 63, 94, 0.35)'),
                    borderColor: scenarioNet.map(v => v >= 0 ? '#10b981' : '#f43f5e'),
                    borderWidth: 1.5,
                    borderRadius: 4
                }
            ]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: {
                legend: { display: true, labels: { color: '#94a3b8', font: { size: 11 } } },
                tooltip: {
                    callbacks: {
                        label: ctx => ` $${ctx.parsed.y.toLocaleString('en-US', { minimumFractionDigits: 2 })}`
                    }
                }
            },
            scales: {
                x: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#94a3b8', font: { size: 10 } } },
                y: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#94a3b8', callback: v => '$' + v.toLocaleString() } }
            }
        }
    });
}

// ─── CHAT SYSTEM ──────────────────────────────────────────────────────────────
async function sendMessage() {
    const input = document.getElementById("chat-input");
    const text = input.value.trim();
    if (!text) return;

    appendChatMessage(text, "outgoing");
    input.value = "";

    const loadingBubble = appendChatMessage("Analyzing transactions...", "incoming loading-bubble");

    try {
        const res = await fetch(`${API_BASE}/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: text })
        });
        const data = await res.json();
        loadingBubble.remove();

        let formattedText = data.response
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\n/g, '<br>');

        appendChatMessage(formattedText, "incoming", true);
    } catch (err) {
        loadingBubble.remove();
        appendChatMessage("Sorry, I encountered an error checking the ledger. Verify backend status.", "incoming");
    }
}

function sendQuickPrompt(promptText) {
    document.getElementById("chat-input").value = promptText;
    sendMessage();
}

function appendChatMessage(content, senderClass, isHtml = false) {
    const historyBox = document.getElementById("chat-history-box");
    const messageDiv = document.createElement("div");
    messageDiv.className = `chat-message ${senderClass}`;

    const bubble = document.createElement("div");
    bubble.className = "msg-bubble";

    if (isHtml) bubble.innerHTML = content;
    else bubble.textContent = content;

    messageDiv.appendChild(bubble);
    historyBox.appendChild(messageDiv);
    historyBox.scrollTop = historyBox.scrollHeight;

    return messageDiv;
}

// ─── FETCH AUDIT & LOGS DATA ──────────────────────────────────────────────────
async function fetchAuditData() {
    try {
        const res = await fetch(`${API_BASE}/nist-audit`);
        const data = await res.json();

        const grid = document.getElementById("nist-grid");
        grid.innerHTML = "";

        data.checklist.forEach(item => {
            const card = document.createElement("div");
            card.className = "nist-card";
            card.innerHTML = `
                <div class="nist-header">
                    <span class="nist-title">${item.standard_prong}</span>
                    <span class="nist-badge nist-badge-pass">${item.status}</span>
                </div>
                <div class="nist-name">${item.metric_name}</div>
                <div class="nist-desc">${item.details}</div>
            `;
            grid.appendChild(card);
        });

        const consoleBox = document.getElementById("logs-console-box");
        consoleBox.innerHTML = "";

        data.recent_logs.forEach(log => {
            const div = document.createElement("div");
            div.className = "log-line";

            let lvlClass = "log-info";
            if (log.level === "WARNING") lvlClass = "log-warning";
            if (log.level === "ERROR") lvlClass = "log-error";

            div.innerHTML = `
                <span class="text-muted">[${log.timestamp.split('.')[0]}]</span>
                <span class="${lvlClass}">[${log.level}]</span>
                <span class="text-secondary">[${log.module}]</span>
                <span>${log.message}</span>
                ${log.details ? `<br><span class="text-muted" style="margin-left:20px;">➔ ${log.details}</span>` : ""}
            `;
            consoleBox.appendChild(div);
        });

    } catch (err) {
        console.error("Failed to load audit logs:", err);
    }
}

// ─── FILE UPLOAD ETL ──────────────────────────────────────────────────────────
function initFileIngestion() {
    const fileInput = document.getElementById("file-input");
    const dropZone = document.getElementById("drop-zone");
    const statusDiv = document.getElementById("upload-status");

    fileInput.addEventListener("change", e => {
        if (e.target.files.length > 0) uploadFile(e.target.files[0]);
    });

    ["dragenter", "dragover"].forEach(event => {
        dropZone.addEventListener(event, e => { e.preventDefault(); dropZone.classList.add("dragover"); }, false);
    });

    ["dragleave", "drop"].forEach(event => {
        dropZone.addEventListener(event, e => { e.preventDefault(); dropZone.classList.remove("dragover"); }, false);
    });

    dropZone.addEventListener("drop", e => {
        const files = e.dataTransfer.files;
        if (files.length > 0) uploadFile(files[0]);
    });

    async function uploadFile(file) {
        statusDiv.innerHTML = `<div class="loading-spinner"></div><p>Executing ETL pipeline operations...</p>`;

        const formData = new FormData();
        formData.append("file", file);

        try {
            const res = await fetch(`${API_BASE}/ingest`, { method: "POST", body: formData });
            const data = await res.json();

            if (data.status === "success") {
                const s = data.summary;
                statusDiv.innerHTML = `
                    <span class="text-success"><i class="fa-solid fa-circle-check"></i> Ingestion Successful!</span><br>
                    <span class="text-small text-secondary">
                        Inserted: <strong>${s.inserted}</strong> |
                        Duplicates: <strong>${s.duplicates}</strong> |
                        Warnings: <strong>${s.anomalies}</strong> |
                        Rejected: <strong>${s.rejected}</strong>
                    </span>
                `;
                fetchDashboardData();
                fetchAuditData();
            } else {
                throw new Error(data.message || "Failed ingestion");
            }
        } catch (err) {
            statusDiv.innerHTML = `<span class="text-danger"><i class="fa-solid fa-circle-exclamation"></i> Ingestion Failed: ${err.message || err}</span>`;
        }
    }
}
