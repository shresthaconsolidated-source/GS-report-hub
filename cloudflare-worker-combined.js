/**
 * Combined Cloudflare Worker: HR Data + FX Rates
 * 
 * Routes:
 * - /api/hr          → Employee data from Notion (5-min cache)
 * - /api/fx?currency=AUD → Official NRB forex rates (24-hour cache)
 */

export default {
    async fetch(request, env, ctx) {
        // Handle CORS preflight
        if (request.method === "OPTIONS") {
            return new Response(null, {
                status: 204,
                headers: corsHeaders()
            });
        }

        const url = new URL(request.url);

        try {
            // Route 1: FX Rates
            if (url.pathname === "/api/fx") {
                return await handleFxRates(request, env, ctx);
            }

            // Route 2: HR Data
            if (url.pathname === "/api/hr") {
                return await handleHrData(request, env, ctx);
            }

            // Default: Show available endpoints
            return jsonResponse({
                message: "HR API with FX Rates",
                endpoints: {
                    hr_data: "/api/hr",
                    fx_rates: "/api/fx?currency=AUD"
                },
                version: "2.0"
            });

        } catch (err) {
            return jsonError("Request failed", err.toString());
        }
    }
};

/* ============================================================================
   FX RATES HANDLER - Official NRB Rates
============================================================================ */

async function handleFxRates(request, env, ctx) {
    const url = new URL(request.url);
    const currency = url.searchParams.get("currency") || "AUD";

    try {
        // Try cache first (v2 to invalidate old 160.15 INR cache)
        const cacheKey = `fx-rate-v2-${currency}`;
        const cache = caches.default;
        const cacheUrl = new URL(`https://fx-cache/${cacheKey}`);

        let response = await cache.match(cacheUrl);

        if (response) {
            const data = await response.json();
            return jsonResponse({ ...data, cached: true });
        }

        // Fetch from Nepal Rastra Bank
        // NRB API requires date parameters
        const today = new Date().toISOString().split('T')[0];
        const nrbUrl = `https://www.nrb.org.np/api/forex/v1/rates?page=1&per_page=100&from=${today}&to=${today}`;

        const nrbResponse = await fetch(nrbUrl);
        if (!nrbResponse.ok) {
            throw new Error(`NRB API failed with status ${nrbResponse.status}`);
        }

        const nrbData = await nrbResponse.json();

        // Extract rates from the correct nested structure
        const payload = nrbData.data?.payload?.[0];
        if (!payload || !payload.rates) {
            throw new Error("No forex data available");
        }

        const latestRates = payload.rates;
        const rateDate = payload.date;

        // Find the requested currency (e.g., AUD, USD, INR)
        const currencyData = latestRates.find(item => item.currency?.iso3 === currency);

        if (!currencyData) {
            return jsonResponse({
                error: `Currency ${currency} not found`,
                available: latestRates.map(r => r.currency?.iso3).filter(Boolean)
            }, 404);
        }
        // Use sell rate (what you pay in NPR to buy the foreign currency)
        const sellRate = parseFloat(currencyData.sell) || parseFloat(currencyData.buy);
        const buyRate = parseFloat(currencyData.buy);
        const unit = parseInt(currencyData.currency?.unit) || 1;

        // Adjust for unit (e.g., INR is per 100, so divide by 100)
        const rate = sellRate / unit;

        const result = {
            rate: rate,
            currency: `${currency}NPR`,
            source: "Nepal Rastra Bank",
            date: rateDate,
            buy: buyRate / unit,
            sell: sellRate / unit,
            unit: unit,
            cached: false
        };

        response = jsonResponse(result);

        // Cache for 24 hours
        const cacheResponse = new Response(JSON.stringify(result), {
            headers: {
                ...corsHeaders(),
                "Content-Type": "application/json",
                "Cache-Control": "public, max-age=86400"
            }
        });

        ctx.waitUntil(cache.put(cacheUrl, cacheResponse));
        return response;

    } catch (error) {
        // Fallback rate if NRB API fails
        return jsonResponse({
            rate: 85.50,
            currency: `${currency}NPR`,
            source: "Fallback (NRB unavailable)",
            date: new Date().toISOString().split('T')[0],
            error: error.message,
            cached: false
        });
    }
}

/* ============================================================================
   HR DATA HANDLER - Employee Data from Notion
============================================================================ */

