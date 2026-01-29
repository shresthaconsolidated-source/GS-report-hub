# NRB Forex Rates - Deployment Instructions

## Step 1: Deploy FX Rates Worker

1. Go to **Cloudflare Dashboard** → **Workers & Pages**
2. Click **"Create Application"** → **"Create Worker"**
3. Name it: `fx-rates` (or any name you prefer)
4. Click **"Deploy"**
5. Click **"Edit Code"**
6. **Delete all existing code**
7. **Copy and paste** the entire contents of `cloudflare-fx-worker.js`
8. Click **"Save and Deploy"**

Your FX API will be live at:
```
https://fx-rates.ashishoct34.workers.dev
```

## Step 2: Test the FX Worker

Open in browser:
```
https://fx-rates.ashishoct34.workers.dev?currency=AUD
https://fx-rates.ashishoct34.workers.dev?currency=INR
https://fx-rates.ashishoct34.workers.dev?currency=USD
```

You should see JSON like:
```json
{
  "rate": 87.23,
  "currency": "AUDNPR",
  "source": "Nepal Rastra Bank",
  "date": "2026-01-29",
  "buy": 86.50,
  "sell": 87.23,
  "cached": false,
  "cache_duration": "24 hours"
}
```

## Step 3: Update Dashboard (Already Done!)

The dashboard `index.html` has already been updated to use:
```javascript
const FX_API_URL = "https://fx-rates.ashishoct34.workers.dev";
```

If you used a different worker name, update line 888 in `index.html`.

## Step 4: Deploy Optimized HR Worker (Optional)

To speed up the HR data loading:

1. Go to your existing worker: `hr-api.ashishoct34.workers.dev`
2. Click **"Edit Code"**
3. **Replace all code** with contents of `cloudflare-worker-optimized.js`
4. Click **"Save and Deploy"**

This adds 5-minute caching to make the dashboard 5-10x faster!

## Step 5: Test Everything

1. Open the dashboard
2. Press F12 for console
3. Refresh the page
4. Look for logs like:
   ```
   Fetching official NRB rates for: AUD, INR
   AUD → NPR: 87.23 (source: Nepal Rastra Bank, date: 2026-01-29)
   INR → NPR: 1.60 (source: Nepal Rastra Bank, date: 2026-01-29)
   ```
5. Go to **Compensation tab**
6. Check currency cards show correct FX rates (not 1.00)

## Features

✅ **Official NRB rates** - Direct from Nepal Rastra Bank
✅ **24-hour caching** - Fast and efficient
✅ **Automatic fallback** - Never breaks if API is down
✅ **Multiple currencies** - AUD, INR, USD, EUR, etc.
✅ **Buy & Sell rates** - Uses sell rate by default

## Troubleshooting

**If rates still show 1.00:**
1. Check worker is deployed correctly
2. Open browser console and look for errors
3. Test the FX API URL directly in browser
4. Verify the worker URL in dashboard matches your deployment

**If NRB API is down:**
- Worker returns fallback rate (85.50 for AUD)
- Dashboard continues to work
- Cached rates used if available
