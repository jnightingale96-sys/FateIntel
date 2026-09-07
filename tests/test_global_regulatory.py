from app.services.global_regulatory import (
    frameworks,
    change_watch,
    endpoint_checklist,
    recommend_regulatory_pathway,
    research_status,
)


def test_all_compendium_frameworks_ingested():
    rows = frameworks()
    assert len(rows) == 139
    assert sum(1 for row in rows if row["verification_tier"] == "A") == 97
    assert all(row["official_url"] for row in rows)


def test_change_watch_and_endpoint_checklist_ingested():
    assert len(change_watch()) == 9
    assert len(endpoint_checklist()) == 8


def test_eu_us_pharmaceutical_wastewater_pathway():
    result = recommend_regulatory_pathway({
        "jurisdictions": ["EU", "US"],
        "product_class": "human_pharmaceutical",
        "scenario": "wastewater_irrigation",
        "tier": 2,
        "include_international": True,
    })
    ids = {row["id"] for row in result["selected_frameworks"]}
    assert "INT-002" in ids
    assert "INT-004" in ids
    assert "EUR-013" in ids
    assert "NAM-009" in ids
    assert "XCT-001" in ids
    assert result["verification_summary"]["A"] > 0


def test_global_research_status_is_honest_about_review_depth():
    result = research_status()
    assert result["framework_entries"] == 139
    assert "separate statuses" in result["implementation_rule"].lower()