async function handleHrData(request, env, ctx) {
    try {
        if (!env.NOTION_TOKEN || !env.NOTION_DB_ID) {
            return jsonError("Missing NOTION_TOKEN or NOTION_DB_ID");
        }

        // Try cache first (5 minutes)
        const cacheKey = `hr-data-${env.NOTION_DB_ID}`;
        const cache = caches.default;
        const cacheUrl = new URL(request.url);

        let response = await cache.match(cacheUrl);

        if (response) {
            const newHeaders = new Headers(response.headers);
            newHeaders.set("X-Cache", "HIT");
            return new Response(response.body, {
                status: response.status,
                headers: newHeaders
            });
        }

        // Load from Notion
        const data = await loadNotion(env);
        let employees = data.results.map(mapEmployee);
        employees.forEach(normalizeStatus);

        const now = new Date();
        const totalEmployees = employees.length;
        const activeEmployees = employees.filter(e => e.status === "Active").length;
        const inactiveEmployees = employees.filter(e => e.status === "Inactive").length;
        const probationEndingSoon = employees.filter(e =>
            e.status === "Probation" &&
            e.probation_end &&
            daysBetween(now, new Date(e.probation_end)) >= 0 &&
            daysBetween(now, new Date(e.probation_end)) <= 30
        ).length;

        const byDepartment = countBy(employees, "department");
        const byDesignation = countBy(employees, "designation");
        const byGender = countBy(employees, "gender");
        const byEducation = countBy(employees, "education");

        const avgSalaryByDept = groupAverage(employees, "department", "salary_npr");
        const avgSalaryByDesig = groupAverage(employees, "designation", "salary_npr");

        const final = {
            last_refreshed: new Date().toISOString(),
            cache_duration: "5 minutes",
            summary: {
                total_employees: totalEmployees,
                active_employees: activeEmployees,
                inactive_employees: inactiveEmployees,
                probation_next_30_days: probationEndingSoon
            },
            breakdowns: {
                by_department: byDepartment,
                by_designation: byDesignation,
                by_gender: byGender,
                by_education: byEducation
            },
            avg_salary_by_department: avgSalaryByDept,
            avg_salary_by_designation: avgSalaryByDesig,
            employees: employees
        };

        response = new Response(JSON.stringify(final, null, 2), {
            headers: {
                ...jsonHeaders(),
                "X-Cache": "MISS",
                "Cache-Control": "public, max-age=300"
            }
        });

        ctx.waitUntil(cache.put(cacheUrl, response.clone()));
        return response;

    } catch (err) {
        return jsonError("Failed to load HR data", err.toString());
    }
}

/* ============================================================================
   NOTION API
============================================================================ */

async function loadNotion(env) {
    const res = await fetch(
        `https://api.notion.com/v1/databases/${env.NOTION_DB_ID}/query`,
        {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${env.NOTION_TOKEN}`,
                "Content-Type": "application/json",
                "Notion-Version": "2022-06-28"
            }
        }
    );

    if (!res.ok) throw new Error(`Notion failed with status ${res.status}`);
    return res.json();
}

function mapEmployee(item) {
    const p = item.properties;

    return {
        id: getText(p["Employee ID"]),
        employee_id: getText(p["Employee ID"]),
        name: getText(p["Name of employee"]),
        designation: getSelect(p["Designation"]) || "Unknown",
        department: getSelect(p["Department"]) || "Unknown",
        country: getSelect(p["Country"]) || "Unknown",
        gender: getSelect(p["Gender"]) || "Unknown",
        education: getSelect(p["Education/Qualification"]) || "Unknown",
        joining_date: getDate(p["Joining Date"]),
        probation_end: getDate(p["Probation End Date"]),
        dob: getDate(p["DOB"]),
        exit_reason: getSelect(p["Exit Reason"]),
        salary_currency: (getSelect(p["Salary FX"]) || "NPR").toUpperCase(),
        salary_fx: (getSelect(p["Salary FX"]) || "NPR").toUpperCase(),
        last_salary: Number(getNumber(p["Revised Salary (NPR)"])) || 0,
        base_salary: Number(getNumber(p["Revised Salary (NPR)"])) || 0,
        status_raw: getFormula(p["Status"]) || "",
        salary_npr: 0,
        reporting_manager: getText(p["Reporting Manager"]),
        email: getText(p["Email"]),
        phone: getText(p["Phone"]),
        citizenship: getText(p["Citizenship"]),
        bank_account: getText(p["Bank Account"]),
        pan: getText(p["PAN"]),
        remarks: getText(p["Remarks"]),
        years_of_experience: getText(p["Years of Experience"]),
        last_working_date: getDate(p["Last Working Date"])
    };
}

function normalizeStatus(e) {
    const raw = (e.status_raw || "").toLowerCase().trim();
    const clean = raw.replace(/[^a-z]/gi, "");

    if (clean === "active") e.status = "Active";
    else if (clean === "inactive") e.status = "Inactive";
    else if (clean === "probation") e.status = "Probation";
    else e.status = "Inactive";

    if (e.probation_end) {
        const end = new Date(e.probation_end);
        if (end > new Date() && e.status === "Active") e.status = "Probation";
    }

    e.status_clean = e.status;
}

/* ============================================================================
   UTILITIES
============================================================================ */

function countBy(list, field) {
    const result = {};
    list.forEach(i => {
        const key = i[field] || "Unknown";
        result[key] = (result[key] || 0) + 1;
    });
    return result;
}

function groupAverage(list, groupField, valueField) {
    const groups = {};
    list.forEach(i => {
        const g = i[groupField] || "Unknown";
        if (!groups[g]) groups[g] = { sum: 0, count: 0 };
        groups[g].sum += Number(i[valueField]) || 0;
        groups[g].count++;
    });

    const result = {};
    Object.keys(groups).forEach(g => {
        result[g] = groups[g].count > 0
            ? Math.round(groups[g].sum / groups[g].count)
            : 0;
    });

    return result;
}

function daysBetween(a, b) {
    return Math.floor((b - a) / (1000 * 60 * 60 * 24));
}

function getText(prop) { return prop?.rich_text?.[0]?.plain_text || ""; }
function getSelect(prop) { return prop?.select?.name || ""; }
function getNumber(prop) { return prop?.number || 0; }
function getDate(prop) { return prop?.date?.start || null; }
function getFormula(prop) { return prop?.formula?.string || ""; }

function corsHeaders() {
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "*"
    };
}

function jsonHeaders() {
    return {
        ...corsHeaders(),
        "Content-Type": "application/json"
    };
}

function jsonResponse(data, status = 200) {
    return new Response(JSON.stringify(data, null, 2), {
        status: status,
        headers: jsonHeaders()
    });
}

function jsonError(msg, details = "") {
    return new Response(JSON.stringify({ error: msg, details }), {
        status: 500,
        headers: jsonHeaders()
    });
}
