/**
 * CivicScale - Enterprise Public Civil Service Platform & Predictive HPA
 * Ultra-Modern Light Civil Service Theme Architecture
 * 
 * 60% Dominant Base: Pastel Light Green (#F4F9F6)
 * 30% Structural Components: Solid Pure White (#FFFFFF) with Cream-Yellow Outline (#FDF9E2)
 * Core Typography: Deep Forest Slate Black (#1A2E26)
 * 10% Functional Accents: Mint Green (#10B981), Sage Blue (#3B82F6), Accent Gold (#EAB308)
 */

// Application State
const state = {
    // Public 311 Records
    publicRecords: [],
    totalRecords: 0,
    totalPages: 1,
    currentPage: 1,
    pageSize: 15,
    searchQuery: '',
    selectedAgency: 'ALL',
    selectedDistrict: 'ALL',
    selectedStatus: 'ALL',
    selectedPriority: 'ALL',
    sortBy: 'created_date',
    sortDir: 'desc',
    analytics: null,

    // Real-Time Telemetry & Predictive Cache
    cluster: null,
    hpa: null,
    predictive: null,
    activeTab: 'tab-dashboard',
    historyRps: [],
    historyReplicas: [],
    maxHistoryPoints: 25,
    wsConnected: false,
    pollIntervalId: null
};

// Cached DOM References
let elements = {};

function getElements() {
    return {
        tabs: document.querySelectorAll('.nav-tab'),
        panes: document.querySelectorAll('.tab-pane'),
        clusterClock: document.getElementById('cluster-clock'),
        topSearchInput: document.getElementById('top-search-input'),

        // Public Table & Filters
        publicSearchInput: document.getElementById('public-search-input'),
        filterAgency: document.getElementById('filter-agency'),
        filterDistrict: document.getElementById('filter-district'),
        filterStatus: document.getElementById('filter-status'),
        filterPriority: document.getElementById('filter-priority'),
        sortBySelect: document.getElementById('sort-by-select'),
        btnResetFilters: document.getElementById('btn-reset-filters'),
        btnExportCsv: document.getElementById('btn-export-csv'),
        btnExportJson: document.getElementById('btn-export-json'),
        publicTableBody: document.getElementById('public-table-body'),
        paginationInfo: document.getElementById('pagination-info'),
        pageIndicator: document.getElementById('page-indicator'),
        btnPrevPage: document.getElementById('btn-prev-page'),
        btnNextPage: document.getElementById('btn-next-page'),
        clickableHeaders: document.querySelectorAll('.clickable-th'),

        // Global KPIs & Radial Rings
        kpiTotalRecords: document.getElementById('kpi-total-records'),
        kpiResolutionRate: document.getElementById('kpi-resolution-rate'),
        kpiResolvedSub: document.getElementById('kpi-resolved-sub'),
        kpiRps: document.getElementById('kpi-rps'),
        kpiCpuBar: document.getElementById('kpi-cpu-bar'),
        kpiPodsCount: document.getElementById('kpi-pods-count'),
        kpiPodStatus: document.getElementById('kpi-pod-status'),
        ringFillRes: document.getElementById('ring-fill-res'),
        ringFillRps: document.getElementById('ring-fill-rps'),
        ringFillPods: document.getElementById('ring-fill-pods'),
        sidebarCpuFill: document.getElementById('sidebar-cpu-fill'),
        sidebarPodsText: document.getElementById('sidebar-pods-text'),

        // Operations & Machine Learning Elements
        activePodCountBadge: document.getElementById('active-pod-count-badge'),
        nodesContainer: document.getElementById('nodes-container'),
        hpaActionText: document.getElementById('hpa-action-text'),
        hpaCooldownText: document.getElementById('hpa-cooldown-text'),
        hpaReasonText: document.getElementById('hpa-reason-text'),
        trendBadge: document.getElementById('trend-badge'),
        accR2: document.getElementById('acc-r2'),
        accMae: document.getElementById('acc-mae'),
        accRmse: document.getElementById('acc-rmse'),
        accMape: document.getElementById('acc-mape'),
        accCoverage: document.getElementById('acc-coverage'),
        weightGbm: document.getElementById('weight-gbm'),
        weightRf: document.getElementById('weight-rf'),
        weightRidge: document.getElementById('weight-ridge'),
        mlFeatureChips: document.getElementById('ml-feature-chips'),
        scenarioButtons: document.querySelectorAll('.btn-scenario'),
        btnTriggerChaos: document.getElementById('btn-trigger-chaos'),
        agencyStatsList: document.getElementById('agency-stats-list'),
        districtStatsGrid: document.getElementById('district-stats-grid'),

        // Calendar Elements
        calendarDaysGrid: document.getElementById('calendar-days-grid'),
        calMonthDisplay: document.getElementById('cal-month-display'),
        calPrevBtn: document.getElementById('cal-prev-btn'),
        calNextBtn: document.getElementById('cal-next-btn'),

        // Modals
        submitModal: document.getElementById('submit-modal'),
        btnOpenSubmitModal: document.getElementById('btn-open-submit-modal'),
        modalSubmitCloseBtn: document.getElementById('modal-submit-close-btn'),
        publicSubmitForm: document.getElementById('public-submit-form'),
        detailModal: document.getElementById('detail-modal'),
        detailModalTitle: document.getElementById('detail-modal-title'),
        detailModalContent: document.getElementById('detail-modal-content'),
        detailModalCloseBtn: document.getElementById('detail-modal-close-btn'),
        toastContainer: document.getElementById('toast-container')
    };
}

// Canvas helper
function getCanvasContext(id) {
    const canvas = document.getElementById(id);
    return canvas ? { canvas, ctx: canvas.getContext('2d') } : null;
}

/* ==========================================================================
   Clock & Navigation Sidebar Routing
   ========================================================================== */
function initClock() {
    setInterval(() => {
        const now = new Date();
        if (elements.clusterClock) {
            elements.clusterClock.textContent = now.toTimeString().split(' ')[0] + ' UTC';
        }
    }, 1000);
}

