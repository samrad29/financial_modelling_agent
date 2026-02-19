from __future__ import annotations

import os
from typing import Dict

from fastapi import FastAPI, Form, Request
from fastapi.responses import JSONResponse

from solar_finance_agent.agent import parse_structured_message, run_agent_from_data

app = FastAPI(title="Solar Finance Agent Webhooks")


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/webhooks/sms")
def sms_webhook(Body: str = Form(default="")) -> JSONResponse:
    return _handle_message(Body, channel="sms")


@app.post("/webhooks/whatsapp")
def whatsapp_webhook(Body: str = Form(default="")) -> JSONResponse:
    """Twilio WhatsApp inbound webhook compatible endpoint."""
    return _handle_message(Body, channel="whatsapp")


@app.post("/webhooks/email")
async def email_webhook(request: Request) -> JSONResponse:
    payload = await request.json()
    body = str(payload.get("text", ""))
    return _handle_message(body, channel="email")


def _handle_message(message_body: str, channel: str) -> JSONResponse:
    service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    if not service_account_json:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error": "Set GOOGLE_SERVICE_ACCOUNT_JSON env var to your credential path.",
            },
        )

    data = parse_structured_message(message_body)
    sheet_title = data.get("sheet_title", f"Solar Model ({channel})")

    result = run_agent_from_data(
        data=data,
        service_account_json_path=service_account_json,
        sheet_title=str(sheet_title),
    )

    if result["status"] == "needs_input":
        missing = result["missing"]
        return JSONResponse(
            status_code=200,
            content={
                "status": "needs_input",
                "channel": channel,
                "message": "I need more details before building the model.",
                "missing_assumptions": missing["assumptions"],
                "missing_capital_stack": missing["capital_stack"],
            },
        )

    return JSONResponse(
        status_code=200,
        content={
            "status": "ok",
            "channel": channel,
            "sheet_url": result["sheet_url"],
            "project_irr": result["project_irr"],
            "project_npv": result["project_npv"],
        },
    )
