document.addEventListener("DOMContentLoaded", () => {
    // Current state
    let botInfo = null;
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

            // Fetch data based on tab
            if (targetTab === "tab-dashboard") loadDashboardStats();
            if (targetTab === "tab-funnels") loadFunnelSteps();
            if (targetTab === "tab-broadcast") loadBroadcasts();
            if (targetTab === "tab-leads") loadLeads();
            if (targetTab === "tab-settings") updateGeneratedLink();
        });
    });

    function updateHeaderTitle(tabId) {
        const titleEl = document.getElementById("headerTitle");
        const subEl = document.getElementById("headerSub");

        switch (tabId) {
            case "tab-dashboard":
                titleEl.textContent = "Dashboard de Desempenho";
                subEl.textContent = "Acompanhe seus leads de tráfego pago e automações em tempo real";
                break;
            case "tab-funnels":
                titleEl.textContent = "Construtor de Funis de Vendas";
                subEl.textContent = "Gerencie os passos e mensagens automatizadas que os leads recebem";
                break;
            case "tab-broadcast":
                titleEl.textContent = "Disparo em Massa (Broadcast)";
                subEl.textContent = "Envie campanhas para a sua base de leads com segurança";
                break;
            case "tab-leads":
                titleEl.textContent = "Base de Leads Capturados";
                subEl.textContent = "Visualize e filtre todos os leads que entraram pelos seus anúncios";
                break;
            case "tab-settings":
                titleEl.textContent = "Gerador de Links & Token";
                subEl.textContent = "Crie links rastreáveis para o Facebook Ads e gerencie o Bot Token";
                break;
        }
    }

    // Toast Notifications
    function showToast(message, type = "info") {
        const container = document.getElementById("toastContainer");
        const toast = document.createElement("div");
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        container.appendChild(toast);

        setTimeout(() => {
            toast.remove();
        }, 3500);
    }

    // 1. DASHBOARD STATS
    async function loadDashboardStats() {
        try {
            const res = await fetch("/api/stats");
            const data = await res.json();

            // Status Card
            const statusDot = document.getElementById("statusDot");
            const statusTitle = document.getElementById("botStatusTitle");
            const statusSub = document.getElementById("botStatusSub");

            if (data.is_token_set && data.bot_info) {
                botInfo = data.bot_info;
                statusDot.className = "status-indicator green";
                statusTitle.textContent = `@${data.bot_info.username}`;
                statusSub.textContent = "Bot Conectado & Polling";
            } else {
                statusDot.className = "status-indicator yellow";
                statusTitle.textContent = "Pendente";
                statusSub.textContent = "Insira o Bot Token";
            }

            // Summary Values
            const summary = data.summary || {};
            document.getElementById("valTotalLeads").textContent = summary.total_leads || 0;
            document.getElementById("valLeadsToday").textContent = summary.leads_today || 0;
            document.getElementById("valTotalSteps").textContent = summary.total_steps || 0;
            document.getElementById("valTotalBroadcasts").textContent = summary.total_broadcasts || 0;

            // Campaigns List
            const campaignContainer = document.getElementById("campaignsContainer");
            const campaignSelects = [document.getElementById("broadcastFilter"), document.getElementById("leadCampaignFilter")];

            campaignSelects.forEach(sel => {
                sel.innerHTML = `<option value="all">🌐 Todas as Campanhas</option>`;
            });

            if (summary.campaigns && summary.campaigns.length > 0) {
                campaignContainer.innerHTML = summary.campaigns.map(c => `
                    <div class="campaign-item">
                        <span class="campaign-tag"><i class="fa-solid fa-bullseye"></i> ${c.campaign_source}</span>
                        <span class="campaign-count">${c.count} leads</span>
                    </div>
                `).join("");

                summary.campaigns.forEach(c => {
                    campaignSelects.forEach(sel => {
                        const opt = document.createElement("option");
                        opt.value = c.campaign_source;
                        opt.textContent = `🎯 Campanha: ${c.campaign_source} (${c.count} leads)`;
                        sel.appendChild(opt);
                    });
                });
            } else {
                campaignContainer.innerHTML = `
                    <div class="empty-state">
                        <p>Nenhuma campanha registrada ainda. Crie um link de anúncio para rastrear!</p>
                    </div>
                `;
            }

            // Recent leads
            loadRecentLeads();
            updateGeneratedLink();

        } catch (err) {
            console.error("Erro ao carregar estatísticas:", err);
        }
    }

    async function loadRecentLeads() {
        try {
            const res = await fetch("/api/leads");
            const data = await res.json();
            allLeads = data.leads || [];

            const container = document.getElementById("recentLeadsContainer");
            if (allLeads.length > 0) {
                container.innerHTML = allLeads.slice(0, 5).map(l => `
                    <div class="campaign-item">
                        <div>
                            <strong>${l.first_name || 'Lead'} ${l.last_name || ''}</strong>
                            <span style="font-size: 11px; color: #94a3b8; display: block;">@${l.username || 'sem_username'}</span>
                        </div>
                        <span class="badge">${l.campaign_source}</span>
                    </div>
                `).join("");
            }
        } catch (err) {
            console.error("Erro ao carregar leads recentes:", err);
        }
    }

    // 2. FUNNEL STEPS BUILDER
    async function loadFunnelSteps() {
        try {
            const res = await fetch("/api/funnel");
            const data = await res.json();
            const container = document.getElementById("funnelStepsList");

            if (!data.steps || data.steps.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <p>Nenhum passo no funil ainda. Clique em "Novo Passo" para começar!</p>
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

            // Event listeners for Edit and Delete
            document.querySelectorAll(".edit-step-btn").forEach(btn => {
                btn.addEventListener("click", () => {
                    const stepData = JSON.parse(btn.getAttribute("data-step"));
                    openStepModal(stepData);
                });
            });

            document.querySelectorAll(".delete-step-btn").forEach(btn => {
                btn.addEventListener("click", async () => {
                    const id = btn.getAttribute("data-id");
                    if (confirm("Tem certeza que deseja remover este passo do funil?")) {
                        await fetch(`/api/funnel/${id}`, { method: "DELETE" });
                        showToast("Passo removido com sucesso!", "success");
                        loadFunnelSteps();
                    }
                });
            });

        } catch (err) {
            console.error("Erro ao carregar passos do funil:", err);
        }
    }

    // MODAL STEP EDITOR
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
        document.getElementById("stepId").value = step ? step.id : "";
        document.getElementById("stepNumber").value = step ? step.step_number : 1;
        document.getElementById("stepTitle").value = step ? step.title : "";
        document.getElementById("stepMessage").value = step ? step.message_text : "";
        document.getElementById("stepMedia").value = step ? step.media_url || "" : "";
        
        document.getElementById("modalStepTitle").textContent = step ? `Editar Passo ${step.step_number}` : "Adicionar Novo Passo ao Funil";

        buttonsContainer.innerHTML = "";
        if (step && step.buttons && step.buttons.length > 0) {
            step.buttons.forEach(b => addButtonRow(b.text, b.url || "", b.callback_data || ""));
        } else {
            addButtonRow("🚀 Ir para o Próximo Passo", "", "next_step_2");
        }

        stepModal.classList.add("active");
    }

    function closeModal() {
        stepModal.classList.remove("active");
    }

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

    // Submit Step Form
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
                showToast("Passo do funil salvo com sucesso!", "success");
                closeModal();
                loadFunnelSteps();
            }
        } catch (err) {
            showToast("Erro ao salvar passo do funil", "error");
        }
    });

    // 3. BROADCAST FORM & HISTORY
    const broadcastForm = document.getElementById("broadcastForm");
    broadcastForm.addEventListener("submit", async (e) => {
        e.preventDefault();

        const payload = {
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
                showToast("⚡ Disparo iniciado com sucesso!", "success");
                broadcastForm.reset();
                loadBroadcasts();
            }
        } catch (err) {
            showToast("Erro ao disparar mensagem", "error");
        }
    });

    async function loadBroadcasts() {
        try {
            const res = await fetch("/api/broadcasts");
            const data = await res.json();
            const container = document.getElementById("broadcastHistoryContainer");

            if (!data.broadcasts || data.broadcasts.length === 0) {
                container.innerHTML = `<div class="empty-state"><p>Nenhum disparo realizado até agora.</p></div>`;
                return;
            }

            container.innerHTML = data.broadcasts.map(b => `
                <div class="campaign-item">
                    <div>
                        <strong>${b.title}</strong>
                        <span style="font-size: 11px; color: #94a3b8; display: block;">Segmento: ${b.filter_campaign}</span>
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

    // 4. LEADS TABLE & FILTER
    async function loadLeads() {
        try {
            const campaignFilter = document.getElementById("leadCampaignFilter").value;
            const res = await fetch(`/api/leads?campaign=${campaignFilter}`);
            const data = await res.json();
            allLeads = data.leads || [];

            renderLeadsTable(allLeads);
        } catch (err) {
            console.error("Erro ao carregar lista de leads:", err);
        }
    }

    function renderLeadsTable(leads) {
        const tbody = document.getElementById("leadsTableBody");
        const search = document.getElementById("leadSearchInput").value.toLowerCase();

        const filtered = leads.filter(l => 
            (l.first_name && l.first_name.toLowerCase().includes(search)) ||
            (l.username && l.username.toLowerCase().includes(search))
        );

        if (filtered.length === 0) {
            tbody.innerHTML = `<tr><td colspan="6" class="text-center py-4">Nenhum lead encontrado.</td></tr>`;
            return;
        }

        tbody.innerHTML = filtered.map(l => `
            <tr>
                <td><code>${l.telegram_id}</code></td>
                <td><strong>${l.first_name || ''} ${l.last_name || ''}</strong></td>
                <td>${l.username ? `@${l.username}` : '<span style="color:#64748b;">-</span>'}</td>
                <td><span class="badge">${l.campaign_source}</span></td>
                <td>Passo ${l.current_step}</td>
                <td>${new Date(l.created_at).toLocaleDateString("pt-BR")}</td>
            </tr>
        `).join("");
    }

    document.getElementById("leadSearchInput").addEventListener("input", () => renderLeadsTable(allLeads));
    document.getElementById("leadCampaignFilter").addEventListener("change", loadLeads);

    // 5. DEEP LINK GENERATOR & TOKEN SETTINGS
    const campaignInput = document.getElementById("campaignInput");
    const linkOutput = document.getElementById("generatedLinkOutput");
    const btnCopyLink = document.getElementById("btnCopyLink");

    function updateGeneratedLink() {
        const campaign = campaignInput.value.trim() || "fb_campanha_01";
        const botUsername = botInfo ? botInfo.username : "SeuBotUsername";
        linkOutput.value = `https://t.me/${botUsername}?start=${campaign}`;
    }

    campaignInput.addEventListener("input", updateGeneratedLink);

    btnCopyLink.addEventListener("click", () => {
        linkOutput.select();
        navigator.clipboard.writeText(linkOutput.value);
        showToast("📋 Link do Anúncio copiado!", "success");
    });

    // TOKEN TESTING & SAVING
    const btnTestToken = document.getElementById("btnTestToken");
    const tokenInput = document.getElementById("botTokenInput");
    const testResultBox = document.getElementById("tokenTestResult");

    btnTestToken.addEventListener("click", async () => {
        const token = tokenInput.value.trim();
        if (!token) {
            showToast("Insira um token para testar", "error");
            return;
        }

        testResultBox.innerHTML = `<span><i class="fa-solid fa-spinner fa-spin"></i> Testando token na API do Telegram...</span>`;

        try {
            const res = await fetch("/api/test-token", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ token })
            });
            const data = await res.json();

            if (data.valid) {
                testResultBox.innerHTML = `
                    <div style="color: #10b981; font-weight: 600;">
                        <i class="fa-solid fa-circle-check"></i> Token Válido! Bot: ${data.bot_name} (@${data.username})
                    </div>
                `;
            } else {
                testResultBox.innerHTML = `
                    <div style="color: #f43f5e; font-weight: 600;">
                        <i class="fa-solid fa-circle-xmark"></i> Token Inválido: ${data.error}
                    </div>
                `;
            }
        } catch (err) {
            testResultBox.innerHTML = `<span style="color: #f43f5e;">Erro de conexão com o servidor.</span>`;
        }
    });

    document.getElementById("tokenForm").addEventListener("submit", async (e) => {
        e.preventDefault();
        const token = tokenInput.value.trim();
        if (!token) return;

        try {
            const res = await fetch("/api/settings/token", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ token })
            });
            const data = await res.json();
            if (data.success) {
                showToast("✅ Token salvo no arquivo .env!", "success");
                loadDashboardStats();
            }
        } catch (err) {
            showToast("Erro ao salvar token", "error");
        }
    });

    // Initial Load
    loadDashboardStats();
});