function initTabs() {
    if (!elements.tabs) return;
    elements.tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const target = tab.dataset.tab;
            state.activeTab = target;

            elements.tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            if (target === 'tab-dashboard') {
                window.scrollTo({ top: 0, behavior: 'smooth' });
            } else if (target === 'tab-public-portal') {
                const el = document.getElementById('tab-public-portal');
                if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
            } else if (target === 'tab-predictive-ops') {
                const el = document.querySelector('.dashboard-grid-2col');
                if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
                renderPredictiveChart();
                renderOpsChart();
            } else if (target === 'tab-transparency') {
                const el = document.getElementById('tab-transparency');
                if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
                fetchDetailedTransparencyAnalytics();
            } else if (target === 'tab-calendar') {
                const el = document.querySelector('.calendar-card');
                if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        });
    });
}

/* ==========================================================================
   Interactive Civil Service Calendar Widget
   ========================================================================== */
let currentCalYear = 2026;
let currentCalMonth = 10; // 0-indexed: 10 is November

const monthNames = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
];

const milestoneEvents = {
    '2026-10-3': { title: 'Today: 311 Ingress Auto-Triage & Health Sweep', type: 'mint' },
    '2026-10-5': { title: 'Quantile Autoregressive Weight Rebalance', type: 'blue' },
    '2026-10-12': { title: 'Mid-Month Service Latency & Pod Audit', type: 'blue' },
    '2026-10-15': { title: 'Bi-Weekly Municipal SLA Compliance Report', type: 'gold' },
    '2026-10-19': { title: 'HPA Proactive Scaling Policy Verification', type: 'blue' },
    '2026-10-26': { title: 'Monthly Infrastructure Resilience Drill', type: 'gold' }
};

function renderCalendar() {
    if (!elements.calendarDaysGrid) return;
    if (elements.calMonthDisplay) {
        elements.calMonthDisplay.textContent = `${monthNames[currentCalMonth]} ${currentCalYear}`;
    }

    const firstDay = new Date(currentCalYear, currentCalMonth, 1).getDay();
    const daysInMonth = new Date(currentCalYear, currentCalMonth + 1, 0).getDate();

    let html = '';
    // Empty padding cells for preceding month
    for (let i = 0; i < firstDay; i++) {
        html += '<div class="cal-day empty"></div>';
    }

    for (let day = 1; day <= daysInMonth; day++) {
        const key = `${currentCalYear}-${currentCalMonth}-${day}`;
        const isToday = (currentCalYear === 2026 && currentCalMonth === 10 && day === 3);
        const milestone = milestoneEvents[key];

        let extraClass = '';
        if (isToday) extraClass += ' today';
        if (milestone) {
            extraClass += milestone.type === 'blue' ? ' milestone-blue' : (milestone.type === 'gold' ? ' milestone-gold' : '');
        }

        html += `<div class="cal-day${extraClass}" data-date="${day}" onclick="selectCalendarDay(${day})">${day}</div>`;
    }

    elements.calendarDaysGrid.innerHTML = html;
}

window.selectCalendarDay = function(day) {
    const key = `${currentCalYear}-${currentCalMonth}-${day}`;
    const milestone = milestoneEvents[key];
    document.querySelectorAll('.cal-day').forEach(el => el.style.outline = '');
    const targetEl = document.querySelector(`.cal-day[data-date="${day}"]`);
    if (targetEl && !targetEl.classList.contains('today')) {
        targetEl.style.outline = '2px solid var(--accent-mint)';
    }
    if (milestone) {
        showToast(`📅 ${monthNames[currentCalMonth]} ${day}: ${milestone.title}`, 'info');
    } else {
        showToast(`📅 Schedule checked for ${monthNames[currentCalMonth]} ${day}, ${currentCalYear}`, 'info');
    }
};

function bindCalendarListeners() {
    if (elements.calPrevBtn) {
        elements.calPrevBtn.addEventListener('click', () => {
            currentCalMonth--;
            if (currentCalMonth < 0) {
                currentCalMonth = 11;
                currentCalYear--;
            }
            renderCalendar();
        });
    }
    if (elements.calNextBtn) {
        elements.calNextBtn.addEventListener('click', () => {
            currentCalMonth++;
            if (currentCalMonth > 11) {
                currentCalMonth = 0;
                currentCalYear++;
            }
            renderCalendar();
        });
    }
}

/* ==========================================================================
   Public 311 Records Fetching, Search, Multi-Filter & Sorting
   ========================================================================== */
async function fetchPublicRequests() {
    try {
        const params = new URLSearchParams({
            page: state.currentPage,
            page_size: state.pageSize,
            sort_by: state.sortBy,
            sort_dir: state.sortDir
        });
        if (state.searchQuery) params.append('query', state.searchQuery);
        if (state.selectedAgency && state.selectedAgency !== 'ALL') params.append('agency', state.selectedAgency);
        if (state.selectedDistrict && state.selectedDistrict !== 'ALL') params.append('district', state.selectedDistrict);
        if (state.selectedStatus && state.selectedStatus !== 'ALL') params.append('status', state.selectedStatus);
        if (state.selectedPriority && state.selectedPriority !== 'ALL') params.append('priority', state.selectedPriority);

        const res = await fetch(`/api/civic/requests?${params.toString()}`);
        if (res.ok) {
            const data = await res.json();
            state.publicRecords = data.records || [];
            state.totalRecords = data.total_records || 0;
            state.totalPages = data.total_pages || 1;
            state.analytics = data.analytics;

            renderPublicTable();
            updatePaginationControls();
            updatePublicKpi();
            updateTableSortHeaders();
        } else {
            throw new Error(`API returned HTTP ${res.status}`);
        }
    } catch (e) {
        console.error('Failed fetching public requests:', e);
        if (elements.publicTableBody) {
            elements.publicTableBody.innerHTML = `
                <tr>
                    <td colspan="9" style="text-align:center; padding:36px; color:var(--accent-danger); font-size:0.85rem; font-weight:700;">
                        ⚠️ Unable to connect to CivicScale API (${e.message}). 
                        <button onclick="fetchPublicRequests()" class="btn-ghost" style="margin-left:10px; padding:4px 12px;">Retry</button>
                    </td>
                </tr>
            `;
        }
    }
}

