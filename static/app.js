document.addEventListener("DOMContentLoaded", () => {
    // Current State
    let currentBotId = 0; // 0 = Todos os Bots
    let allBots = [];
    let allLeads = [];

    // Tab Navigation
    const navItems = document.querySelectorAll(".nav-item");
    const tabContents = document.querySelectorAll(".tab-content");

    navItems.forEach(item => {
        item.addEventListener("click", () => {
            const targetTab = item.getAttribute("data-tab");
            
            navItems.forEach(n => n.classList.remove("active"));
            tabContents.forEach(c => c.classList.remove("active"));

            item.classList.add("active");
            document.getElementById(targetTab).classList.add("active");

            updateHeaderTitle(targetTab);

            if (targetTab === "tab-dashboard") loadDashboardStats();
            if (targetTab === "tab-my-bots") loadMyBots();
            if (targetTab === "tab-funnels") loadFunnelSteps();
            if (targetTab === "tab-broadcast") loadBroadcasts();
            if (targetTab === "tab-leads") loadLeads();
            if (targetTab === "tab-settings") updateGeneratedLink();
        });
    });

    // Global Bot Selector in Sidebar
    const globalBotSelector = document.getElementById("globalBotSelector");
    globalBotSelector.addEventListener("change", (e) => {
        currentBotId = parseInt(e.target.value) || 0;
        loadDashboardStats();
        loadFunnelSteps();
        loadLeads();
    });

    function updateHeaderTitle(tabId) {
        const titleEl = document.getElementById("headerTitle");
        const subEl = document.getElementById("headerSub");

        switch (tabId) {
            case "tab-dashboard":
                titleEl.textContent = "Dashboard de Desempenho Multi-Bot";
                subEl.textContent = "Acompanhe a captura de leads e automações em tempo real";
                break;
            case "tab-my-bots":
                titleEl.textContent = "Gerenciador de Bots Telegram";
                subEl.textContent = "Conecte e monitore múltiplos bots rodando simultaneamente";
                break;
            case "tab-funnels":
                titleEl.textContent = "Editor de Funis de Vendas";
                subEl.textContent = "Configure funis universais ou exclusivos por bot";
                break;
            case "tab-broadcast":
                titleEl.textContent = "Disparo em Massa (Broadcast)";
                subEl.textContent = "Envie campanhas para leads de um bot específico ou para todos";
                break;
            case "tab-leads":
                titleEl.textContent = "Base de Leads Capturados";
                subEl.textContent = "Filtre e analise leads agrupados por bot e campanha de anúncio";
                break;
            case "tab-settings":
                titleEl.textContent = "Gerador de Links de Anúncio";
                subEl.textContent = "Crie links rastreáveis para botões de anúncio do Facebook/Instagram";
                break;
        }
    }

    function showToast(message, type = "info") {
        const container = document.getElementById("toastContainer");
        const toast = document.createElement("div");
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        container.appendChild(toast);

        setTimeout(() => toast.remove(), 3500);
    }

    // 1. DASHBOARD STATS & BOT SYNC
    async function loadDashboardStats() {
        try {
            const res = await fetch(`/api/stats?bot_id=${currentBotId}`);
            const data = await res.json();
            const summary = data.summary || {};

            allBots = summary.bots || [];

            // Update Summary Counters
            document.getElementById("valTotalBots").textContent = summary.total_bots || 0;
            document.getElementById("valTotalLeads").textContent = summary.total_leads || 0;
            document.getElementById("valLeadsToday").textContent = summary.leads_today || 0;
            document.getElementById("valTotalBroadcasts").textContent = summary.total_broadcasts || 0;

            // Populate Bot Selectors everywhere
            syncBotSelectors(allBots);

            // Campaigns List
            const campaignContainer = document.getElementById("campaignsContainer");
            if (summary.campaigns && summary.campaigns.length > 0) {
                campaignContainer.innerHTML = summary.campaigns.map(c => `
                    <div class="campaign-item">
                        <span class="campaign-tag"><i class="fa-solid fa-bullseye"></i> ${c.campaign_source}</span>
                        <span class="campaign-count">${c.count} leads</span>
                    </div>
                `).join("");
            } else {
                campaignContainer.innerHTML = `<div class="empty-state"><p>Nenhuma campanha de tráfego iniciada.</p></div>`;
            }

            // Dashboard Bots Overview
            const dashBotsContainer = document.getElementById("dashBotsContainer");
            if (allBots.length > 0) {
                dashBotsContainer.innerHTML = allBots.map(b => `
                    <div class="campaign-item">
                        <div>
                            <strong>${b.name}</strong>
                            <span style="font-size: 11px; color: #06b6d4; display: block;">@${b.username}</span>
                        </div>
                        <span class="badge ${b.status === 'active' ? 'green' : 'yellow'}">${b.status}</span>
                    </div>
                `).join("");
            } else {
                dashBotsContainer.innerHTML = `<div class="empty-state"><p>Nenhum bot conectado. Vá na aba "Meus Bots" para adicionar!</p></div>`;
            }

            updateGeneratedLink();

        } catch (err) {
            console.error("Erro ao carregar estatísticas:", err);
        }
    }

    function syncBotSelectors(bots) {
        // Global Selector in Sidebar
        const prevGlobalVal = globalBotSelector.value;
        globalBotSelector.innerHTML = `<option value="0">🌐 Todos os Bots (${bots.length})</option>`;
        bots.forEach(b => {
            const opt = document.createElement("option");
            opt.value = b.id;
            opt.textContent = `🤖 ${b.name} (@${b.username})`;
            globalBotSelector.appendChild(opt);
        });
        globalBotSelector.value = prevGlobalVal || "0";

        // Funnel Scope Selector
        const funnelScope = document.getElementById("funnelScopeSelect");
        const stepScope = document.getElementById("stepBotScope");
        const linkBotSelect = document.getElementById("linkTargetBotSelect");
        const leadBotSelect = document.getElementById("leadBotFilter");
        const broadcastBotSelect = document.getElementById("broadcastTargetBot");

        [funnelScope, stepScope].forEach(sel => {
            if (!sel) return;
            const currentVal = sel.value;
            sel.innerHTML = `<option value="0">🌐 Funil Global (Usado por todos os bots por padrão)</option>`;
            bots.forEach(b => {
                const opt = document.createElement("option");
                opt.value = b.id;
                opt.textContent = `🎯 Funil Exclusivo para @${b.username}`;
                sel.appendChild(opt);
            });
            sel.value = currentVal || "0";
        });

        // Link Generator Bot Selector
        if (linkBotSelect) {
            linkBotSelect.innerHTML = bots.length > 0 ? "" : `<option value="">Nenhum bot conectado</option>`;
            bots.forEach(b => {
                const opt = document.createElement("option");
                opt.value = b.username;
                opt.textContent = `🤖 @${b.username} (${b.name})`;
                linkBotSelect.appendChild(opt);
            });
        }

        // Leads & Broadcast Bot Filters
        [leadBotSelect, broadcastBotSelect].forEach(sel => {
            if (!sel) return;
            const cur = sel.value;
            sel.innerHTML = `<option value="0">🌐 Todos os Bots</option>`;
            bots.forEach(b => {
                const opt = document.createElement("option");
                opt.value = b.id;
                opt.textContent = `🤖 @${b.username}`;
                sel.appendChild(opt);
            });
            sel.value = cur || "0";
        });
    }

    // 2. MEUS BOTS TAB
    async function loadMyBots() {
        try {
            const res = await fetch("/api/bots");
            const data = await res.json();
            allBots = data.bots || [];

            const container = document.getElementById("myBotsListContainer");
            if (allBots.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <i class="fa-solid fa-robot"></i>
                        <p>Nenhum bot conectado ainda. Cole o Token do BotFather ao lado para conectar seu primeiro bot!</p>
                    </div>
                `;
                return;
            }

            container.innerHTML = allBots.map(b => `
                <div class="bot-card-item">
                    <div class="bot-card-info">
                        <div class="bot-avatar"><i class="fa-solid fa-robot"></i></div>
                        <div class="bot-details">
                            <h4>${b.name}</h4>
                            <span>@${b.username}</span>
                        </div>
                    </div>
                    <div style="display: flex; gap: 8px; align-items: center;">
                        <span class="badge ${b.status === 'active' ? 'green' : 'yellow'}">${b.status}</span>
                        <button class="btn btn-secondary btn-sm delete-bot-btn" data-id="${b.id}">
                            <i class="fa-solid fa-trash" style="color: #f43f5e;"></i>
                        </button>
                    </div>
                </div>
            `).join("");

            document.querySelectorAll(".delete-bot-btn").forEach(btn => {
                btn.addEventListener("click", async () => {
                    const id = btn.getAttribute("data-id");
                    if (confirm("Tem certeza que deseja remover este bot? Ele deixará de responder mensagens.")) {
                        await fetch(`/api/bots/${id}`, { method: "DELETE" });
                        showToast("Bot desconectado com sucesso!", "success");
                        loadMyBots();
                        loadDashboardStats();
                    }
                });
            });

        } catch (err) {
            console.error("Erro ao carregar bots:", err);
        }
    }

    // ADD NEW BOT FORM
    const addBotForm = document.getElementById("addBotForm");
    const btnTestNewBotToken = document.getElementById("btnTestNewBotToken");
    const newBotTokenInput = document.getElementById("newBotTokenInput");
    const newBotTestResult = document.getElementById("newBotTestResult");

    btnTestNewBotToken.addEventListener("click", async () => {
        const token = newBotTokenInput.value.trim();
        if (!token) return showToast("Insira o token do bot", "error");

        newBotTestResult.innerHTML = `<span><i class="fa-solid fa-spinner fa-spin"></i> Testando token...</span>`;

        try {
            const res = await fetch("/api/test-token", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ token })
            });
            const data = await res.json();
            if (data.valid) {
                newBotTestResult.innerHTML = `<span style="color: #10b981; font-weight:600;"><i class="fa-solid fa-check-circle"></i> Token Válido! Bot: ${data.bot_name} (@${data.username})</span>`;
            } else {
                newBotTestResult.innerHTML = `<span style="color: #f43f5e; font-weight:600;"><i class="fa-solid fa-times-circle"></i> Token Inválido: ${data.error}</span>`;
            }
        } catch (err) {
            newBotTestResult.innerHTML = `<span style="color: #f43f5e;">Erro na verificação.</span>`;
        }
    });

    addBotForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const token = newBotTokenInput.value.trim();
        if (!token) return;

        try {
            const res = await fetch("/api/bots", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ token })
            });
            const data = await res.json();
            if (data.success) {
                showToast(`🤖 ${data.message}`, "success");
                addBotForm.reset();
                newBotTestResult.innerHTML = "";
                loadMyBots();
                loadDashboardStats();
            }
        } catch (err) {
            showToast("Erro ao conectar novo bot", "error");
        }
    });

    // 3. FUNNEL STEPS BUILDER
    const funnelScopeSelect = document.getElementById("funnelScopeSelect");
    funnelScopeSelect.addEventListener("change", () => loadFunnelSteps());

    async function loadFunnelSteps() {
        const scopeBotId = parseInt(funnelScopeSelect.value) || 0;
        const subTitle = document.getElementById("funnelScopeSubtitle");
        
        if (scopeBotId === 0) {
            subTitle.innerHTML = `Configurando: <strong>Funil Global Compartilhado (Usado por todos os bots)</strong>`;
        } else {
            const selectedBot = allBots.find(b => b.id === scopeBotId);
            subTitle.innerHTML = `Configurando: <strong>Funil Exclusivo para @${selectedBot ? selectedBot.username : 'Bot'}</strong>`;
        }

        try {
            const res = await fetch(`/api/funnel?bot_id=${scopeBotId}`);
            const data = await res.json();
            const container = document.getElementById("funnelStepsList");

            if (!data.steps || data.steps.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <p>Nenhum passo configurado para este contexto ainda. Clique em "Novo Passo" para adicionar!</p>
                    </div>
                `;
                return;
            }

            container.innerHTML = data.steps.map(step => `
                <div class="step-card">
                    <div class="step-number-badge">${step.step_number}</div>
                    <div class="step-content">
                        <h4>${step.title}</h4>
                        <p>${step.message_text}</p>
                        ${step.media_url ? `<span class="badge" style="background: rgba(6, 182, 212, 0.15); color: #06b6d4;"><i class="fa-solid fa-image"></i> Mídia: ${step.media_url}</span>` : ''}
                        <div class="step-buttons-preview">
                            ${(step.buttons || []).map(b => `
                                <span class="preview-btn">
                                    <i class="fa-solid fa-hand-pointer"></i> ${b.text} ${b.url ? `(URL)` : `(Próx: ${b.callback_data})`}
                                </span>
                            `).join("")}
                        </div>
                    </div>
                    <div class="step-actions">
                        <button class="btn btn-secondary btn-sm edit-step-btn" data-step='${JSON.stringify(step)}'>
                            <i class="fa-solid fa-pen"></i>
                        </button>
                        <button class="btn btn-secondary btn-sm delete-step-btn" data-id="${step.id}">
                            <i class="fa-solid fa-trash" style="color: #f43f5e;"></i>
                        </button>
                    </div>
                </div>
            `).join("");

            document.querySelectorAll(".edit-step-btn").forEach(btn => {
                btn.addEventListener("click", () => {
                    const stepData = JSON.parse(btn.getAttribute("data-step"));
                    openStepModal(stepData);
                });
            });

            document.querySelectorAll(".delete-step-btn").forEach(btn => {
                btn.addEventListener("click", async () => {
                    const id = btn.getAttribute("data-id");
                    if (confirm("Remover este passo do funil?")) {
                        await fetch(`/api/funnel/${id}`, { method: "DELETE" });
                        showToast("Passo removido!", "success");
                        loadFunnelSteps();
                    }
                });
            });

        } catch (err) {
            console.error("Erro ao carregar passos do funil:", err);
        }
    }

    // STEP MODAL LOGIC
    const stepModal = document.getElementById("stepModal");
    const btnAddStepModal = document.getElementById("btnAddStepModal");
    const btnCloseStepModal = document.getElementById("btnCloseStepModal");
    const btnCancelStepModal = document.getElementById("btnCancelStepModal");
    const btnAddButtonRow = document.getElementById("btnAddButtonRow");
    const buttonsContainer = document.getElementById("buttonsEditorContainer");

    btnAddStepModal.addEventListener("click", () => openStepModal());
    btnCloseStepModal.addEventListener("click", () => closeModal());
    btnCancelStepModal.addEventListener("click", () => closeModal());

    function openStepModal(step = null) {
        const scopeBotId = parseInt(funnelScopeSelect.value) || 0;
        document.getElementById("stepId").value = step ? step.id : "";
        document.getElementById("stepBotScope").value = step ? step.bot_id : scopeBotId;
        document.getElementById("stepNumber").value = step ? step.step_number : 1;
        document.getElementById("stepTitle").value = step ? step.title : "";
        document.getElementById("stepMessage").value = step ? step.message_text : "";
        document.getElementById("stepMedia").value = step ? step.media_url || "" : "";

        buttonsContainer.innerHTML = "";
        if (step && step.buttons && step.buttons.length > 0) {
            step.buttons.forEach(b => addButtonRow(b.text, b.url || "", b.callback_data || ""));
        } else {
            addButtonRow("🚀 Ir para o Próximo Passo", "", "next_step_2");
        }

        stepModal.classList.add("active");
    }

    function closeModal() { stepModal.classList.remove("active"); }

    function addButtonRow(text = "", url = "", callback = "") {
        const row = document.createElement("div");
        row.className = "button-row";
        row.style.display = "flex";
        row.style.gap = "8px";
        row.style.marginBottom = "8px";
        row.innerHTML = `
            <input type="text" placeholder="Texto do Botão" value="${text}" class="btn-text-input" style="flex:1;">
            <input type="text" placeholder="URL ou callback (ex: next_step_2)" value="${url || callback}" class="btn-target-input" style="flex:1;">
            <button type="button" class="btn btn-secondary btn-sm remove-btn-row">&times;</button>
        `;
        buttonsContainer.appendChild(row);
        row.querySelector(".remove-btn-row").addEventListener("click", () => row.remove());
    }

    btnAddButtonRow.addEventListener("click", () => addButtonRow());

    document.getElementById("stepForm").addEventListener("submit", async (e) => {
        e.preventDefault();
        const buttons = [];
        document.querySelectorAll(".button-row").forEach(row => {
            const txt = row.querySelector(".btn-text-input").value.trim();
            const target = row.querySelector(".btn-target-input").value.trim();
            if (txt) {
                if (target.startsWith("http://") || target.startsWith("https://")) {
                    buttons.push({ text: txt, url: target });
                } else {
                    buttons.push({ text: txt, callback_data: target || "next_step_2" });
                }
            }
        });

        const payload = {
            bot_id: parseInt(document.getElementById("stepBotScope").value) || 0,
            step_number: parseInt(document.getElementById("stepNumber").value),
            title: document.getElementById("stepTitle").value,
            message_text: document.getElementById("stepMessage").value,
            media_url: document.getElementById("stepMedia").value,
            delay_seconds: 0,
            buttons: buttons
        };

        try {
            const res = await fetch("/api/funnel", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (data.success) {
                showToast("Passo do funil salvo!", "success");
                closeModal();
                loadFunnelSteps();
            }
        } catch (err) {
            showToast("Erro ao salvar passo do funil", "error");
        }
    });

    // 4. BROADCAST
    document.getElementById("broadcastForm").addEventListener("submit", async (e) => {
        e.preventDefault();
        const payload = {
            bot_id: parseInt(document.getElementById("broadcastTargetBot").value) || 0,
            title: document.getElementById("broadcastTitle").value,
            message_text: document.getElementById("broadcastMessage").value,
            filter_campaign: document.getElementById("broadcastFilter").value
        };

        try {
            const res = await fetch("/api/broadcast", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (data.success) {
                showToast("⚡ Disparo em massa iniciado!", "success");
                document.getElementById("broadcastForm").reset();
                loadBroadcasts();
            }
        } catch (err) {
            showToast("Erro ao iniciar disparo", "error");
        }
    });

    async function loadBroadcasts() {
        try {
            const res = await fetch("/api/broadcasts");
            const data = await res.json();
            const container = document.getElementById("broadcastHistoryContainer");

            if (!data.broadcasts || data.broadcasts.length === 0) {
                container.innerHTML = `<div class="empty-state"><p>Nenhum disparo realizado até o momento.</p></div>`;
                return;
            }

            container.innerHTML = data.broadcasts.map(b => `
                <div class="campaign-item">
                    <div>
                        <strong>${b.title}</strong>
                        <span style="font-size: 11px; color: #94a3b8; display: block;">Escopo Bot #${b.bot_id || 'Todos'} &bull; Campanha: ${b.filter_campaign}</span>
                    </div>
                    <span class="badge ${b.status === 'completed' ? 'green' : 'yellow'}">
                        ${b.sent_count}/${b.total_target} Enviados (${b.status})
                    </span>
                </div>
            `).join("");
        } catch (err) {
            console.error("Erro ao carregar histórico de disparos:", err);
        }
    }

    // 5. LEADS TABLE
    const leadBotFilter = document.getElementById("leadBotFilter");
    const leadCampaignFilter = document.getElementById("leadCampaignFilter");
    const leadSearchInput = document.getElementById("leadSearchInput");

    leadBotFilter.addEventListener("change", loadLeads);
    leadCampaignFilter.addEventListener("change", loadLeads);
    leadSearchInput.addEventListener("input", () => renderLeadsTable(allLeads));

    async function loadLeads() {
        try {
            const bId = leadBotFilter.value || 0;
            const camp = leadCampaignFilter.value || "all";
            const res = await fetch(`/api/leads?bot_id=${bId}&campaign=${camp}`);
            const data = await res.json();
            allLeads = data.leads || [];
            renderLeadsTable(allLeads);
        } catch (err) {
            console.error("Erro ao carregar leads:", err);
        }
    }

    function renderLeadsTable(leads) {
        const tbody = document.getElementById("leadsTableBody");
        const search = leadSearchInput.value.toLowerCase();

        const filtered = leads.filter(l => 
            (l.first_name && l.first_name.toLowerCase().includes(search)) ||
            (l.username && l.username.toLowerCase().includes(search))
        );

        if (filtered.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-center py-4">Nenhum lead encontrado.</td></tr>`;
            return;
        }

        tbody.innerHTML = filtered.map(l => `
            <tr>
                <td><span class="badge cyan">@${l.bot_username || 'bot'}</span></td>
                <td><code>${l.telegram_id}</code></td>
                <td><strong>${l.first_name || ''} ${l.last_name || ''}</strong></td>
                <td>${l.username ? `@${l.username}` : '<span style="color:#64748b;">-</span>'}</td>
                <td><span class="badge">${l.campaign_source}</span></td>
                <td>Passo ${l.current_step}</td>
                <td>${new Date(l.created_at).toLocaleDateString("pt-BR")}</td>
            </tr>
        `).join("");
    }

    // 6. LINK GENERATOR
    const linkBotSelect = document.getElementById("linkTargetBotSelect");
    const campaignInput = document.getElementById("campaignInput");
    const linkOutput = document.getElementById("generatedLinkOutput");
    const btnCopyLink = document.getElementById("btnCopyLink");

    function updateGeneratedLink() {
        const campaign = campaignInput.value.trim() || "fb_campanha_01";
        const botUsername = linkBotSelect.value || (allBots.length > 0 ? allBots[0].username : "SeuBotUsername");
        linkOutput.value = `https://t.me/${botUsername}?start=${campaign}`;
    }

    linkBotSelect.addEventListener("change", updateGeneratedLink);
    campaignInput.addEventListener("input", updateGeneratedLink);

    btnCopyLink.addEventListener("click", () => {
        linkOutput.select();
        navigator.clipboard.writeText(linkOutput.value);
        showToast("📋 Link do Anúncio copiado!", "success");
    });

    // Navigation buttons inside cards
    document.getElementById("btnQuickAddBot").addEventListener("click", () => {
        document.getElementById("btn-tab-my-bots").click();
    });
    document.getElementById("btnGoToBots").addEventListener("click", () => {
        document.getElementById("btn-tab-my-bots").click();
    });
    document.getElementById("btnRefreshData").addEventListener("click", () => {
        loadDashboardStats();
        showToast("Dados atualizados!", "info");
    });

    // Initial Load
    loadDashboardStats();
});
