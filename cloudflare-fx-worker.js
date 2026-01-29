/**
 * Cloudflare Worker: NRB Forex Rates API Proxy
 * Fetches official Nepal Rastra Bank rates and caches for 24 hours
 * 
 * Deploy: https://fx-rates.YOUR-SUBDOMAIN.workers.dev
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

        try {
            const url = new URL(request.url);
            const currency = url.searchParams.get("currency") || "AUD";

            // Try to get from cache first
            const cacheKey = `fx-rate-${currency}`;
            const cache = caches.default;
            const cacheUrl = new URL(`https://fx-cache/${cacheKey}`);

            let response = await cache.match(cacheUrl);

            if (response) {
                console.log(`Cache HIT for ${currency}`);
                const data = await response.json();
                return jsonResponse({ ...data, cached: true });
            }

            console.log(`Cache MISS for ${currency} - fetching from NRB`);

            // Fetch from Nepal Rastra Bank API
            const nrbResponse = await fetch("https://www.nrb.org.np/api/forex/v1/rates");

            if (!nrbResponse.ok) {
                throw new Error(`NRB API failed with status ${nrbResponse.status}`);
            }

            const nrbData = await nrbResponse.json();

            // Extract the latest rates
            const latestRates = nrbData.data?.payload || [];

            if (!latestRates || latestRates.length === 0) {
                throw new Error("No forex data available from NRB");
            }

            // Find the requested currency (e.g., AUD, USD, INR)
            const currencyData = latestRates.find(item =>
                item.currency?.iso3 === currency
            );

            if (!currencyData) {
                return jsonResponse({
                    error: `Currency ${currency} not found in NRB data`,
                    available: latestRates.map(r => r.currency?.iso3).filter(Boolean)
                }, 404);
            }

            // Use sell rate (what you pay in NPR to buy the foreign currency)
            const rate = parseFloat(currencyData.sell) || parseFloat(currencyData.buy);
            const date = nrbData.data?.date || new Date().toISOString().split('T')[0];

            const result = {
                rate: rate,
                currency: `${currency}NPR`,
                source: "Nepal Rastra Bank",
                date: date,
                buy: parseFloat(currencyData.buy),
                sell: parseFloat(currencyData.sell),
                cached: false,
                cache_duration: "24 hours"
            };

            // Create response
            response = jsonResponse(result);

            // Cache for 24 hours (86400 seconds)
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
            console.error("Error fetching FX rates:", error);

            // Return fallback rate if API fails
            return jsonResponse({
                rate: 85.50, // Fallback AUD rate
                currency: "AUDNPR",
                source: "Fallback (NRB API unavailable)",
                date: new Date().toISOString().split('T')[0],
                error: error.message,
                cached: false
            }, 200); // Return 200 so dashboard doesn't break
        }
    }
};

function corsHeaders() {
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "*"
    };
}

function jsonResponse(data, status = 200) {
    return new Response(JSON.stringify(data, null, 2), {
        status: status,
        headers: {
            ...corsHeaders(),
            "Content-Type": "application/json"
        }
    });
}
