from solar_finance_agent.model import CapitalStack, ProjectAssumptions, build_financial_model


def test_model_outputs_valid_ranges() -> None:
    assumptions = ProjectAssumptions(
        project_name="Demo",
        project_size_mw=100,
        capex_per_watt=1.1,
        capacity_factor=0.28,
        ppa_price_per_mwh=60,
        opex_per_kw_year=18,
        annual_degradation_pct=0.005,
        merchant_tail_price_per_mwh=45,
        merchant_tail_start_year=16,
        analysis_years=20,
        discount_rate=0.08,
    )
    stack = CapitalStack(
        debt_pct=0.6,
        tax_equity_pct=0.2,
        sponsor_equity_pct=0.2,
        debt_rate=0.06,
        debt_tenor_years=15,
    )

    result = build_financial_model(assumptions, stack)

    assert len(result.yearly_cashflows) == 20
    assert result.project_npv > -1e9
    assert -0.95 < result.project_irr < 1.5
    assert set(result.sensitivity.keys()) == {"ppa_price", "capex"}