window.fetchPublicRequests = fetchPublicRequests;

function updateTableSortHeaders() {
    if (!elements.clickableHeaders) return;
    elements.clickableHeaders.forEach(th => {
        const sortField = th.dataset.sort;
        const iconSpan = th.querySelector('.sort-icon');
        if (!iconSpan) return;

        if (sortField === state.sortBy) {
            iconSpan.textContent = state.sortDir === 'asc' ? '▲' : '▼';
            th.style.color = 'var(--accent-mint)';
        } else {
            iconSpan.textContent = '';
            th.style.color = '';
        }
    });
}

function renderPublicTable() {
    if (!elements.publicTableBody) return;

    if (!state.publicRecords || state.publicRecords.length === 0) {
        elements.publicTableBody.innerHTML = `
            <tr>
                <td colspan="9" style="text-align:center; padding:36px; color:var(--text-muted); font-size:0.86rem; font-weight:600;">
                    🔍 No public records matched your search filters. Try adjusting your search query or resetting filters.
                </td>
            </tr>
        `;
        return;
    }

    let html = '';
    state.publicRecords.forEach(r => {
        const agencyCode = (r.agency || 'OTHER').toLowerCase();
        const statusCode = (r.status || 'QUEUED').toLowerCase();
        
        let priorityClass = 'priority-p3';
        if (r.priority === 'P1_CRITICAL') priorityClass = 'priority-p1';
        else if (r.priority === 'P2_HIGH') priorityClass = 'priority-p2';
        else if (r.priority === 'P4_ROUTINE') priorityClass = 'priority-p4';

        const createdShort = (r.created_date || '').split(' ')[0] || '--';

        html += `
            <tr onclick="inspectPublicRecord('${r.service_request_id}')">
                <td><span class="t-req-id">${r.service_request_id}</span></td>
                <td style="font-family:var(--font-mono); font-size:0.75rem; color:var(--text-muted); font-weight:600;">${createdShort}</td>
                <td><span class="agency-tag agency-${agencyCode}">${r.agency}</span></td>
                <td>
                    <div style="font-weight:700; color:var(--text-primary);">${r.complaint_type || 'General Service'}</div>
                    <div style="font-size:0.72rem; color:var(--text-muted); max-width:240px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${r.descriptor || ''}</div>
                </td>
                <td>
                    <div style="font-weight:600; color:var(--text-primary);">${r.incident_address || 'Metro Center'}</div>
                    <div style="font-size:0.72rem; color:var(--text-muted);">${r.district || ''}</div>
                </td>
                <td><span class="priority-badge ${priorityClass}">${r.priority}</span></td>
                <td><span class="status-badge status-${statusCode}">${r.status}</span></td>
                <td style="font-family:var(--font-mono); font-size:0.75rem; color:var(--text-primary); font-weight:800;">${r.sla_target_hours}h</td>
                <td style="font-family:var(--font-mono); font-size:0.75rem; color:var(--accent-mint); font-weight:700;">${r.assigned_pod}</td>
            </tr>
        `;
    });
    elements.publicTableBody.innerHTML = html;
}

function updatePaginationControls() {
    if (!elements.paginationInfo) return;
    const start = state.totalRecords > 0 ? (state.currentPage - 1) * state.pageSize + 1 : 0;
    const end = Math.min(state.currentPage * state.pageSize, state.totalRecords);

    elements.paginationInfo.textContent = state.totalRecords > 0 ? `Showing records ${start} - ${end} of ${state.totalRecords}` : 'Showing 0 records';
    if (elements.pageIndicator) {
        elements.pageIndicator.textContent = `Page ${state.currentPage} of ${state.totalPages}`;
    }

    if (elements.btnPrevPage) elements.btnPrevPage.disabled = state.currentPage <= 1;
    if (elements.btnNextPage) elements.btnNextPage.disabled = state.currentPage >= state.totalPages;
}

function updatePublicKpi() {
    if (!state.analytics) return;
    if (elements.kpiTotalRecords) elements.kpiTotalRecords.textContent = state.analytics.total_in_system;
    if (elements.kpiResolutionRate) elements.kpiResolutionRate.textContent = `${state.analytics.resolution_rate_pct}%`;
    if (elements.kpiResolvedSub) {
        elements.kpiResolvedSub.textContent = `${state.analytics.resolved_count} of ${state.analytics.total_in_system} closed (${state.analytics.processing_count} in-flight)`;
    }

    // Radial Resolution Ring (circumference: 163.36)
    if (elements.ringFillRes) {
        const pct = state.analytics.resolution_rate_pct || 98.4;
        const circumference = 163.36;
        const offset = circumference * (1 - pct / 100);
        elements.ringFillRes.style.strokeDashoffset = offset.toFixed(2);
    }
}

/* ==========================================================================
   Filter & Search Event Listeners
   ========================================================================== */
