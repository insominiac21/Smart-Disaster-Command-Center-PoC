/**
 * Smart Disaster Command Center - Frontend Logic (Leaflet.js + API integration)
 */

const API_BASE = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
    ? "http://localhost:8000/api"
    : "/api";

let masterDistricts = []; // all 556 districts loaded on startup
let allAlerts = [];
let selectedDistrict = null;

// Leaflet Map Globals
let mapInstance = null;
let geoJsonLayer = null;

// EOC Dashboard State
let dbSort = {
    column: "overall_risk_score",
    direction: "desc"
};

let queryCounter = 0; // tracking session queries processed

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener("DOMContentLoaded", async () => {
    console.log("🚀 Initializing Operational Command Center...");
    await loadKPIs();
    await loadAlerts();
    await loadMasterDistricts();
    await loadMap();
});

// ============================================================================
// API CALLS
// ============================================================================

async function fetchAPI(endpoint, params = {}) {
    try {
        const queryString = new URLSearchParams(params).toString();
        const url = `${API_BASE}${endpoint}${queryString ? "?" + queryString : ""}`;
        console.log(`📡 Fetching API: ${endpoint}`, params);

        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error(`API Error on ${endpoint}:`, error);
        return null;
    }
}

// ============================================================================
// LOAD CACHED DATASETS
// ============================================================================

async function loadMasterDistricts() {
    // Load all 556 districts once on page start
    const districts = await fetchAPI("/districts", { disaster_type: "All", severity: "All" });
    if (districts) {
        masterDistricts = districts;
        populateStateDropdown(masterDistricts);
        updateExecutiveInsights(masterDistricts);
        applyDBFilters();
    }
}

// ============================================================================
// COLLAPSIBLE HEADERS (Section 3, 4, 5, 6)
// ============================================================================

function toggleCollapsible(id) {
    const el = document.getElementById(id);
    const arrow = document.getElementById(`arrow-${id}`);
    if (el.classList.contains("open")) {
        el.classList.remove("open");
        arrow.textContent = "▼";
    } else {
        el.classList.add("open");
        arrow.textContent = "▲";
    }
}

// ============================================================================
// KPI LOADING
// ============================================================================

async function loadKPIs() {
    const params = getFilterParams();
    const kpis = await fetchAPI("/kpis", params);

    if (kpis) {
        document.getElementById("kpiTotalAlerts").textContent = kpis.total_active_alerts;
        document.getElementById("kpiDualHazard").textContent = kpis.dual_hazard_count;
        document.getElementById("kpiCriticalFloods").textContent = kpis.critical_flood_count;
        document.getElementById("kpiExtremeRisk").textContent = kpis.extreme_risk_count;
    }
}

// ============================================================================
// ALERTS LOADING
// ============================================================================

async function loadAlerts() {
    const alerts = await fetchAPI("/alerts", { limit: 25 });

    if (!alerts) {
        document.getElementById("alertsContainer").innerHTML =
            '<p class="loading">Failed to load active alert streams</p>';
        return;
    }

    allAlerts = alerts;
    renderAlerts();
}

function renderAlerts() {
    const container = document.getElementById("alertsContainer");

    if (allAlerts.length === 0) {
        container.innerHTML = '<p class="loading">No active alerts at this time. Operations clear.</p>';
        return;
    }

    const html = allAlerts
        .map(
            (alert) => `
        <div class="alert-item alert-${alert.severity.toLowerCase()}" onclick="viewDistrict('${alert.district_id}')" style="cursor:pointer;">
            <div class="alert-item-header">
                <span class="alert-type">${alert.type}</span>
                <span class="alert-location">${alert.district}, ${alert.state}</span>
            </div>
            <div class="alert-msg">
                ${alert.message}
            </div>
        </div>
    `
        )
        .join("");

    container.innerHTML = html;
}

// ============================================================================
// EXECUTIVE INSIGHTS (Section 7)
// ============================================================================

