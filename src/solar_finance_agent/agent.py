from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, Tuple

from solar_finance_agent.model import CapitalStack, ProjectAssumptions, build_financial_model
from solar_finance_agent.sheet_export import export_to_google_sheets

REQUIRED_ASSUMPTION_KEYS = {
    "project_name",
    "project_size_mw",
    "capex_per_watt",
    "capacity_factor",
    "ppa_price_per_mwh",
    "opex_per_kw_year",
    "annual_degradation_pct",
    "merchant_tail_price_per_mwh",
    "merchant_tail_start_year",
    "analysis_years",
    "discount_rate",
}

REQUIRED_CAPITAL_KEYS = {
    "debt_pct",
    "tax_equity_pct",
    "sponsor_equity_pct",
    "debt_rate",
    "debt_tenor_years",
}

FIELD_TYPES = {
    "project_name": str,
    "project_size_mw": float,
    "capex_per_watt": float,
    "capacity_factor": float,
    "ppa_price_per_mwh": float,
    "opex_per_kw_year": float,
    "annual_degradation_pct": float,
    "merchant_tail_price_per_mwh": float,
    "merchant_tail_start_year": int,
    "analysis_years": int,
    "discount_rate": float,
    "debt_pct": float,
    "tax_equity_pct": float,
    "sponsor_equity_pct": float,
    "debt_rate": float,
    "debt_tenor_years": int,
}


def parse_structured_message(message: str) -> Dict[str, Any]:
    """Parse newline-delimited key=value pairs from SMS/email body."""
    data: Dict[str, Any] = {}
    for raw_line in message.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        parser = FIELD_TYPES.get(key, str)
        data[key] = parser(value)
    return data


def split_input_payload(data: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    assumptions = {k: v for k, v in data.items() if k in REQUIRED_ASSUMPTION_KEYS}
    capital_stack = {k: v for k, v in data.items() if k in REQUIRED_CAPITAL_KEYS}
    return assumptions, capital_stack


def find_missing_fields(data: Dict[str, Any]) -> Dict[str, list[str]]:
    assumptions, capital_stack = split_input_payload(data)
    missing_assumptions = sorted(REQUIRED_ASSUMPTION_KEYS - set(assumptions.keys()))
    missing_capital = sorted(REQUIRED_CAPITAL_KEYS - set(capital_stack.keys()))
    return {"assumptions": missing_assumptions, "capital_stack": missing_capital}


def run_agent_from_data(
    data: Dict[str, Any],
    service_account_json_path: str,
    sheet_title: str,
) -> Dict[str, Any]:
    missing = find_missing_fields(data)
    if missing["assumptions"] or missing["capital_stack"]:
        return {
            "status": "needs_input",
            "missing": missing,
        }

    assumptions_raw, capital_raw = split_input_payload(data)
    assumptions = ProjectAssumptions(**assumptions_raw)
    capital_stack = CapitalStack(**capital_raw)

    result = build_financial_model(assumptions, capital_stack)
    sheet_url = export_to_google_sheets(
        model=result,
        service_account_json_path=service_account_json_path,
        spreadsheet_title=sheet_title,
    )

    return {
        "status": "ok",
        "sheet_url": sheet_url,
        "project_irr": result.project_irr,
        "project_npv": result.project_npv,
        "assumptions": asdict(assumptions),
        "capital_stack": asdict(capital_stack),
    }