function bindFilterListeners() {
    // Top Elongated Search Bar Sync
    if (elements.topSearchInput) {
        let topDebounce;
        elements.topSearchInput.addEventListener('input', (e) => {
            clearTimeout(topDebounce);
            topDebounce = setTimeout(() => {
                state.searchQuery = e.target.value.trim();
                if (elements.publicSearchInput) elements.publicSearchInput.value = state.searchQuery;
                state.currentPage = 1;
                fetchPublicRequests();
            }, 200);
        });
    }

    let searchDebounceTimer;
    if (elements.publicSearchInput) {
        elements.publicSearchInput.addEventListener('input', (e) => {
            clearTimeout(searchDebounceTimer);
            searchDebounceTimer = setTimeout(() => {
                state.searchQuery = e.target.value.trim();
                if (elements.topSearchInput) elements.topSearchInput.value = state.searchQuery;
                state.currentPage = 1;
                fetchPublicRequests();
            }, 200);
        });
    }

    if (elements.filterAgency) {
        elements.filterAgency.addEventListener('change', (e) => {
            state.selectedAgency = e.target.value;
            state.currentPage = 1;
            fetchPublicRequests();
        });
    }

    if (elements.filterDistrict) {
        elements.filterDistrict.addEventListener('change', (e) => {
            state.selectedDistrict = e.target.value;
            state.currentPage = 1;
            fetchPublicRequests();
        });
    }

    if (elements.filterStatus) {
        elements.filterStatus.addEventListener('change', (e) => {
            state.selectedStatus = e.target.value;
            state.currentPage = 1;
            fetchPublicRequests();
        });
    }

    if (elements.filterPriority) {
        elements.filterPriority.addEventListener('change', (e) => {
            state.selectedPriority = e.target.value;
            state.currentPage = 1;
            fetchPublicRequests();
        });
    }

    if (elements.sortBySelect) {
        elements.sortBySelect.addEventListener('change', (e) => {
            const parts = e.target.value.split(':');
            state.sortBy = parts[0];
            state.sortDir = parts[1] || 'desc';
            state.currentPage = 1;
            fetchPublicRequests();
        });
    }

    if (elements.clickableHeaders) {
        elements.clickableHeaders.forEach(th => {
            th.addEventListener('click', () => {
                const field = th.dataset.sort;
                if (state.sortBy === field) {
                    state.sortDir = state.sortDir === 'asc' ? 'desc' : 'asc';
                } else {
                    state.sortBy = field;
                    state.sortDir = 'desc';
                }

                const targetVal = `${state.sortBy}:${state.sortDir}`;
                if (elements.sortBySelect && elements.sortBySelect.querySelector(`option[value="${targetVal}"]`)) {
                    elements.sortBySelect.value = targetVal;
                }

                state.currentPage = 1;
                fetchPublicRequests();
            });
        });
    }

    if (elements.btnResetFilters) {
        elements.btnResetFilters.addEventListener('click', () => {
            if (elements.topSearchInput) elements.topSearchInput.value = '';
            if (elements.publicSearchInput) elements.publicSearchInput.value = '';
            if (elements.filterAgency) elements.filterAgency.value = 'ALL';
            if (elements.filterDistrict) elements.filterDistrict.value = 'ALL';
            if (elements.filterStatus) elements.filterStatus.value = 'ALL';
            if (elements.filterPriority) elements.filterPriority.value = 'ALL';
            if (elements.sortBySelect) elements.sortBySelect.value = 'created_date:desc';
            state.searchQuery = '';
            state.selectedAgency = 'ALL';
            state.selectedDistrict = 'ALL';
            state.selectedStatus = 'ALL';
            state.selectedPriority = 'ALL';
            state.sortBy = 'created_date';
            state.sortDir = 'desc';
            state.currentPage = 1;
            fetchPublicRequests();
            showToast('Search filters reset', 'info');
        });
    }

    // Pagination
    if (elements.btnPrevPage) {
        elements.btnPrevPage.addEventListener('click', () => {
            if (state.currentPage > 1) {
                state.currentPage--;
                fetchPublicRequests();
            }
        });
    }

    if (elements.btnNextPage) {
        elements.btnNextPage.addEventListener('click', () => {
            if (state.currentPage < state.totalPages) {
                state.currentPage++;
                fetchPublicRequests();
            }
        });
    }

    // CSV & JSON Exports
    if (elements.btnExportCsv) {
        elements.btnExportCsv.addEventListener('click', () => {
            const params = new URLSearchParams();
            if (state.searchQuery) params.append('query', state.searchQuery);
            if (state.selectedAgency && state.selectedAgency !== 'ALL') params.append('agency', state.selectedAgency);
            if (state.selectedDistrict && state.selectedDistrict !== 'ALL') params.append('district', state.selectedDistrict);
            if (state.selectedStatus && state.selectedStatus !== 'ALL') params.append('status', state.selectedStatus);
            if (state.selectedPriority && state.selectedPriority !== 'ALL') params.append('priority', state.selectedPriority);
            window.location.href = `/api/civic/export/csv?${params.toString()}`;
            showToast('Downloading verified 311 CSV dataset...', 'success');
        });
    }

    if (elements.btnExportJson) {
        elements.btnExportJson.addEventListener('click', () => {
            const params = new URLSearchParams();
            if (state.searchQuery) params.append('query', state.searchQuery);
            if (state.selectedAgency && state.selectedAgency !== 'ALL') params.append('agency', state.selectedAgency);
            if (state.selectedDistrict && state.selectedDistrict !== 'ALL') params.append('district', state.selectedDistrict);
            if (state.selectedStatus && state.selectedStatus !== 'ALL') params.append('status', state.selectedStatus);
            if (state.selectedPriority && state.selectedPriority !== 'ALL') params.append('priority', state.selectedPriority);
            window.location.href = `/api/civic/export/json?${params.toString()}`;
            showToast('Downloading verified 311 JSON dataset...', 'success');
        });
    }

    // Workload Scenario Buttons
    if (elements.scenarioButtons) {
        elements.scenarioButtons.forEach(btn => {
            btn.addEventListener('click', async () => {
                const scenario = btn.dataset.scenario;
                elements.scenarioButtons.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');

                try {
                    const res = await fetch(`/api/telemetry/scenario?scenario=${scenario}`, { method: 'POST' });
                    if (res.ok) {
                        showToast(`Injected Autonomous Workload: ${scenario.toUpperCase().replace('_', ' ')}`, 'success');
                    }
                } catch (e) {
                    console.error('Failed setting workload scenario:', e);
                }
            });
        });
    }

    // Chaos Crash Pod Button
    if (elements.btnTriggerChaos) {
        elements.btnTriggerChaos.addEventListener('click', async () => {
            try {
                const res = await fetch('/api/telemetry/chaos/kill-pod', { method: 'POST' });
                if (res.ok) {
                    const data = await res.json();
                    showToast(`💥 Chaos Injected: Terminated Pod ${data.killed_pod_id}`, 'error');
                }
            } catch (e) {
                console.error('Failed killing pod:', e);
            }
        });
    }
}