function updateExecutiveInsights(districts) {
    const totalDistricts = districts.length;
    const extremeDistricts = districts.filter(d => d.overall_risk_score > 75).length;
    const activeFloods = districts.filter(d => d.flood_severity === "Critical").length;
    
    // Get state concentration of alerts
    const stateAlertCounts = {};
    districts.forEach(d => {
        if (d.flood_severity === "Critical" || d.heat_alert_tier === "Yellow") {
            const state = d.state || d.st_nm || "Unknown";
            stateAlertCounts[state] = (stateAlertCounts[state] || 0) + 1;
        }
    });
    
    // Sort states by counts
    const sortedStates = Object.entries(stateAlertCounts)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 2)
        .map(entry => entry[0]);
        
    const stateStr = sortedStates.length > 0 
        ? sortedStates.join(" and ") 
        : "multiple states";

    const overviewText = `Currently, <strong>${extremeDistricts}</strong> districts fall under Extreme risk conditions out of ${totalDistricts} monitored regions. The highest concentration of critical flood alerts is observed in <strong>${stateStr}</strong>. Additionally, <strong>${districts.filter(d => d.dual_hazard_flag).length}</strong> dual-hazard zones require immediate multi-agency rescue and shelter coordination.`;
    
    document.getElementById("executiveInsightsText").innerHTML = overviewText;
}

// ============================================================================
// ADVANCED EXPLORER FILTERING & SORTING (Section 1)
// ============================================================================

function populateStateDropdown(districts) {
    const dropdown = document.getElementById("dbFilterState");
    const states = [...new Set(districts.map(d => d.state))].sort();
    
    states.forEach(state => {
        if (state) {
            const opt = document.createElement("option");
            opt.value = state;
            opt.textContent = state;
            dropdown.appendChild(opt);
        }
    });
}

function derivePriority(score) {
    if (score > 75) return "Critical";
    if (score > 50) return "High";
    if (score > 25) return "Moderate";
    return "Low";
}

function applyDBFilters() {
    const stateVal = document.getElementById("dbFilterState").value;
    const floodVal = document.getElementById("dbFilterFlood").value;
    const heatVal = document.getElementById("dbFilterHeat").value;
    const dualVal = document.getElementById("dbFilterDual").value;
    const priorityVal = document.getElementById("dbFilterPriority").value;
    const teamsVal = document.getElementById("dbFilterTeams").value;
    const waterVal = document.getElementById("dbFilterWater").value;
    const historyVal = document.getElementById("dbFilterHistory").value;
    
    const minRisk = parseFloat(document.getElementById("dbFilterRiskMin").value) || 0;
    const maxRisk = parseFloat(document.getElementById("dbFilterRiskMax").value) || 100;
    const searchVal = document.getElementById("dbFilterSearch").value.toLowerCase().trim();

    let filtered = masterDistricts.filter(d => {
        // State
        if (stateVal !== "All") {
            const dState = (d.state || "").toLowerCase();
            if (dState !== stateVal.toLowerCase()) return false;
        }
        
        // Flood Severity
        if (floodVal !== "All" && d.flood_severity !== floodVal) return false;
        
        // Heat Tier
        if (heatVal !== "All" && d.heat_alert_tier !== heatVal) return false;
        
        // Dual Hazard
        if (dualVal !== "All") {
            const isDual = d.dual_hazard_flag;
            if (dualVal === "Yes" && !isDual) return false;
            if (dualVal === "No" && isDual) return false;
        }
        
        // Priority (derived)
        const priority = derivePriority(d.overall_risk_score);
        if (priorityVal !== "All" && priority !== priorityVal) return false;
        
        // Response teams
        if (teamsVal !== "All" && d.response_teams_deployed !== parseInt(teamsVal)) return false;
        
        // Water level above danger
        if (waterVal !== "All") {
            const val = parseFloat(waterVal);
            if (d.water_level_above_danger_m <= val) return false;
        }
        
        // Historical flood ratio
        if (historyVal !== "All") {
            const val = parseFloat(historyVal);
            if (d.historical_flood_ratio <= val) return false;
        }
        
        // Risk range
        if (d.overall_risk_score < minRisk || d.overall_risk_score > maxRisk) return false;
        
        // Text Search
        if (searchVal) {
            const name = (d.district || "").toLowerCase();
            const stateName = (d.state || "").toLowerCase();
            const id = (d.district_id || "").toLowerCase();
            if (!name.includes(searchVal) && !stateName.includes(searchVal) && !id.includes(searchVal)) return false;
        }
        
        return true;
    });

    // Apply Sorting
    filtered.sort((a, b) => {
        let valA = a[dbSort.column];
        let valB = b[dbSort.column];
        
        if (valA === undefined) valA = "";
        if (valB === undefined) valB = "";
        
        if (typeof valA === "string") {
            return dbSort.direction === "asc" 
                ? valA.localeCompare(valB) 
                : valB.localeCompare(valA);
        }
        
        return dbSort.direction === "asc" ? valA - valB : valB - valA;
    });

    renderDBTable(filtered);
}

