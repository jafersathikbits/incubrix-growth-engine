# 30-Day Launch Kit

## Week 1: Infrastructure & Warm-up
* **Action:** Import the `production_priority_a.csv` into the CRM.
* **Action:** Connect the Email sequence to the SMTP provider. Verify domain reputation.
* **Volume:** Send 20 emails/day manually to test deliverability.
* **Target:** 5% reply rate (15 replies).

## Week 2: Scale Outbound
* **Action:** Increase volume to 50 emails/day.
* **Action:** Begin manual LinkedIn connection requests to the backup channels of Priority A leads.
* **Volume:** 50 Emails/day, 20 LinkedIn connections/day.
* **Target:** 5% reply rate (50 replies), 3 discovery calls booked.

## Week 3: Demo & Pilot
* **Action:** Run discovery calls. Pitch the "Course-to-Shorts" use case specifically.
* **Action:** Offer a 7-day free pilot to the first 5 interested creators.
* **Volume:** 50 Emails/day, 20 LinkedIn connections/day.
* **Target:** 5 pilots secured.

## Week 4: Review & Iterate
* **Action:** Analyze which subject lines and segments performed best.
* **Action:** Pause outreach to non-responders and focus on closing the 5 pilots.
* **Target:** 2 paid conversions.

## Pricing & Business Model
* **Global Pricing:** $99/mo (Standard) / $249/mo (Pro). *Note: Since our target creators are US/UK/AU-based, pricing is anchored in USD to reflect international SaaS standards. For the domestic Indian market, this translates to roughly ₹8,250/mo.*
* **Why this works:** The LTV (Lifetime Value) of a creator saving 10+ hours a week on editing easily justifies $99/mo.
* **Expected ROI for Creator:** Replacing a freelance video editor (which costs $500-$1000/mo) with IncuBrix for $99/mo.

## Scaling & Infrastructure Costs (Production)

During the 7-day testing phase, this engine ran on **$0 (₹0)** using free API tiers. To scale this to IncuBrix's production level (running weekly at 3,000+ leads), the following infrastructure upgrades are required:

1. **YouTube Data API v3 Quota:** The free tier allows 10,000 units/day, which a 3,000-lead search will exhaust in minutes. We must apply for a **Quota Extension** via the Google Cloud Console (free, but requires a 1-2 day review process).
2. **Groq API (Llama 3):** The free tier limits (30 requests/min, 1,000/day) will cause HTTP 429 errors during batch processing. Upgrading to the **Groq Developer Tier** costs approx. **$2.00/month (~₹166/month)** for our expected volume of 6,000 leads.
3. **Email Deliverability:** Sending 50+ cold emails/day via a standard Gmail account will result in spam blocking. IncuBrix must provision a dedicated cold-email tool (e.g., **Instantly.ai**, approx. **$37/month / ~₹3,071/month**) with warmed-up domains to ensure a 95%+ inbox placement rate.

**Total Estimated Monthly Infrastructure Cost:** ~$39/month (~₹3,237/month). 
*This is highly profitable compared to our $99/mo (~₹8,250/mo) target pricing.*
