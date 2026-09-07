from app.services.sds import parse_sds_text, build_coshh_draft

SDS = """
SECTION 1: Identification
Test Substance
SECTION 2: Hazard identification
Danger H314 H335 P280 P305+P351+P338
SECTION 4: First aid measures
Eye contact: rinse cautiously with water. Inhalation: move to fresh air.
SECTION 6: Accidental release measures
Contain spill and collect with inert absorbent.
SECTION 7: Handling and storage
Store locked up. Avoid incompatible acids.
SECTION 8: Exposure controls/personal protection
Wear protective gloves and eye protection. Workplace exposure limit 5 mg/m3.
SECTION 13: Disposal considerations
Dispose of waste through an approved hazardous waste contractor.
"""


def test_sds_parser_and_coshh_draft():
    parsed = parse_sds_text(SDS)
    assert "H314" in parsed["hazard_statement_codes"]
    assert parsed["signal_word"] == "Danger"
    draft = build_coshh_draft(parsed, {
        "substance_name": "Test Substance",
        "task_description": "Open transfer and dilution",
        "quantity": "100 mL",
        "frequency": "weekly",
        "persons_at_risk": "researchers",
        "open_handling": True,
        "heating_or_aerosol": False,
    })
    assert draft["status"] == "draft_for_competent_person_review"
    assert draft["recommended_controls"]