function renderDBTable(districts) {
    const tbody = document.querySelector("#districtTable tbody");
    const countDisplay = document.getElementById("tableRecordCount");

    if (countDisplay) {
        countDisplay.textContent = `Showing ${districts.length} records`;
    }

    if (districts.length === 0) {
        tbody.innerHTML =
            '<tr><td colspan="10" class="loading">No districts match active EOC filter inputs</td></tr>';
        return;
    }

    const rows = districts
        .map(
            (d) => {
                const priority = derivePriority(d.overall_risk_score);
                const priorityClass = `priority-${priority.toLowerCase()}`;
                
                return `
            <tr>
                <td><strong>${d.district}</strong></td>
                <td>${d.state}</td>
                <td>
                    <span class="severity-badge severity-${d.flood_severity.toLowerCase()}">
                        ${d.flood_severity}
                    </span>
                </td>
                <td>
                    <span class="severity-badge severity-${d.heat_alert_tier === "None" || d.heat_alert_tier === "Normal" ? "low" : d.heat_alert_tier.toLowerCase()}">
                        ${d.heat_alert_tier}
                    </span>
                </td>
                <td><strong>${d.dual_hazard_flag ? "YES ⚠️" : "NO"}</strong></td>
                <td><strong>${d.overall_risk_score.toFixed(1)}</strong></td>
                <td>${d.water_level_above_danger_m.toFixed(2)}m</td>
                <td>${d.response_teams_deployed} deployed</td>
                <td><span class="severity-badge ${priorityClass}">${priority}</span></td>
                <td>
                    <button class="btn-secondary" onclick="viewDistrict('${d.district_id}')">
                        Inspect
                    </button>
                </td>
            </tr>
        `;
            }
        )
        .join("");

    tbody.innerHTML = rows;
}

function triggerSort(col) {
    if (dbSort.column === col) {
        dbSort.direction = dbSort.direction === "asc" ? "desc" : "asc";
    } else {
        dbSort.column = col;
        dbSort.direction = "desc";
    }
    
    const headers = document.querySelectorAll(".sorting-header");
    headers.forEach(h => {
        h.classList.remove("sort-asc", "sort-desc");
    });
    
    const activeHeader = document.getElementById(`th-${col}`);
    if (activeHeader) {
        activeHeader.classList.add(dbSort.direction === "asc" ? "sort-asc" : "sort-desc");
    }
    
    applyDBFilters();
}

// ============================================================================
// EXPORT FILTERED CSV (Section 1)
// ============================================================================

