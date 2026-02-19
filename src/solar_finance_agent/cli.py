from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Callable, Optional

from solar_finance_agent.model import CapitalStack, ProjectAssumptions, build_financial_model
from solar_finance_agent.sheet_export import export_to_google_sheets


@dataclass
class PromptField:
    key: str
    question: str
    parser: Callable[[str], object]
    default: Optional[object] = None


def _float(value: str) -> float:
    return float(value.strip())


def _int(value: str) -> int:
    return int(value.strip())


def collect_inputs() -> tuple[ProjectAssumptions, CapitalStack]:
    print("\nSolar Finance Agent — let's gather project details for the model.\n")

    assumption_fields = [
        PromptField("project_name", "Project name", str, "Solar Project"),
        PromptField("project_size_mw", "Project size (MW)", _float),
        PromptField("capex_per_watt", "CAPEX ($/W)", _float),
        PromptField("capacity_factor", "Capacity factor (0-1)", _float),
        PromptField("ppa_price_per_mwh", "PPA price ($/MWh)", _float),
        PromptField("opex_per_kw_year", "OPEX ($/kW-year)", _float),
        PromptField("annual_degradation_pct", "Annual degradation (0-1)", _float, 0.005),
        PromptField("merchant_tail_start_year", "Merchant tail start year", _int, 16),
        PromptField("merchant_tail_price_per_mwh", "Merchant tail price ($/MWh)", _float, 40.0),
        PromptField("analysis_years", "Analysis period (15-25 years recommended)", _int, 20),
        PromptField("discount_rate", "Discount rate (0-1)", _float, 0.08),
    ]

    capital_fields = [
        PromptField("debt_pct", "Debt % of capital stack (0-1)", _float, 0.6),
        PromptField("tax_equity_pct", "Tax equity % of capital stack (0-1)", _float, 0.2),
        PromptField("sponsor_equity_pct", "Sponsor equity % of capital stack (0-1)", _float, 0.2),
        PromptField("debt_rate", "Debt interest rate (0-1)", _float, 0.06),
        PromptField("debt_tenor_years", "Debt tenor (years)", _int, 15),
    ]

    assumptions_data = _collect_group("Project Assumptions", assumption_fields)
    capital_data = _collect_group("Capital Stack", capital_fields)

    assumptions = ProjectAssumptions(**assumptions_data)
    capital_stack = CapitalStack(**capital_data)
    _review_gaps(assumptions, capital_stack)

    return assumptions, capital_stack


def _collect_group(title: str, fields: list[PromptField]) -> dict[str, object]:
    print(f"\n{title}")
    print("-" * len(title))
    values: dict[str, object] = {}

    for field in fields:
        suffix = f" [{field.default}]" if field.default is not None else ""
        raw = input(f"{field.question}{suffix}: ").strip()
        if not raw and field.default is not None:
            parsed = field.default
        else:
            parsed = field.parser(raw)
        values[field.key] = parsed
    return values


def _review_gaps(assumptions: ProjectAssumptions, capital_stack: CapitalStack) -> None:
    print("\nReviewing inputs for likely gaps/flags...")
    flags: list[str] = []
    if assumptions.capacity_factor <= 0 or assumptions.capacity_factor > 1:
        flags.append("Capacity factor should be between 0 and 1.")
    if assumptions.analysis_years < 15 or assumptions.analysis_years > 25:
        flags.append("Analysis period is outside typical 15-25 years range.")
    stack_total = (
        capital_stack.debt_pct + capital_stack.tax_equity_pct + capital_stack.sponsor_equity_pct
    )
    if abs(stack_total - 1.0) > 1e-6:
        flags.append("Capital stack percentages should sum to 1.0.")

    if flags:
        print("Potential issues identified:")
        for flag in flags:
            print(f" - {flag}")
    else:
        print("No obvious gaps found. Proceeding with model build.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Solar financial modeling CLI agent")
    parser.add_argument(
        "--service-account-json",
        required=True,
        help="Path to Google service account JSON credential file.",
    )
    parser.add_argument(
        "--sheet-title",
        default="Solar Financial Model",
        help="Title for the output Google Sheet workbook.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    assumptions, capital_stack = collect_inputs()
    result = build_financial_model(assumptions, capital_stack)

    sheet_url = export_to_google_sheets(
        model=result,
        service_account_json_path=args.service_account_json,
        spreadsheet_title=args.sheet_title,
    )

    print("\nModel build complete.")
    print(f"Google Sheet created: {sheet_url}")


if __name__ == "__main__":
    main()
