from __future__ import annotations

from pathlib import Path

from ctp.schema import load_vector
from ctp.validate import validate_directory

VECTORS = Path(__file__).resolve().parents[2] / "vectors"


def test_seed_directory_has_thirteen_unique_vectors() -> None:
    files = sorted(VECTORS.glob("*.json"))
    assert len(files) == 13
    vectors = [load_vector(path) for path in files]
    assert len({vector.id for vector in vectors}) == 13
    assert all(vector.source for vector in vectors)
    assert all(vector.env.get("jinja2") for vector in vectors)


def test_seed_vectors_match_the_reference_engine() -> None:
    report = validate_directory(VECTORS, ["reference"], None)
    assert report.exit_code == 0
    assert report.checked == 13
    assert report.matches == 13
    assert report.mismatches == 0
    assert report.errors == 0


def test_mock_vector_records_hand_computed_token_ids() -> None:
    vector = load_vector(VECTORS / "013-mock-token-ids.json")
    assert vector.expected["mock"].token_ids == (1104, 1105)


def test_issue_vectors_cite_their_source_and_stay_honest() -> None:
    vector = load_vector(VECTORS / "011-reasoning-after-last-user.json")
    assert "13404" in str(vector.source.get("issue", ""))
    assert "not a byte-level" in str(vector.source.get("note", ""))