function exportFilteredCSV(event) {
    if (event) event.stopPropagation();
    
    const stateVal = document.getElementById("dbFilterState").value;
    const floodVal = document.getElementById("dbFilterFlood").value;
    const heatVal = document.getElementById("dbFilterHeat").value;
    const dualVal = document.getElementById("dbFilterDual").value;
    const priorityVal = document.getElementById("dbFilterPriority").value;
    const teamsVal = document.getElementById("dbFilterTeams").value;
    const waterVal = document.getElementById("dbFilterWater").value;
    const historyVal = document.getElementById("dbFilterHistory").value;
    
    const minRisk = parseFloat(document.getElementById("dbFilterRiskMin").value) || 0;
    const maxRisk = parseFloat(document.getElementById("dbFilterRiskMax").value) || 100;
    const searchVal = document.getElementById("dbFilterSearch").value.toLowerCase().trim();

    let filtered = masterDistricts.filter(d => {
        if (stateVal !== "All" && (d.state || "").toLowerCase() !== stateVal.toLowerCase()) return false;
        if (floodVal !== "All" && d.flood_severity !== floodVal) return false;
        if (heatVal !== "All" && d.heat_alert_tier !== heatVal) return false;
        if (dualVal !== "All") {
            const isDual = d.dual_hazard_flag;
            if (dualVal === "Yes" && !isDual) return false;
            if (dualVal === "No" && isDual) return false;
        }
        const priority = derivePriority(d.overall_risk_score);
        if (priorityVal !== "All" && priority !== priorityVal) return false;
        if (teamsVal !== "All" && d.response_teams_deployed !== parseInt(teamsVal)) return false;
        if (waterVal !== "All" && d.water_level_above_danger_m <= parseFloat(waterVal)) return false;
        if (historyVal !== "All" && d.historical_flood_ratio <= parseFloat(historyVal)) return false;
        if (d.overall_risk_score < minRisk || d.overall_risk_score > maxRisk) return false;
        if (searchVal) {
            const name = (d.district || "").toLowerCase();
            const stateName = (d.state || "").toLowerCase();
            const id = (d.district_id || "").toLowerCase();
            if (!name.includes(searchVal) && !stateName.includes(searchVal) && !id.includes(searchVal)) return false;
        }
        return true;
    });

    if (filtered.length === 0) {
        alert("No records to export.");
        return;
    }

    let csv = "District_ID,District,State,Flood_Severity,Heat_Alert_Tier,Dual_Hazard,Overall_Risk_Score,Water_Level_Above_Danger_m,Response_Teams_Deployed,Operational_Priority\n";
    filtered.forEach(d => {
        const priority = derivePriority(d.overall_risk_score);
        const name = d.district.replace(/,/g, ""); 
        const stateName = (d.state || "").replace(/,/g, "");
        csv += `${d.district_id},${name},${stateName},${d.flood_severity},${d.heat_alert_tier},${d.dual_hazard_flag ? 'Yes' : 'No'},${d.overall_risk_score.toFixed(2)},${d.water_level_above_danger_m.toFixed(2)},${d.response_teams_deployed},${priority}\n`;
    });

    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    const url = URL.createObjectURL(blob);
    link.setAttribute("href", url);
    link.setAttribute("download", `EOC_Filtered_Districts_${new Date().toISOString().substring(0,10)}.csv`);
    link.style.visibility = "hidden";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function triggerQuickDBFilter(type) {
    resetDBFilters(false);
    
    if (type === 'critical_floods') {
        document.getElementById("dbFilterFlood").value = "Critical";
    } else if (type === 'maharashtra') {
        const stateSelect = document.getElementById("dbFilterState");
        for (let i = 0; i < stateSelect.options.length; i++) {
            if (stateSelect.options[i].value.toLowerCase() === "maharashtra") {
                stateSelect.value = stateSelect.options[i].value;
                break;
            }
        }
    } else if (type === 'dual_hazards') {
        document.getElementById("dbFilterDual").value = "Yes";
    } else if (type === 'high_risk') {
        document.getElementById("dbFilterRiskMin").value = "80";
        document.getElementById("dbFilterRiskMax").value = "100";
    } else if (type === 'zero_teams') {
        document.getElementById("dbFilterTeams").value = "0";
    } else if (type === 'danger_threshold') {
        document.getElementById("dbFilterWater").value = "1.5";
    }
    
    applyDBFilters();
}

function resetDBFilters(reRender = true) {
    document.getElementById("dbFilterState").value = "All";
    document.getElementById("dbFilterFlood").value = "All";
    document.getElementById("dbFilterHeat").value = "All";
    document.getElementById("dbFilterDual").value = "All";
    document.getElementById("dbFilterPriority").value = "All";
    document.getElementById("dbFilterTeams").value = "All";
    document.getElementById("dbFilterWater").value = "All";
    document.getElementById("dbFilterHistory").value = "All";
    document.getElementById("dbFilterRiskMin").value = "";
    document.getElementById("dbFilterRiskMax").value = "";
    document.getElementById("dbFilterSearch").value = "";
    
    if (reRender) {
        applyDBFilters();
    }
}

// ============================================================================
// MAP VIEW AND POLYGON HIGHLIGHT INTERACT (Section 8)
// ============================================================================

async function loadMap() {
    const params = getFilterParams();
    const geojson = await fetchAPI("/districts/geojson/map", params);

    if (!geojson) {
        console.error("Failed to load map GeoJSON data");
        return;
    }

    if (!mapInstance) {
        console.log("🗺️ Initializing Leaflet map viewport...");
        mapInstance = L.map('map', { 
            zoomControl: true,
            scrollWheelZoom: true 
        }).setView([22.973, 78.656], 5);

        L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CartoDB</a>',
            subdomains: 'abcd',
            maxZoom: 20
        }).addTo(mapInstance);
    }

    renderMap(geojson, params);
}

