from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, List

from solar_finance_agent.model import FinancialModelResult

if TYPE_CHECKING:
    import gspread

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def load_google_client(service_account_json_path: str) -> "gspread.Client":
    import gspread
    from google.oauth2.service_account import Credentials

    credentials_info = json.loads(Path(service_account_json_path).read_text())
    creds = Credentials.from_service_account_info(credentials_info, scopes=SCOPES)
    return gspread.authorize(creds)


def export_to_google_sheets(
    model: FinancialModelResult,
    service_account_json_path: str,
    spreadsheet_title: str,
) -> str:
    client = load_google_client(service_account_json_path)
    sheet = client.create(spreadsheet_title)

    assumptions_tab = sheet.sheet1
    assumptions_tab.update_title("Assumptions")
    assumptions_rows = _assumption_rows(model)
    assumptions_tab.update(range_name="A1", values=assumptions_rows)

    cashflow_tab = sheet.add_worksheet(title="Cash Flow", rows=200, cols=10)
    cashflow_tab.update(range_name="A1", values=_cashflow_rows(model))

    returns_tab = sheet.add_worksheet(title="IRR_NPV", rows=100, cols=10)
    returns_tab.update(range_name="A1", values=_returns_rows(model))

    return f"https://docs.google.com/spreadsheets/d/{sheet.id}"


def _assumption_rows(model: FinancialModelResult) -> List[List[Any]]:
    a = model.assumptions
    c = model.capital_stack
    return [
        ["Assumption", "Value", "Notes"],
        ["Project Name", a.project_name, ""],
        ["Project Size (MW)", a.project_size_mw, "Core production lever"],
        ["CAPEX ($/W)", a.capex_per_watt, "Affects upfront investment"],
        ["Capacity Factor", a.capacity_factor, "Drives annual generation"],
        ["PPA Price ($/MWh)", a.ppa_price_per_mwh, "Primary contracted revenue lever"],
        ["OPEX ($/kW-year)", a.opex_per_kw_year, "Operating expense lever"],
        ["Annual Degradation", a.annual_degradation_pct, "Generation declines over time"],
        ["Merchant Tail Start Year", a.merchant_tail_start_year, "Switch from PPA to merchant pricing"],
        ["Merchant Tail Price ($/MWh)", a.merchant_tail_price_per_mwh, "Uncontracted revenue assumption"],
        ["Analysis Period (years)", a.analysis_years, ""],
        ["Discount Rate", a.discount_rate, "Used in NPV"],
        ["Debt %", c.debt_pct, "Capital stack lever"],
        ["Tax Equity %", c.tax_equity_pct, "Capital stack lever"],
        ["Sponsor Equity %", c.sponsor_equity_pct, "Capital stack lever"],
        ["Debt Rate", c.debt_rate, ""],
        ["Debt Tenor", c.debt_tenor_years, ""],
    ]


def _cashflow_rows(model: FinancialModelResult) -> List[List[Any]]:
    rows = [["Year", "Generation MWh", "Revenue", "OPEX", "Debt Service", "Levered Cash Flow"]]
    for y in model.yearly_cashflows:
        rows.append([y.year, y.generation_mwh, y.revenue, y.opex, y.debt_service, y.levered_cash_flow])
    return rows


def _returns_rows(model: FinancialModelResult) -> List[List[Any]]:
    rows: List[List[Any]] = [
        ["Metric", "Value"],
        ["Project IRR", model.project_irr],
        ["Project NPV", model.project_npv],
        [],
        ["Sensitivity", "Downside", "Base", "Upside"],
    ]
    for key, vals in model.sensitivity.items():
        rows.append([key, vals["-10%"], vals["base"], vals["+10%"]])
    return rows
