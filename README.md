# Solar Finance Agent (CLI)

A local CLI agent that helps you build a **solar project financial model** and publish it as a **Google Sheets workbook** with:

- An **Assumptions** tab (key levers highlighted)
- A **Cash Flow** tab (15–25 year projections)
- An **IRR_NPV** tab (returns + simple sensitivities)

## What this does today

1. Prompts for core project details and capital stack assumptions.
2. Flags likely missing/problematic inputs (e.g., capital stack not summing to 100%).
3. Builds a levered annual cash flow projection.
4. Calculates sponsor-equity IRR and NPV.
5. Publishes a Google Sheet workbook with the model output.
6. Supports webhook-based ingestion so you can trigger runs via **WhatsApp**, SMS, or email.

## Quickstart

### 1) Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2) Set up Google Sheets API credentials

- Create a Google Cloud project and enable **Google Sheets API** and **Google Drive API**.
- Create a service account and download its JSON key.
- Share the target Google Drive folder (or future sheet) with the service-account email.

### 3) Run CLI mode

```bash
solar-finance-agent --service-account-json /path/to/service_account.json --sheet-title "Project Falcon Solar Model"
```

You will be prompted for the project assumptions and capital stack.

## WhatsApp/SMS/Email interface (Webhook mode)

Run the API server locally:

```bash
export GOOGLE_SERVICE_ACCOUNT_JSON=/path/to/service_account.json
uvicorn solar_finance_agent.server:app --host 0.0.0.0 --port 8000
```

### Expected message format (WhatsApp/SMS/email body)

Use newline-delimited `key=value` pairs:

```text
project_name=Falcon Solar
project_size_mw=120
capex_per_watt=1.12
capacity_factor=0.29
ppa_price_per_mwh=61
opex_per_kw_year=17
annual_degradation_pct=0.005
merchant_tail_price_per_mwh=44
merchant_tail_start_year=16
analysis_years=20
discount_rate=0.08
debt_pct=0.55
tax_equity_pct=0.25
sponsor_equity_pct=0.20
debt_rate=0.062
debt_tenor_years=15
sheet_title=Falcon SMS Run
```

### Endpoints

- `POST /webhooks/whatsapp` with form field `Body` (Twilio WhatsApp webhook payload)
- `POST /webhooks/sms` with form field `Body` (Twilio SMS payload)
- `POST /webhooks/email` with JSON payload containing `text` field

### How to wire providers

- **WhatsApp (recommended)**: Use Twilio WhatsApp sandbox/number webhook URL → `https://<your-host>/webhooks/whatsapp`
- **SMS**: Use Twilio SMS webhook URL → `https://<your-host>/webhooks/sms`
- **Email**: Use SendGrid inbound parse, Mailgun routes, or Postmark inbound webhook → `https://<your-host>/webhooks/email`
- For local development, expose your machine using `ngrok http 8000` and configure provider webhook URL to the ngrok URL.

### Is WhatsApp easier than email/SMS?

Usually **yes** for this workflow:
- Better for multi-line, structured `key=value` messages than SMS character-limited threads.
- Easier user experience than email (faster back-and-forth, fewer formatting issues).
- Twilio can host both WhatsApp and SMS, so you can keep one webhook backend and support both channels.

Email is still useful for long-form context, attachments, and forwarding model outputs to wider stakeholders.

If required fields are missing, the response lists missing assumption/capital-stack fields. If complete, response includes the generated Google Sheet URL + IRR/NPV summary.

## Modeling notes

- CAPEX is based on `project_size_mw * 1,000,000 * capex_per_watt`.
- Generation declines annually with degradation.
- Revenue uses PPA price until merchant-tail start year, then switches to merchant price.
- Debt service is levelized over debt tenor.
- IRR is calculated from sponsor-equity outflow at year 0 and annual levered cash flows thereafter.

## Suggested next enhancements

- ITC/PTC support and tax-equity waterfall distributions
- DSCR, LLCR, sculpted debt profiles
- Construction draw schedule and COD date handling
- Monthly/quarterly periods instead of annual only
- Multi-scenario batch run + charting
- Conversation state store so the agent can ask follow-up questions over multiple texts/emails