function renderMap(geojson, params) {
    if (geoJsonLayer) {
        mapInstance.removeLayer(geoJsonLayer);
    }

    function getRiskColor(score) {
        return score > 90 ? '#800000' : 
               score > 75 ? '#c62828' : 
               score > 50 ? '#ef6c00' : 
               score > 25 ? '#f9a825' : 
                            '#81c784'; 
    }

    function styleFeature(feature) {
        let score = feature.properties.overall_risk_score || 0;
        return {
            fillColor: getRiskColor(score),
            weight: 1,
            opacity: 1,
            color: 'rgba(255, 255, 255, 0.25)',
            fillOpacity: 0.55
        };
    }

    function onEachFeature(feature, layer) {
        let props = feature.properties;
        let stateName = props.state || props.st_nm || 'Unknown';
        
        let tooltipText = `<div class="popup-title">📍 ${props.district}</div>` +
                           `<div class="popup-grid">` +
                           `<span class="popup-lbl">State:</span><span class="popup-val">${stateName}</span>` +
                           `<span class="popup-lbl">Risk Index:</span><span class="popup-val" style="color:#ff9f43">${props.overall_risk_score?.toFixed(1) || 0}</span>` +
                           `<span class="popup-lbl">Flood Status:</span><span class="popup-val">${props.flood_severity || 'Low'}</span>` +
                           `<span class="popup-lbl">Heatwave Status:</span><span class="popup-val">${props.heat_alert_tier || 'None'}</span>` +
                           `</div>`;
        
        layer.bindTooltip(tooltipText, { sticky: true, className: 'leaflet-popup-content-wrapper' });
        
        layer.on({
            mouseover: function(e) {
                let l = e.target;
                l.setStyle({
                    weight: 2,
                    color: '#00f0ff',
                    fillOpacity: 0.75
                });
                l.bringToFront();
            },
            mouseout: function(e) {
                geoJsonLayer.resetStyle(e.target);
            },
            click: function(e) {
                viewDistrict(props.district_id);
            }
        });
    }

    geoJsonLayer = L.geoJSON(geojson, {
        style: styleFeature,
        onEachFeature: onEachFeature
    }).addTo(mapInstance);

    if (geojson.features && geojson.features.length > 0 && params.search && params.search.trim() !== '') {
        try {
            mapInstance.fitBounds(geoJsonLayer.getBounds(), { padding: [30, 30] });
        } catch (e) {
            console.warn("Could not align map bounds: ", e);
        }
    }
}

function highlightMapPolygon(districtId) {
    if (!geoJsonLayer || !mapInstance) return;
    
    geoJsonLayer.eachLayer(layer => {
        const props = layer.feature.properties;
        if (props.district_id === districtId) {
            layer.setStyle({
                weight: 3,
                color: '#00f0ff',
                fillOpacity: 0.8
            });
            mapInstance.setView(layer.getBounds().getCenter(), 8);
            layer.openTooltip();
        } else {
            geoJsonLayer.resetStyle(layer);
        }
    });
}

function highlightTableRow(districtId) {
    const rows = document.querySelectorAll("#districtTable tbody tr");
    rows.forEach(r => r.style.background = "");
    
    const buttons = document.querySelectorAll(`#districtTable tbody button`);
    buttons.forEach(btn => {
        if (btn.getAttribute("onclick") && btn.getAttribute("onclick").includes(districtId)) {
            const targetRow = btn.closest("tr");
            if (targetRow) {
                targetRow.style.background = "rgba(13, 148, 136, 0.15)";
                targetRow.scrollIntoView({ behavior: "smooth", block: "nearest" });
            }
        }
    });
}

