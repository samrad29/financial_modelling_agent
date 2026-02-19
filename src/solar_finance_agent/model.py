from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class CapitalStack:
    debt_pct: float
    tax_equity_pct: float
    sponsor_equity_pct: float
    debt_rate: float
    debt_tenor_years: int


@dataclass
class ProjectAssumptions:
    project_name: str
    project_size_mw: float
    capex_per_watt: float
    capacity_factor: float
    ppa_price_per_mwh: float
    opex_per_kw_year: float
    annual_degradation_pct: float
    merchant_tail_price_per_mwh: float
    merchant_tail_start_year: int
    analysis_years: int
    discount_rate: float


@dataclass
class YearlyCashFlow:
    year: int
    generation_mwh: float
    revenue: float
    opex: float
    debt_service: float
    levered_cash_flow: float


@dataclass
class FinancialModelResult:
    assumptions: ProjectAssumptions
    capital_stack: CapitalStack
    total_capex: float
    debt_amount: float
    tax_equity_amount: float
    sponsor_equity_amount: float
    yearly_cashflows: List[YearlyCashFlow]
    project_irr: float
    project_npv: float
    sensitivity: Dict[str, Dict[str, float]]


def validate_capital_stack(capital_stack: CapitalStack) -> None:
    total = (
        capital_stack.debt_pct
        + capital_stack.tax_equity_pct
        + capital_stack.sponsor_equity_pct
    )
    if abs(total - 1.0) > 1e-6:
        raise ValueError(
            f"Capital stack percentages must sum to 1.0, found {total:.4f}."
        )


def total_capex(assumptions: ProjectAssumptions) -> float:
    return assumptions.project_size_mw * 1_000_000 * assumptions.capex_per_watt


def annual_generation_mwh(assumptions: ProjectAssumptions, year: int) -> float:
    base = assumptions.project_size_mw * 8_760 * assumptions.capacity_factor
    return base * ((1 - assumptions.annual_degradation_pct) ** (year - 1))


def revenue_for_year(assumptions: ProjectAssumptions, generation_mwh: float, year: int) -> float:
    if year < assumptions.merchant_tail_start_year:
        price = assumptions.ppa_price_per_mwh
    else:
        price = assumptions.merchant_tail_price_per_mwh
    return generation_mwh * price


def levelized_annual_debt_service(principal: float, rate: float, tenor_years: int) -> float:
    if principal <= 0 or tenor_years <= 0:
        return 0.0
    if rate == 0:
        return principal / tenor_years
    growth = (1 + rate) ** tenor_years
    return principal * (rate * growth) / (growth - 1)


def npv(discount_rate: float, cashflows: List[float]) -> float:
    return sum(cf / ((1 + discount_rate) ** year) for year, cf in enumerate(cashflows))


def irr(cashflows: List[float], low: float = -0.95, high: float = 1.5, tol: float = 1e-6) -> float:
    def f(rate: float) -> float:
        return npv(rate, cashflows)

    f_low = f(low)
    f_high = f(high)
    if f_low * f_high > 0:
        raise ValueError("IRR root is not bracketed; adjust bounds or cash flow profile.")

    for _ in range(200):
        mid = (low + high) / 2
        f_mid = f(mid)
        if abs(f_mid) < tol:
            return mid
        if f_low * f_mid < 0:
            high = mid
            f_high = f_mid
        else:
            low = mid
            f_low = f_mid
    return (low + high) / 2


def build_financial_model(
    assumptions: ProjectAssumptions,
    capital_stack: CapitalStack,
) -> FinancialModelResult:
    validate_capital_stack(capital_stack)
    capex = total_capex(assumptions)

    debt_amount = capex * capital_stack.debt_pct
    tax_equity_amount = capex * capital_stack.tax_equity_pct
    sponsor_equity_amount = capex * capital_stack.sponsor_equity_pct

    debt_service = levelized_annual_debt_service(
        debt_amount,
        capital_stack.debt_rate,
        capital_stack.debt_tenor_years,
    )

    yearly_rows: List[YearlyCashFlow] = []
    levered_cashflows: List[float] = [-sponsor_equity_amount]

    for year in range(1, assumptions.analysis_years + 1):
        generation = annual_generation_mwh(assumptions, year)
        revenue = revenue_for_year(assumptions, generation, year)
        opex = assumptions.opex_per_kw_year * assumptions.project_size_mw * 1000
        annual_debt = debt_service if year <= capital_stack.debt_tenor_years else 0.0
        levered = revenue - opex - annual_debt
        yearly_rows.append(
            YearlyCashFlow(
                year=year,
                generation_mwh=generation,
                revenue=revenue,
                opex=opex,
                debt_service=annual_debt,
                levered_cash_flow=levered,
            )
        )
        levered_cashflows.append(levered)

    model_irr = irr(levered_cashflows)
    model_npv = npv(assumptions.discount_rate, levered_cashflows)

    sensitivity = {
        "ppa_price": {
            "-10%": _compute_irr_shift(assumptions, capital_stack, price_mult=0.9),
            "base": model_irr,
            "+10%": _compute_irr_shift(assumptions, capital_stack, price_mult=1.1),
        },
        "capex": {
            "-10%": _compute_irr_shift(assumptions, capital_stack, capex_mult=0.9),
            "base": model_irr,
            "+10%": _compute_irr_shift(assumptions, capital_stack, capex_mult=1.1),
        },
    }

    return FinancialModelResult(
        assumptions=assumptions,
        capital_stack=capital_stack,
        total_capex=capex,
        debt_amount=debt_amount,
        tax_equity_amount=tax_equity_amount,
        sponsor_equity_amount=sponsor_equity_amount,
        yearly_cashflows=yearly_rows,
        project_irr=model_irr,
        project_npv=model_npv,
        sensitivity=sensitivity,
    )


def _compute_irr_shift(
    assumptions: ProjectAssumptions,
    capital_stack: CapitalStack,
    price_mult: float = 1.0,
    capex_mult: float = 1.0,
) -> float:
    shifted_assumptions = ProjectAssumptions(
        **{**assumptions.__dict__, "ppa_price_per_mwh": assumptions.ppa_price_per_mwh * price_mult}
    )
    shifted_capex = total_capex(shifted_assumptions) * capex_mult

    debt_amount = shifted_capex * capital_stack.debt_pct
    sponsor_equity_amount = shifted_capex * capital_stack.sponsor_equity_pct
    debt_service = levelized_annual_debt_service(
        debt_amount,
        capital_stack.debt_rate,
        capital_stack.debt_tenor_years,
    )

    cashflows = [-sponsor_equity_amount]
    for year in range(1, shifted_assumptions.analysis_years + 1):
        generation = annual_generation_mwh(shifted_assumptions, year)
        revenue = revenue_for_year(shifted_assumptions, generation, year)
        opex = shifted_assumptions.opex_per_kw_year * shifted_assumptions.project_size_mw * 1000
        annual_debt = debt_service if year <= capital_stack.debt_tenor_years else 0.0
        cashflows.append(revenue - opex - annual_debt)
    return irr(cashflows)
