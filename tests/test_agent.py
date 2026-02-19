from solar_finance_agent.agent import find_missing_fields, parse_structured_message


def test_parse_structured_message_converts_known_types() -> None:
    body = """
project_name=Demo
project_size_mw=100
analysis_years=20
debt_tenor_years=15
# comment
"""
    parsed = parse_structured_message(body)

    assert parsed["project_name"] == "Demo"
    assert parsed["project_size_mw"] == 100.0
    assert parsed["analysis_years"] == 20
    assert parsed["debt_tenor_years"] == 15


def test_missing_fields_detected() -> None:
    parsed = parse_structured_message("project_name=Only Name")
    missing = find_missing_fields(parsed)

    assert "project_size_mw" in missing["assumptions"]
    assert "debt_pct" in missing["capital_stack"]