// ============================================================================
// GENERAL FILTER TOOLBAR (Map & Alert Stream)
// ============================================================================

function getFilterParams() {
    return {
        disaster_type: document.getElementById("filterDisaster").value,
        severity: document.getElementById("filterSeverity").value,
        search: document.getElementById("filterSearch").value.trim(),
    };
}

async function applyFilters() {
    console.log("🔄 Applying map & feed filters...");
    await loadKPIs();
    await loadMap();
}

// ============================================================================
// DRILLDOWN DRAWER DETAILED REVELATION (Section 2)
// ============================================================================

async function viewDistrict(districtId) {
    const response = await fetchAPI(`/districts/${districtId}`);

    if (!response || !response.district) {
        alert("Failed to load operational intelligence records for this district");
        return;
    }

    selectedDistrict = response.district;
    const insights = response.insights || {};

    let stateName = selectedDistrict.state || selectedDistrict.st_nm || 'Unknown';

    let flagsHTML = '';
    let riskFlags = insights.risk_flags || [];
    if (!Array.isArray(riskFlags) && typeof riskFlags === 'object') {
        riskFlags = Object.entries(riskFlags).map(([k, v]) => `${k}: ${v}`);
    }

    if (riskFlags.length > 0) {
        flagsHTML = `
            <div class="risk-flags-container" style="margin-top: 0.5rem; margin-bottom: 0.5rem;">
                ${riskFlags.map(flag => {
                    let cls = '';
                    let flg = flag.toLowerCase();
                    if (flg.includes('dual')) cls = 'dual-flag';
                    else if (flg.includes('flood') || flg.includes('water') || flg.includes('discharge')) cls = 'flood-flag';
                    else if (flg.includes('heat') || flg.includes('temp') || flg.includes('wave')) cls = 'heat-flag';
                    return `<span class="flag-badge ${cls}">${flag}</span>`;
                }).join('')}
            </div>
        `;
    }

    const priority = derivePriority(selectedDistrict.overall_risk_score);
    const priorityClass = `priority-${priority.toLowerCase()}`;

    let drawerHTML = `
        <div class="drawer-grid">
            <div class="drawer-metric-card">
                <span class="drawer-lbl">District Name</span>
                <span class="drawer-val">${selectedDistrict.district}</span>
            </div>
            <div class="drawer-metric-card">
                <span class="drawer-lbl">State / Province</span>
                <span class="drawer-val">${stateName}</span>
            </div>
            <div class="drawer-metric-card">
                <span class="drawer-lbl">Operational Priority</span>
                <span class="drawer-val ${priorityClass}">${priority}</span>
            </div>
            <div class="drawer-metric-card">
                <span class="drawer-lbl">Overall Risk Score</span>
                <span class="drawer-val" style="color:#d97706;">${selectedDistrict.overall_risk_score.toFixed(1)}</span>
            </div>
        </div>

        <div class="drawer-insight-block">
            <h4>🌧️ Hydrological Metrics</h4>
            <div class="drawer-grid" style="margin-top: 0.5rem;">
                <div class="drawer-metric-card">
                    <span class="drawer-lbl">Flood Severity</span>
                    <span class="drawer-val">${selectedDistrict.flood_severity}</span>
                </div>
                <div class="drawer-metric-card">
                    <span class="drawer-lbl">Water Above Danger Line</span>
                    <span class="drawer-val">${selectedDistrict.water_level_above_danger_m.toFixed(2)}m</span>
                </div>
                <div class="drawer-metric-card">
                    <span class="drawer-lbl">Active Hotspots</span>
                    <span class="drawer-val">${selectedDistrict.active_flood_hotspots}</span>
                </div>
                <div class="drawer-metric-card">
                    <span class="drawer-lbl">Response Teams</span>
                    <span class="drawer-val">${selectedDistrict.response_teams_deployed} deployed</span>
                </div>
            </div>
        </div>

        <div class="drawer-insight-block">
            <h4>☀️ Thermal Exposure Metrics</h4>
            <div class="drawer-grid" style="margin-top: 0.5rem;">
                <div class="drawer-metric-card">
                    <span class="drawer-lbl">Heat wave Alert Tier</span>
                    <span class="drawer-val">${selectedDistrict.heat_alert_tier}</span>
                </div>
                <div class="drawer-metric-card">
                    <span class="drawer-lbl">Dual Hazard Status</span>
                    <span class="drawer-val">${selectedDistrict.dual_hazard_flag ? 'ACTIVE ⚠️' : 'Normal'}</span>
                </div>
            </div>
        </div>

        <div class="drawer-insight-block">
            <h4>📋 Situation Room AI Summary</h4>
            ${flagsHTML}
            <div class="drawer-summary-box">
                ${insights.summary || 'No operational narrative generated for this district.'}
            </div>
        </div>

        <div class="drawer-insight-block">
            <h4>🛠️ Recommended Actions (SOP)</h4>
            <ul class="drawer-list">
                ${insights.recommended_actions && insights.recommended_actions.length > 0
                    ? insights.recommended_actions.map(action => `<li>${action}</li>`).join('')
                    : '<li>Continue routine command center monitoring patrols.</li>'
                }
            </ul>
        </div>
    `;

    document.getElementById("drawerTitle").textContent = `📍 ${selectedDistrict.district}, ${stateName} Profile`;
    document.getElementById("drawerContent").innerHTML = drawerHTML;

    document.getElementById("drilldownDrawer").classList.add("open");
    document.getElementById("drawerOverlay").classList.add("open");

    highlightTableRow(districtId);
    highlightMapPolygon(districtId);
}

