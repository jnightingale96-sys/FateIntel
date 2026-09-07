from app.services.selection import arrhenius_dt50, geometric_mean, calculate_selection

class E:
    def __init__(self, id, v, t, group, rel=2):
        self.id=id
        self.property_code="FATE.SOIL_DT50"
        self.original_value=v
        self.original_unit="days"
        self.include_by_default=True
        self.reliability_score=rel
        self.temperature_c=t
        self.representative_group_key=group

def test_arrhenius_direction():
    assert arrhenius_dt50(12, 10, 20, 65.4) < 12
    assert arrhenius_dt50(80, 25, 20, 65.4) > 80

def test_geometric_mean():
    assert round(geometric_mean([4, 16]), 6) == 8

def test_grouping_avoids_double_weighting():
    evidence = [
        E(1, 10, 20, "soil-A"),
        E(2, 40, 20, "soil-A"),
        E(3, 80, 20, "soil-B"),
    ]
    r = calculate_selection(evidence, 20, 65.4, 2)
    assert r["statistics"]["n_evidence_records"] == 3
    assert r["statistics"]["n_independent_groups"] == 2
    # group A representative = GM(10,40)=20; overall GM(20,80)=40
    assert round(r["selected_value_days"], 6) == 40
