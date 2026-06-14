// AFIS System Client Logic - Dynamic UI & Chart.js Integration

const API_BASE = "http://127.0.0.1:8000/api";
let cashflowChart = null;

document.addEventListener("DOMContentLoaded", () => {
    // 1. Initialize Tabs
    initTabs();
    
    // 2. Fetch Dashboard and Compliance Data
    fetchDashboardData();
    fetchComplianceData();
    
    // 3. Setup Drag and Drop Ingestion
    initFileIngestion();
});

// --- TAB SYSTEM ---
function initTabs() {
    const tabs = document.querySelectorAll(".nav-btn");
    const panels = document.querySelectorAll(".tab-panel");
    const pageTitle = document.getElementById("page-title");
    const pageSubtitle = document.getElementById("page-subtitle");
    
    const meta = {
        "dashboard": { title: "Executive Dashboard", subtitle: "Overview of historical accounts and ML cash projections." },
        "chat": { title: "AI CFO Analyst Agent", subtitle: "Interact with our cognitive financial assistant to audit ledger." },
        "compliance": { title: "NIST Compliance & Ingestion", subtitle: "Audit logs console and raw data ETL pipeline ingestion." }
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

// --- FETCH DASHBOARD DATA ---
async function fetchDashboardData() {
    try {
        // Fetch KPIs
        const kpisRes = await fetch(`${API_BASE}/kpis`);
        const kpis = await kpisRes.json();
        
        document.getElementById("kpi-cash").textContent = `$${kpis.current_cash.toLocaleString('en-US', { minimumFractionDigits: 2 })}`;
        document.getElementById("kpi-runway").textContent = typeof kpis.runway === 'number' ? `${kpis.runway} Months` : kpis.runway;
        document.getElementById("kpi-burnrate").textContent = kpis.burn_rate > 0 ? `Burn: $${kpis.burn_rate.toLocaleString('en-US')}/mo` : `Cash Surplus: $${Math.abs(kpis.net_cash_flow_3m).toLocaleString('en-US')}/mo`;
        document.getElementById("kpi-margin").textContent = `${kpis.net_margin_percent}%`;
        document.getElementById("kpi-netprofit").textContent = `Net: $${kpis.net_profit.toLocaleString('en-US', { minimumFractionDigits: 2 })}`;
        
        // Fetch Transactions
        const txRes = await fetch(`${API_BASE}/transactions`);
        const transactions = await txRes.json();
        renderTransactions(transactions);
        
        // Generate Health Advisory Warnings
        renderAdvisory(kpis);
        
        // Fetch Forecasts and Build Chart
        const forecastRes = await fetch(`${API_BASE}/forecast`);
        const forecasts = await forecastRes.json();
        buildChart(transactions, forecasts);
        
    } catch (err) {
        console.error("Failed to load dashboard data:", err);
    }
}

// --- RENDER TRANSACTIONS ---
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

// --- RENDER ADVISORY ---
function renderAdvisory(kpis) {
    const container = document.getElementById("advisory-container");
    container.innerHTML = "";
    
    const items = [];
    
    // Runway thresholds
    if (typeof kpis.runway === 'number') {
        if (kpis.runway < 6) {
            items.push({
                type: "red",
                icon: "fa-triangle-exclamation",
                text: `**Critical Runway Alert:** Cash will run out in **${kpis.runway} months**. We suggest pausing new hires immediately.`
            });
        } else if (kpis.runway < 12) {
            items.push({
                type: "orange",
                icon: "fa-circle-exclamation",
                text: `**Caution Runway:** Runway sits at **${kpis.runway} months**. Monitor expansion costs.`
            });
        } else {
            items.push({
                type: "green",
                icon: "fa-circle-check",
                text: `**Healthy Cash Position:** Cash reserves project **${kpis.runway} months** of runway under current rates.`
            });
        }
    } else {
        items.push({
            type: "green",
            icon: "fa-circle-check",
            text: `**Cash Flow Positive:** Net income is positive. Your runway is infinite under stable operations.`
        });
    }
    
    // Profit margin threshold
    if (kpis.net_margin_percent < 15) {
        items.push({
            type: "orange",
            icon: "fa-chart-line-down",
            text: `**Low Margin Warning:** Net margin is **${kpis.net_margin_percent}%**. Review AWS infrastructure cost and billing hours.`
        });
    } else {
        items.push({
            type: "green",
            icon: "fa-piggy-bank",
            text: `**Leverage Stable:** Net margin is **${kpis.net_margin_percent}%**, ensuring robust margin retention.`
        });
    }
    
    items.forEach(item => {
        const div = document.createElement("div");
        div.className = `advisory-alert alert-${item.type}`;
        
        // Simple markdown parser helper for bolding inside advisory
        const parsedText = item.text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        div.innerHTML = `
            <i class="fa-solid ${item.icon}" style="margin-top:2px;"></i>
            <div>${parsedText}</div>
        `;
        container.appendChild(div);
    });
}

// --- RENDER CHART.JS GRAPH ---
function buildChart(historical, forecasts) {
    const ctx = document.getElementById("cashflowChart").getContext("2d");
    
    // Group historical transactions by month (last 6 months for chart readability)
    const monthlyHist = {};
    historical.forEach(tx => {
        const m = tx.date.substring(0, 7);
        if (!monthlyHist[m]) monthlyHist[m] = { income: 0, expense: 0 };
        if (tx.type === 'income') monthlyHist[m].income += tx.amount;
        else monthlyHist[m].expense += tx.amount;
    });
    
    // Sort historical months
    const sortedHistMonths = Object.keys(monthlyHist).sort();
    
    const labels = [];
    const actualIncome = [];
    const actualExpense = [];
    const predIncome = [];
    const predExpense = [];
    
    // Populate historical aggregates
    sortedHistMonths.forEach(m => {
        labels.push(m);
        actualIncome.push(monthlyHist[m].income);
        actualExpense.push(monthlyHist[m].expense);
        predIncome.push(null); // No prediction for past
        predExpense.push(null);
    });
    
    // Pivot connecting point for chart continuity
    if (labels.length > 0) {
        const lastMonth = labels[labels.length - 1];
        predIncome[labels.length - 1] = monthlyHist[lastMonth].income;
        predExpense[labels.length - 1] = monthlyHist[lastMonth].expense;
    }
    
    // Populate predictions
    forecasts.forEach(f => {
        labels.push(f.month);
        actualIncome.push(null);
        actualExpense.push(null);
        predIncome.push(f.income);
        predExpense.push(f.expense);
    });
    
    if (cashflowChart) {
        cashflowChart.destroy();
    }
    
    // Gradient definitions
    const gradientInc = ctx.createLinearGradient(0, 0, 0, 400);
    gradientInc.addColorStop(0, 'rgba(16, 185, 129, 0.4)');
    gradientInc.addColorStop(1, 'rgba(16, 185, 129, 0.0)');
    
    const gradientExp = ctx.createLinearGradient(0, 0, 0, 400);
    gradientExp.addColorStop(0, 'rgba(244, 63, 94, 0.4)');
    gradientExp.addColorStop(1, 'rgba(244, 63, 94, 0.0)');
    
    cashflowChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Actual Income',
                    data: actualIncome,
                    borderColor: '#10b981',
                    backgroundColor: gradientInc,
                    borderWidth: 3,
                    fill: true,
                    tension: 0.35,
                    spanGaps: false
                },
                {
                    label: 'Actual Expense',
                    data: actualExpense,
                    borderColor: '#f43f5e',
                    backgroundColor: gradientExp,
                    borderWidth: 3,
                    fill: true,
                    tension: 0.35,
                    spanGaps: false
                },
                {
                    label: 'Predicted Income',
                    data: predIncome,
                    borderColor: '#10b981',
                    borderDash: [5, 5],
                    borderWidth: 2,
                    pointRadius: 2,
                    fill: false,
                    tension: 0.35,
                    spanGaps: true
                },
                {
                    label: 'Predicted Expense',
                    data: predExpense,
                    borderColor: '#f43f5e',
                    borderDash: [5, 5],
                    borderWidth: 2,
                    pointRadius: 2,
                    fill: false,
                    tension: 0.35,
                    spanGaps: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#94a3b8' }
                },
                y: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: {
                        color: '#94a3b8',
                        callback: function(value) { return '$' + value.toLocaleString(); }
                    }
                }
            }
        }
    });
}

