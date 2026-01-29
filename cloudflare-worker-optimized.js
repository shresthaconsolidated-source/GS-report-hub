export default {
    async fetch(request, env, ctx) {
        // Handle preflight (OPTIONS)
        if (request.method === "OPTIONS") {
            return new Response(null, {
                status: 204,
                headers: corsHeaders()
            });
        }

        try {
            if (!env.NOTION_TOKEN || !env.NOTION_DB_ID) {
                return jsonError("Missing NOTION_TOKEN or NOTION_DB_ID");
            }

            // ============================================
            // CACHE KEY - Cache for 5 minutes
            // ============================================
            const cacheKey = `hr-data-${env.NOTION_DB_ID}`;
            const cache = caches.default;
            const cacheUrl = new URL(request.url);

            // Try to get from cache first
            let response = await cache.match(cacheUrl);

            if (response) {
                console.log("Returning cached data");
                // Add header to indicate it's cached
                const newHeaders = new Headers(response.headers);
                newHeaders.set("X-Cache", "HIT");
                return new Response(response.body, {
                    status: response.status,
                    headers: newHeaders
                });
            }

            console.log("Cache miss - fetching from Notion");

            // Load from Notion
            const data = await loadNotion(env);
            let employees = data.results.map(mapEmployee);

            // Normalize status
            employees.forEach(normalizeStatus);

            const now = new Date();

            // Summary
            const totalEmployees = employees.length;
            const activeEmployees = employees.filter(e => e.status === "Active").length;
            const inactiveEmployees = employees.filter(e => e.status === "Inactive").length;
            const probationEndingSoon = employees.filter(e =>
                e.status === "Probation" &&
                e.probation_end &&
                daysBetween(now, new Date(e.probation_end)) >= 0 &&
                daysBetween(now, new Date(e.probation_end)) <= 30
            ).length;

            // Group breakdowns
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

            // Create response
            response = new Response(JSON.stringify(final, null, 2), {
                headers: {
                    ...jsonHeaders(),
                    "X-Cache": "MISS",
                    "Cache-Control": "public, max-age=300" // 5 minutes
                }
            });

            // Store in cache for 5 minutes
            ctx.waitUntil(cache.put(cacheUrl, response.clone()));

            return response;

        } catch (err) {
            return jsonError("Failed to load HR data", err.toString());
        }
    }
};

/* ============================================================================ */

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

function jsonError(msg, details = "") {
    return new Response(JSON.stringify({ error: msg, details }), {
        status: 500,
        headers: jsonHeaders()
    });
}

/* ============================================================================ */

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

/* ============================================================================ */

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
        // Additional fields
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

    // Override to Probation if probation end date is in future
    if (e.probation_end) {
        const end = new Date(e.probation_end);
        if (end > new Date() && e.status === "Active") e.status = "Probation";
    }

    e.status_clean = e.status;
}

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
