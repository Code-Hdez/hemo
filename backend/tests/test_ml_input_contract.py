from __future__ import annotations

import pytest

from app.modules.ml.input_contract import InputContractError, validate_cbc_contract


def test_validate_cbc_contract_accepts_normal_core_values() -> None:
    normalized = validate_cbc_contract(
        {"WBC": "10.0", "RBC": 7, "HGB": 14.0, "HCT": 42, "Platelets": 250}
    )

    assert normalized["WBC"] == 10.0
    assert normalized["Platelets"] == 250.0


def test_validate_cbc_contract_normalizes_absolute_cell_counts() -> None:
    normalized = validate_cbc_contract(
        {"WBC": 8400, "RBC": 8_180_000, "HGB": 14, "Platelets": 80_000}
    )

    assert normalized["WBC"] == 8.4
    assert normalized["RBC"] == 8.18
    assert normalized["Platelets"] == 80.0


def test_validate_cbc_contract_normalizes_common_field_aliases() -> None:
    normalized = validate_cbc_contract({"WBC": 8, "RBC": 7, "HGB": 14, "PLT": 220, "NEU": 5})

    assert normalized["Platelets"] == 220.0
    assert normalized["Neutrophils"] == 5.0
    assert "PLT" not in normalized


@pytest.mark.parametrize(
    ("cbc", "error_code"),
    [
        ({"WBC": 10, "RBC": 7}, "MISSING_FIELD"),
        ({"WBC": "not-a-number", "RBC": 7, "HGB": 14}, "TYPE_ERROR"),
        ({"WBC": 999, "RBC": 7, "HGB": 14}, "RANGE_VIOLATION"),
    ],
)
def test_validate_cbc_contract_rejects_invalid_input(
    cbc: dict[str, object], error_code: str
) -> None:
    with pytest.raises(InputContractError) as caught:
        validate_cbc_contract(cbc)

    assert caught.value.error_code == error_code