/* ==========================================================================
   Inspect Single Record in High-Contrast Modal
   ========================================================================== */
window.inspectPublicRecord = async function(id) {
    let record = state.publicRecords.find(r => r.service_request_id === id);
    if (!record) {
        try {
            const res = await fetch(`/api/civic/requests?query=${encodeURIComponent(id)}`);
            if (res.ok) {
                const d = await res.json();
                if (d.records && d.records.length > 0) record = d.records[0];
            }
        } catch (e) {
            console.error('Failed looking up record:', e);
        }
    }

    if (!record) return;

    if (elements.detailModalTitle) {
        elements.detailModalTitle.textContent = `${record.service_request_id}`;
    }

    let priorityClass = 'priority-p3';
    if (record.priority === 'P1_CRITICAL') priorityClass = 'priority-p1';
    else if (record.priority === 'P2_HIGH') priorityClass = 'priority-p2';
    else if (record.priority === 'P4_ROUTINE') priorityClass = 'priority-p4';

    const statusClass = `status-${(record.status || 'queued').toLowerCase()}`;
    const agencyClass = `agency-${(record.agency || 'other').toLowerCase()}`;

    if (elements.detailModalContent) {
        elements.detailModalContent.innerHTML = `
            <div style="display:flex; flex-direction:column; gap:16px; font-family:var(--font-sans);">
                <!-- Status & Agency Top Ribbon -->
                <div style="display:flex; justify-content:space-between; align-items:center; background:#F4F9F6; padding:12px 16px; border-radius:10px; border:1px solid #FDF9E2;">
                    <div style="display:flex; align-items:center; gap:8px;">
                        <span class="agency-tag ${agencyClass}">${record.agency}</span>
                        <span style="font-size:0.88rem; font-weight:800; color:#1A2E26;">${record.agency_name || ''}</span>
                    </div>
                    <div style="display:flex; align-items:center; gap:8px;">
                        <span class="priority-badge ${priorityClass}">${record.priority}</span>
                        <span class="status-badge ${statusClass}">${record.status}</span>
                    </div>
                </div>

                <!-- Complaint Details Card -->
                <div style="background:#FFFFFF; border:1px solid #FDF9E2; border-radius:10px; padding:16px; box-shadow:0 2px 6px rgba(26,46,38,0.03);">
                    <div style="font-size:0.72rem; font-weight:800; color:#527566; text-transform:uppercase; margin-bottom:4px;">Complaint Category & Description</div>
                    <div style="font-size:1.05rem; font-weight:800; color:#1A2E26; margin-bottom:6px;">${record.complaint_type || ''}</div>
                    <div style="font-size:0.86rem; color:#2E4A3F; line-height:1.55;">${record.descriptor || ''}</div>
                </div>

                <!-- Location & Jurisdiction -->
                <div style="background:#FFFFFF; border:1px solid #FDF9E2; border-radius:10px; padding:16px; box-shadow:0 2px 6px rgba(26,46,38,0.03);">
                    <div style="font-size:0.72rem; font-weight:800; color:#527566; text-transform:uppercase; margin-bottom:4px;">Incident Location</div>
                    <div style="font-size:0.95rem; font-weight:700; color:#1A2E26;">📍 ${record.incident_address || ''}</div>
                    <div style="font-size:0.78rem; color:#527566; margin-top:4px;">${record.district || ''} • GPS: ${record.latitude}, ${record.longitude}</div>
                </div>

                <!-- Telemetry & Pod Allocation Grid -->
                <div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:12px;">
                    <div style="background:#F4F9F6; border:1px solid #FDF9E2; border-radius:10px; padding:12px; text-align:center;">
                        <div style="font-size:0.68rem; color:#527566; font-weight:800;">TARGET SLA</div>
                        <div style="font-family:var(--font-mono); font-size:1.05rem; font-weight:800; color:#1A2E26; margin-top:2px;">${record.sla_target_hours}h</div>
                    </div>
                    <div style="background:#F4F9F6; border:1px solid #FDF9E2; border-radius:10px; padding:12px; text-align:center;">
                        <div style="font-size:0.68rem; color:#527566; font-weight:800;">ELAPSED TIME</div>
                        <div style="font-family:var(--font-mono); font-size:1.05rem; font-weight:800; color:#1A2E26; margin-top:2px;">${record.elapsed_hours}h</div>
                    </div>
                    <div style="background:#F4F9F6; border:1px solid #FDF9E2; border-radius:10px; padding:12px; text-align:center;">
                        <div style="font-size:0.68rem; color:#527566; font-weight:800;">WORKER POD</div>
                        <div style="font-family:var(--font-mono); font-size:0.88rem; font-weight:800; color:#10B981; margin-top:4px;">${record.assigned_pod}</div>
                    </div>
                </div>

                <!-- Citizen & Date Footnote -->
                <div style="display:flex; justify-content:space-between; align-items:center; font-size:0.78rem; color:#527566; padding:0 4px;">
                    <span>Filed by: <b style="color:#1A2E26;">${record.citizen_name || 'Anonymous'}</b> (${record.channel || 'Civic Portal'})</span>
                    <span style="font-family:var(--font-mono);">Date: ${record.created_date || ''}</span>
                </div>
            </div>
        `;
    }
    if (elements.detailModal) elements.detailModal.classList.add('open');
};