// --- CHAT SYSTEM LOGIC ---
async function sendMessage() {
    const input = document.getElementById("chat-input");
    const text = input.value.strip ? input.value.strip() : input.value.trim();
    if (!text) return;
    
    appendChatMessage(text, "outgoing");
    input.value = "";
    
    // Add typing loader bubble
    const loadingBubble = appendChatMessage("Analyzing transactions...", "incoming loading-bubble");
    
    try {
        const res = await fetch(`${API_BASE}/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: text })
        });
        const data = await res.json();
        
        // Remove typing bubble and show real output
        loadingBubble.remove();
        
        // Simple markdown link conversion for chat outputs
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
    
    if (isHtml) {
        bubble.innerHTML = content;
    } else {
        bubble.textContent = content;
    }
    
    messageDiv.appendChild(bubble);
    historyBox.appendChild(messageDiv);
    historyBox.scrollTop = historyBox.scrollHeight;
    
    return messageDiv;
}

// --- FETCH COMPLIANCE & LOGS DATA ---
async function fetchComplianceData() {
    try {
        const res = await fetch(`${API_BASE}/nist-compliance`);
        const data = await res.json();
        
        // Render NIST Cards
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
        
        // Render system logs
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
                ${log.details ? `<br><span class="text-muted" style="margin-left: 20px;">➔ ${log.details}</span>` : ""}
            `;
            consoleBox.appendChild(div);
        });
        
    } catch (err) {
        console.error("Failed to load compliance audit logs:", err);
    }
}