function closeDrilldownDrawer() {
    selectedDistrict = null;
    document.getElementById("drilldownDrawer").classList.remove("open");
    document.getElementById("drawerOverlay").classList.remove("open");
    
    const rows = document.querySelectorAll("#districtTable tbody tr");
    rows.forEach(r => r.style.background = "");
}

// ============================================================================
// AI GROUNDED OPERATOR ASSISTANT
// ============================================================================

async function submitQuestion() {
    const question = document.getElementById("assistantQuestion").value.trim();

    if (!question) {
        alert("Please type an operational query first.");
        return;
    }

    const placeholder = document.getElementById("assistantPlaceholder");
    const container = document.getElementById("assistantResponse");
    const output = document.getElementById("assistantAnswer");

    placeholder.style.display = "none";
    container.style.display = "block";
    output.innerHTML = '<p class="loading">Querying grounded command console... (Waiting for Gemini)</p>';

    const params = getFilterParams();
    const filteredDistricts = await fetchAPI("/districts", params);
    const districtIds = filteredDistricts ? filteredDistricts.map((d) => d.district_id) : [];

    try {
        const response = await fetch(`${API_BASE}/assistant`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                question: question,
                filtered_districts: districtIds,
            }),
        });

        if (!response.ok) {
            throw new Error(`Server returned code ${response.status}`);
        }

        const result = await response.json();

        if (result.success) {
            output.innerHTML = formatMarkdown(result.answer);
            queryCounter++;
            document.getElementById("statAIQueries").textContent = queryCounter;
        } else {
            output.innerHTML = `<span style="color:var(--neon-red)">Error: ${result.error || "Grounded analysis failed"}</span>`;
        }
    } catch (err) {
        console.error("AI assistant query failed: ", err);
        output.innerHTML = `<span style="color:var(--neon-red)">Terminal error querying grounded assistant: ${err.message}</span>`;
    }
}

function setQuestion(question) {
    document.getElementById("assistantQuestion").value = question;
}

function formatMarkdown(text) {
    if (!text) return '';
    
    let html = text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");

    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/^\s*[-*]\s+(.*)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*?<\/li>)+/gs, '<ul>$&</ul>');
    
    html = html.split('\n').map(line => {
        let trimmed = line.trim();
        if (trimmed.startsWith('<ul>') || trimmed.startsWith('</ul>') || trimmed.startsWith('<li>') || trimmed.startsWith('</li>')) {
            return line;
        }
        return line + '<br>';
    }).join('\n');
    
    return html;
}