function bindModalListeners() {
    if (elements.detailModalCloseBtn) {
        elements.detailModalCloseBtn.addEventListener('click', () => {
            if (elements.detailModal) elements.detailModal.classList.remove('open');
        });
    }

    if (elements.btnOpenSubmitModal) {
        elements.btnOpenSubmitModal.addEventListener('click', () => {
            if (elements.submitModal) elements.submitModal.classList.add('open');
        });
    }

    if (elements.modalSubmitCloseBtn) {
        elements.modalSubmitCloseBtn.addEventListener('click', () => {
            if (elements.submitModal) elements.submitModal.classList.remove('open');
        });
    }

    document.querySelectorAll('.modal-overlay').forEach(overlay => {
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) overlay.classList.remove('open');
        });
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            document.querySelectorAll('.modal-overlay.open').forEach(modal => {
                modal.classList.remove('open');
            });
            if (elements.topSearchInput) elements.topSearchInput.value = '';
        }
    });

    // Form Submission
    if (elements.publicSubmitForm) {
        elements.publicSubmitForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const payload = {
                citizen_name: document.getElementById('sub-name').value,
                citizen_email: document.getElementById('sub-email').value,
                category: document.getElementById('sub-category').value,
                district: document.getElementById('sub-district').value,
                address: document.getElementById('sub-address').value,
                summary: document.getElementById('sub-summary').value
            };

            try {
                const res = await fetch('/api/civic/requests', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                if (res.ok) {
                    const data = await res.json();
                    showToast(`✓ Ticket Filed: ${data.service_request_id} routed to ${data.assigned_pod}`, 'success');
                    if (elements.submitModal) elements.submitModal.classList.remove('open');
                    elements.publicSubmitForm.reset();
                    state.currentPage = 1;
                    fetchPublicRequests();
                } else {
                    throw new Error(`Server returned HTTP ${res.status}`);
                }
            } catch (err) {
                showToast(`Failed submitting ticket: ${err.message}`, 'error');
            }
        });
    }
}

/* ==========================================================================
   Real-Time Telemetry & Fallback Polling
   ========================================================================== */
