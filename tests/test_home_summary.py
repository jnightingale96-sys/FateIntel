from app.services.home_summary import build_home_use_summary


def test_home_summary_annualises_and_flags():
    result = build_home_use_summary({
        "product_identifier": "123",
        "product_name": "Test cleaner",
        "chemical_name": "Test chemical",
        "amount_value": 10,
        "amount_unit": "mL",
        "frequency_value": 1,
        "frequency_unit": "week",
        "release_route": "down_drain",
        "log_kow": 4.2,
        "koc_l_kg": 900,
        "soil_dt50_days": 150,
    })
    assert result["annual_use"]["value"] == 520
    assert result["confidence"] == "higher"
    assert any(x["level"] == "high" for x in result["fate_flags"])