// --- FILE UPLOAD ETL ---
function initFileIngestion() {
    const fileInput = document.getElementById("file-input");
    const dropZone = document.getElementById("drop-zone");
    const statusDiv = document.getElementById("upload-status");
    
    // Click browse triggers input
    fileInput.addEventListener("change", (e) => {
        if (e.target.files.length > 0) {
            uploadFile(e.target.files[0]);
        }
    });
    
    // Drag events
    ["dragenter", "dragover"].forEach(event => {
        dropZone.addEventListener(event, (e) => {
            e.preventDefault();
            dropZone.classList.add("dragover");
        }, false);
    });
    
    ["dragleave", "drop"].forEach(event => {
        dropZone.addEventListener(event, (e) => {
            e.preventDefault();
            dropZone.classList.remove("dragover");
        }, false);
    });
    
    dropZone.addEventListener("drop", (e) => {
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            uploadFile(files[0]);
        }
    });
    
    async function uploadFile(file) {
        statusDiv.innerHTML = `<div class="loading-spinner"></div><p>Executing ETL pipeline operations...</p>`;
        
        const formData = new FormData();
        formData.append("file", file);
        
        try {
            const res = await fetch(`${API_BASE}/ingest`, {
                method: "POST",
                body: formData
            });
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
                
                // Refresh dashboard to show loaded values
                fetchDashboardData();
                fetchComplianceData();
            } else {
                throw new Error(data.message || "Failed ingestion");
            }
        } catch (err) {
            statusDiv.innerHTML = `<span class="text-danger"><i class="fa-solid fa-circle-exclamation"></i> Ingestion Failed: ${err.message || err}</span>`;
        }
    }
}