function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/telemetry`;

    try {
        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            state.wsConnected = true;
            stopFallbackPolling();
            console.log('Telemetry WebSocket connected.');
        };

        ws.onmessage = (event) => {
            try {
                const payload = JSON.parse(event.data);
                handleTelemetryPayload(payload);
            } catch (e) {
                console.error('Failed parsing WebSocket telemetry:', e);
            }
        };

        ws.onerror = (err) => {
            console.warn('WebSocket encountered error. Falling back to HTTP polling:', err);
            startFallbackPolling();
        };

        ws.onclose = () => {
            state.wsConnected = false;
            console.warn('WebSocket closed. Retrying connection in 4s...');
            startFallbackPolling();
            setTimeout(connectWebSocket, 4000);
        };
    } catch (e) {
        console.warn('WebSocket unavailable. Triggering fallback HTTP polling:', e);
        startFallbackPolling();
    }
}

function startFallbackPolling() {
    if (state.pollIntervalId) return;
    console.log('Active fallback HTTP polling initiated (every 2.5s)...');
    state.pollIntervalId = setInterval(async () => {
        try {
            const [clusterRes, hpaRes, predRes] = await Promise.all([
                fetch('/api/telemetry/cluster'),
                fetch('/api/telemetry/hpa'),
                fetch('/api/predictive/forecast')
            ]);
            if (clusterRes.ok && hpaRes.ok && predRes.ok) {
                const cluster = await clusterRes.json();
                const hpa = await hpaRes.json();
                const predictive = await predRes.json();
                handleTelemetryPayload({ cluster, hpa, predictive });
            }
        } catch (e) {
            console.error('Error polling telemetry endpoints:', e);
        }
    }, 2500);
}

function stopFallbackPolling() {
    if (state.pollIntervalId) {
        clearInterval(state.pollIntervalId);
        state.pollIntervalId = null;
    }
}

function handleTelemetryPayload(payload) {
    if (!payload || !payload.cluster) return;

    state.cluster = payload.cluster;
    state.hpa = payload.hpa;
    state.predictive = payload.predictive;

    state.historyRps.push(payload.cluster.total_rps);
    state.historyReplicas.push(payload.cluster.current_replicas);

    if (state.historyRps.length > state.maxHistoryPoints) {
        state.historyRps.shift();
        state.historyReplicas.shift();
    }

    if (elements.kpiRps) elements.kpiRps.textContent = payload.cluster.total_rps.toFixed(1);
    if (elements.kpiCpuBar) elements.kpiCpuBar.style.width = `${Math.min(100, payload.cluster.avg_cpu_percent)}%`;
    if (elements.kpiPodsCount) elements.kpiPodsCount.textContent = payload.cluster.ready_replicas;
    if (elements.kpiPodStatus) {
        elements.kpiPodStatus.textContent = `${payload.cluster.ready_replicas} Ready / ${payload.cluster.target_replicas} Target`;
    }

    // Radial Progress Rings & Sidebar Stats
    if (elements.ringFillRps) {
        const rps = payload.cluster.total_rps || 0;
        const circumference = 163.36;
        const pct = Math.min(100, (rps / 600) * 100);
        elements.ringFillRps.style.strokeDashoffset = (circumference * (1 - pct / 100)).toFixed(2);
    }
    if (elements.ringFillPods) {
        const pods = payload.cluster.ready_replicas || 0;
        const circumference = 163.36;
        const pct = Math.min(100, (pods / 24) * 100);
        elements.ringFillPods.style.strokeDashoffset = (circumference * (1 - pct / 100)).toFixed(2);
    }
    if (elements.sidebarCpuFill) {
        elements.sidebarCpuFill.style.width = `${Math.min(100, payload.cluster.avg_cpu_percent)}%`;
    }
    if (elements.sidebarPodsText) {
        elements.sidebarPodsText.textContent = `${payload.cluster.ready_replicas} / 24 Replicas Active`;
    }

    updateNodeTopology(payload.cluster);
    updateHpaDisplay(payload.hpa);
    updatePredictiveAccuracyDisplay(payload.predictive);

    renderPredictiveChart();
    renderOpsChart();
}

function updatePredictiveAccuracyDisplay(predictive) {
    if (!predictive) return;

    if (predictive.accuracy) {
        const acc = predictive.accuracy;
        if (elements.accR2) elements.accR2.textContent = acc.r2_score.toFixed(3);
        if (elements.accMae) elements.accMae.innerHTML = `${acc.mae.toFixed(1)} <span class="acc-unit">rps</span>`;
        if (elements.accRmse) elements.accRmse.innerHTML = `${acc.rmse.toFixed(1)} <span class="acc-unit">rps</span>`;
        if (elements.accMape) elements.accMape.innerHTML = `${acc.mape_percent.toFixed(1)}<span class="acc-unit">%</span>`;
        if (elements.accCoverage) elements.accCoverage.innerHTML = `${acc.interval_coverage_pct.toFixed(1)}<span class="acc-unit">%</span>`;

        if (acc.ensemble_weights) {
            const w = acc.ensemble_weights;
            if (elements.weightGbm) elements.weightGbm.textContent = `GBM: ${(w.GradientBoosting * 100).toFixed(0)}%`;
            if (elements.weightRf) elements.weightRf.textContent = `RF: ${(w.RandomForest * 100).toFixed(0)}%`;
            if (elements.weightRidge) elements.weightRidge.textContent = `Ridge: ${(w.RidgeCV * 100).toFixed(0)}%`;
        }
    }

    if (predictive.feature_importance && elements.mlFeatureChips) {
        let chipsHtml = '';
        for (const [feat, val] of Object.entries(predictive.feature_importance)) {
            chipsHtml += `<span class="feature-chip">${feat}: ${(val * 100).toFixed(0)}%</span>`;
        }
        elements.mlFeatureChips.innerHTML = chipsHtml;
    }
}

function updateNodeTopology(cluster) {
    if (!cluster || !elements.nodesContainer) return;
    if (elements.activePodCountBadge) {
        elements.activePodCountBadge.textContent = `${cluster.current_replicas} Total Pods`;
    }

    const nodeGroups = { 'node-us-east-1a': [], 'node-us-east-1b': [], 'node-us-east-1c': [] };
    cluster.pods.forEach(pod => {
        if (!nodeGroups[pod.node_name]) nodeGroups[pod.node_name] = [];
        nodeGroups[pod.node_name].push(pod);
    });

    let html = '';
    for (const [nodeName, pods] of Object.entries(nodeGroups)) {
        html += `
        <div class="node-box">
            <div class="node-header">
                <span>🖥 ${nodeName}</span>
                <span>Active Pods: ${pods.length}</span>
            </div>
            <div class="node-pod-grid">
                ${pods.map(p => `
                    <div class="pod-card">
                        <span>●</span>
                        <span>${p.id}</span>
                    </div>
                `).join('')}
            </div>
        </div>
        `;
    }
    elements.nodesContainer.innerHTML = html;
}

function updateHpaDisplay(hpa) {
    if (!hpa) return;
    if (elements.hpaActionText) elements.hpaActionText.textContent = hpa.scaling_action;
    if (elements.hpaCooldownText) elements.hpaCooldownText.textContent = `${hpa.cooldown_remaining_sec}s`;
    if (elements.hpaReasonText) elements.hpaReasonText.textContent = hpa.reason;
}

/* ==========================================================================
   Real-Time Canvas Charts (Mint Green, Sage Blue, Accent Gold on White)
   ========================================================================== */
function renderOpsChart() {
    const target = getCanvasContext('ops-canvas-chart');
    if (!target) return;
    const { canvas, ctx } = target;

    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    const rpsData = state.historyRps;
    const repData = state.historyReplicas;
    const n = rpsData.length;
    if (n < 2) return;

    const maxRps = Math.max(120, Math.max(...rpsData) * 1.25);
    const stepX = w / (state.maxHistoryPoints - 1);

    // Subtle Grid lines (Deep forest slate #1A2E26)
    ctx.strokeStyle = 'rgba(26, 46, 38, 0.08)';
    ctx.lineWidth = 1;
    for (let yVal = 0.25; yVal <= 0.75; yVal += 0.25) {
        ctx.beginPath();
        ctx.moveTo(0, h * yVal);
        ctx.lineTo(w, h * yVal);
        ctx.stroke();
    }

    // RPS line: Crisp Sage Blue (#3B82F6)
    ctx.beginPath();
    rpsData.forEach((val, idx) => {
        const x = idx * stepX;
        const y = h - (val / maxRps) * (h - 22);
        if (idx === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    });
    ctx.strokeStyle = '#3B82F6';
    ctx.lineWidth = 2.5;
    ctx.stroke();

    // Replicas step line: Vibrant Mint Green (#10B981)
    ctx.beginPath();
    repData.forEach((val, idx) => {
        const x = idx * stepX;
        const y = h - (val / 24) * (h - 28);
        if (idx === 0) ctx.moveTo(x, y);
        else {
            ctx.lineTo(x, h - (repData[idx - 1] / 24) * (h - 28));
            ctx.lineTo(x, y);
        }
    });
    ctx.strokeStyle = '#10B981';
    ctx.lineWidth = 2.5;
    ctx.stroke();
}

function renderPredictiveChart() {
    const target = getCanvasContext('predictive-canvas-chart');
    if (!target || !state.predictive || !state.predictive.predictions) return;
    const { canvas, ctx } = target;

    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    const preds = state.predictive.predictions;
    if (preds.length < 2) return;

    if (elements.trendBadge) {
        elements.trendBadge.textContent = `TREND: ${state.predictive.trend_direction}`;
    }

    const allValues = preds.map(p => p.upper_bound_rps).concat(preds.map(p => p.forecasted_rps));
    const maxVal = Math.max(120, Math.max(...allValues) * 1.2);
    const stepX = w / (preds.length - 1);

    // Grid lines (Deep forest slate #1A2E26)
    ctx.strokeStyle = 'rgba(26, 46, 38, 0.08)';
    ctx.lineWidth = 1;
    for (let yVal = 0.25; yVal <= 0.75; yVal += 0.25) {
        ctx.beginPath();
        ctx.moveTo(0, h * yVal);
        ctx.lineTo(w, h * yVal);
        ctx.stroke();
    }

    // Shaded 95% Quantile Confidence Ribbon in Sharp Accent Gold Tint
    ctx.beginPath();
    preds.forEach((p, idx) => {
        const x = idx * stepX;
        const y = h - (p.upper_bound_rps / maxVal) * (h - 30);
        if (idx === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    });
    for (let idx = preds.length - 1; idx >= 0; idx--) {
        const x = idx * stepX;
        const y = h - (preds[idx].lower_bound_rps / maxVal) * (h - 30);
        ctx.lineTo(x, y);
    }
    ctx.closePath();

    ctx.fillStyle = 'rgba(234, 179, 8, 0.12)';
    ctx.fill();

    // Quantile Upper Bound Dashed Line (Accent Gold #EAB308)
    ctx.beginPath();
    ctx.setLineDash([4, 4]);
    preds.forEach((p, idx) => {
        const x = idx * stepX;
        const y = h - (p.upper_bound_rps / maxVal) * (h - 30);
        if (idx === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    });
    ctx.strokeStyle = '#EAB308';
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // Quantile Lower Bound Dashed Line (Accent Gold #EAB308)
    ctx.beginPath();
    preds.forEach((p, idx) => {
        const x = idx * stepX;
        const y = h - (p.lower_bound_rps / maxVal) * (h - 30);
        if (idx === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    });
    ctx.strokeStyle = '#EAB308';
    ctx.lineWidth = 1.5;
    ctx.stroke();
    ctx.setLineDash([]);

    // Ensemble Forecast Mean Trajectory: Vibrant Mint Green (#10B981)
    ctx.beginPath();
    preds.forEach((p, idx) => {
        const x = idx * stepX;
        const y = h - (p.forecasted_rps / maxVal) * (h - 30);
        if (idx === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    });
    ctx.strokeStyle = '#10B981';
    ctx.lineWidth = 3;
    ctx.stroke();

    // End point highlight (Accent Gold with Deep Forest outline)
    const lastP = preds[preds.length - 1];
    const lastX = (preds.length - 1) * stepX;
    const lastY = h - (lastP.forecasted_rps / maxVal) * (h - 30);
    ctx.beginPath();
    ctx.arc(lastX, lastY, 4.5, 0, 2 * Math.PI);
    ctx.fillStyle = '#EAB308';
    ctx.fill();
    ctx.strokeStyle = '#1A2E26';
    ctx.lineWidth = 2;
    ctx.stroke();
}

/* ==========================================================================
   Transparency Analytics Fetcher
   ========================================================================== */
async function fetchDetailedTransparencyAnalytics() {
    try {
        const res = await fetch('/api/civic/analytics/summary');
        if (res.ok) {
            const data = await res.json();
            renderTransparencyBreakdown(data);
        }
    } catch (e) {
        console.error('Failed fetching transparency summary:', e);
    }
}

function renderTransparencyBreakdown(data) {
    if (!data) return;

    const agencyFullNames = {
        'DEP': 'Environmental Protection (Water & Sewer)',
        'DOT': 'Transportation (Signals, Roads & Bridges)',
        'DOB': 'Buildings & Infrastructure Safety',
        'DSNY': 'Sanitation & Clean City Waste Removal',
        'DOHMH': 'Public Health, Hygiene & Vector Control'
    };

    if (data.agency_breakdown && elements.agencyStatsList) {
        let agencyHtml = '';
        for (const [code, stats] of Object.entries(data.agency_breakdown)) {
            const fullName = agencyFullNames[code] || 'Municipal Civic Service';
            agencyHtml += `
                <div class="agency-stat-row">
                    <div>
                        <span class="agency-tag agency-${code.toLowerCase()}">${code}</span>
                        <span style="font-weight:800; margin-left:8px; color:#1A2E26;">${fullName}</span>
                    </div>
                    <div style="font-family:var(--font-mono); font-size:0.78rem;">
                        <span style="color:#527566;">${stats.total_requests} requests</span> • 
                        <span style="color:#1A2E26; font-weight:800;">avg ${stats.avg_resolution_hours}h</span> • 
                        <span style="color:#10B981; font-weight:800;">${stats.sla_compliance_pct}% SLA</span>
                    </div>
                </div>
            `;
        }
        elements.agencyStatsList.innerHTML = agencyHtml;
    }

    if (data.district_distribution && elements.districtStatsGrid) {
        let districtHtml = '';
        for (const [dist, count] of Object.entries(data.district_distribution)) {
            districtHtml += `
                <div class="district-stat-item">
                    <div style="font-weight:800; font-size:0.82rem; color:#1A2E26;">${dist}</div>
                    <div style="font-family:var(--font-mono); font-size:0.75rem; color:#10B981; font-weight:800; margin-top:4px;">
                        ${count} verified public reports
                    </div>
                </div>
            `;
        }
        elements.districtStatsGrid.innerHTML = districtHtml;
    }
}

/* ==========================================================================
   Clean Toast Notifications
   ========================================================================== */
function showToast(message, type = 'info') {
    if (!elements.toastContainer) return;
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    const icon = type === 'success' ? '✓' : type === 'error' ? '⚠️' : 'ℹ';
    toast.innerHTML = `<span>${icon}</span><span>${message}</span>`;
    elements.toastContainer.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => toast.remove(), 250);
    }, 3500);
}

/* ==========================================================================
   Initialization Routine
   ========================================================================== */
function init() {
    console.log('CivicScale initializing Ultra-Modern Civil Service Dashboard...');
    elements = getElements();
    initClock();
    initTabs();
    renderCalendar();
    bindCalendarListeners();
    bindFilterListeners();
    bindModalListeners();
    fetchPublicRequests();
    fetchDetailedTransparencyAnalytics();
    connectWebSocket();
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
