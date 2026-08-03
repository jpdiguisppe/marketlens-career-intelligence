from __future__ import annotations

import json
from pathlib import Path

from app.occupation_catalog import registry_summary


def test_universal_occupation_acceptance_contract_matches_registry() -> None:
    contract_path = Path(__file__).resolve().parents[1] / "evaluation" / "universal_occupation_acceptance.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    summary = registry_summary()

    assert summary["major_groups"] >= contract["required_major_groups"]
    assert summary["occupations"] >= contract["required_occupation_concepts"]
    assert summary["accepted_titles"] >= contract["required_accepted_titles"]
    assert summary["ambiguous_acronyms"] >= contract["required_ambiguous_acronyms"]
    assert len(contract["friend_acceptance_spheres"]) >= 12
    assert len(contract["sae_required_variants"]) == 4
    assert contract["sae_rejected_neighbors"] == ["Sales Engineer", "Systems Administrator"]
