import json
import os
from dataclasses import replace
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from whatif_mcp.core.model import Model
from whatif_mcp.store import (
    ACCOUNT_KEYS,
    DOCUMENT_KEYS,
    FLOW_KEYS,
    ModelFileError,
    load_model,
    save_model,
)


def test_AC3_failed_write_leaves_previous_file_intact(
    model_w_file: Path, model_w: Model, monkeypatch: pytest.MonkeyPatch
) -> None:
    original_bytes = model_w_file.read_bytes()
    changed_model = replace(model_w, inflation_rate=0.05)

    def failing_replace(source: str | os.PathLike[str], target: str | os.PathLike[str]) -> None:
        raise OSError("simulated failure at the final replace")

    monkeypatch.setattr(os, "replace", failing_replace)

    with pytest.raises(OSError):
        save_model(model_w_file, changed_model)
    assert model_w_file.read_bytes() == original_bytes


def model_w_document() -> dict[str, Any]:
    return {
        "version": 1,
        "inflation_rate": 0.03,
        "accounts": [
            {
                "name": "Checking",
                "kind": "asset",
                "balance": 5000.0,
                "balance_as_of": "2026-10-06",
                "growth_rate": 0.0,
                "volatility": 0.0,
            },
            {
                "name": "Car loan",
                "kind": "liability",
                "balance": 10000.0,
                "balance_as_of": "2026-10-06",
                "growth_rate": 0.06,
                "volatility": 0.0,
            },
        ],
        "flows": [
            {
                "name": "Salary",
                "from": None,
                "to": "Checking",
                "amount": 4000.0,
                "rate": None,
                "rate_of": None,
                "frequency": "monthly",
                "start_date": "2026-11-01",
                "end_date": None,
            },
            {
                "name": "Car payment",
                "from": "Checking",
                "to": "Car loan",
                "amount": 500.0,
                "rate": None,
                "rate_of": None,
                "frequency": "monthly",
                "start_date": "2026-11-01",
                "end_date": None,
            },
        ],
    }


def write_text(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_R1_load_accepts_model_w_document(model_path: Path, today: date) -> None:
    write_text(model_path, json.dumps(model_w_document()))
    assert [account.name for account in load_model(model_path, today).accounts] == [
        "Checking",
        "Car loan",
    ]


@pytest.mark.parametrize(
    ("entry_path", "fields", "expected_problem"),
    [
        (("flows", 1), {"to": "Marina"}, '"Marina"'),
        (("flows", 1), {"from": "Marina"}, '"Marina"'),
        (("flows", 0), {"amount": None, "rate": 0.02, "rate_of": "Marina"}, '"Marina"'),
        (("accounts", 1), {"name": "CHECKING"}, '"CHECKING"'),
        (("flows", 1), {"name": "salary"}, '"salary"'),
        (("accounts", 1), {"name": " Checking "}, '" Checking "'),
    ],
)
def test_R1_load_refuses_broken_references_and_duplicate_names(
    model_path: Path,
    entry_path: tuple[str, int],
    fields: dict[str, Any],
    expected_problem: str,
    today: date,
) -> None:
    document = model_w_document()
    section, index = entry_path
    document[section][index].update(fields)
    original = write_text(model_path, json.dumps(document)).read_bytes()

    with pytest.raises(ModelFileError) as raised:
        load_model(model_path, today)

    assert str(model_path) in str(raised.value)
    assert expected_problem in str(raised.value)
    assert model_path.read_bytes() == original


@pytest.mark.parametrize(
    ("version", "expected_problem"),
    [(True, "version true"), (1.0, "version 1.0"), (None, "no version")],
)
def test_R1_load_requires_integer_version_1(
    model_path: Path, version: bool | float | None, expected_problem: str, today: date
) -> None:
    document = model_w_document()
    if version is None:
        del document["version"]
    else:
        document["version"] = version
    write_text(model_path, json.dumps(document))

    with pytest.raises(ModelFileError) as raised:
        load_model(model_path, today)

    assert str(model_path) in str(raised.value)
    assert expected_problem in str(raised.value)


@pytest.mark.parametrize("number_text", ["NaN", "Infinity", "-Infinity"])
def test_R1_load_refuses_non_finite_numbers(
    model_path: Path, number_text: str, today: date
) -> None:
    text = json.dumps(model_w_document()).replace('"balance": 5000.0', f'"balance": {number_text}')
    write_text(model_path, text)

    with pytest.raises(ModelFileError) as raised:
        load_model(model_path, today)

    assert str(model_path) in str(raised.value)
    assert number_text in str(raised.value)


def test_R1_load_refuses_integer_too_large_for_a_float(model_path: Path, today: date) -> None:
    document = model_w_document()
    document["accounts"][0]["balance"] = 10**400
    write_text(model_path, json.dumps(document))

    with pytest.raises(ModelFileError) as raised:
        load_model(model_path, today)

    assert str(model_path) in str(raised.value)
    assert '"balance"' in str(raised.value)


@pytest.mark.parametrize(
    ("flow_fields", "expected_problem"),
    [
        ({"amount": None}, "amount or rate"),
        ({"amount": None, "rate": 0.02}, "rate_of"),
    ],
)
def test_R1_load_refuses_flow_without_amount_or_complete_rate(
    model_path: Path, flow_fields: dict[str, Any], expected_problem: str, today: date
) -> None:
    document = model_w_document()
    document["flows"][0].update(flow_fields)
    write_text(model_path, json.dumps(document))

    with pytest.raises(ModelFileError) as raised:
        load_model(model_path, today)

    assert str(model_path) in str(raised.value)
    assert '"Salary"' in str(raised.value)
    assert expected_problem in str(raised.value)


@pytest.mark.parametrize(
    ("flow_fields", "expected_problem"),
    [
        ({"from": None, "to": None}, "from and to"),
        ({"from": "Car loan"}, "to"),
        ({"rate": 0.02, "rate_of": "Checking"}, "amount and rate"),
        ({"rate_of": "Checking"}, "rate"),
        ({"amount": 0.0}, "amount"),
        ({"amount": None, "rate": 0.0, "rate_of": "Checking"}, "rate"),
        ({"amount": None, "rate": 1.5, "rate_of": "Checking"}, "rate"),
        ({"end_date": "2026-10-31"}, "end_date"),
    ],
)
def test_R1_load_refuses_flow_breaking_an_R4_rule(
    model_path: Path, flow_fields: dict[str, Any], expected_problem: str, today: date
) -> None:
    document = model_w_document()
    document["flows"][1].update(flow_fields)
    original = write_text(model_path, json.dumps(document)).read_bytes()

    with pytest.raises(ModelFileError) as raised:
        load_model(model_path, today)

    assert str(model_path) in str(raised.value)
    assert f'flow "Car payment": {expected_problem}' in str(raised.value)
    assert model_path.read_bytes() == original


@pytest.mark.parametrize(
    ("account_fields", "expected_problem"),
    [
        ({"balance": -1.0}, "balance"),
        ({"growth_rate": 7.0}, "growth_rate"),
        ({"growth_rate": -1.0}, "growth_rate"),
        ({"growth_rate": 1.5}, "growth_rate"),
        ({"volatility": -0.1}, "volatility"),
        ({"volatility": 1.5}, "volatility"),
    ],
)
def test_R1_load_refuses_account_breaking_an_R2_rule(
    model_path: Path, account_fields: dict[str, Any], expected_problem: str, today: date
) -> None:
    document = model_w_document()
    document["accounts"][1].update(account_fields)
    original = write_text(model_path, json.dumps(document)).read_bytes()

    with pytest.raises(ModelFileError) as raised:
        load_model(model_path, today)

    assert str(model_path) in str(raised.value)
    assert '"Car loan"' in str(raised.value)
    assert expected_problem in str(raised.value)
    assert model_path.read_bytes() == original


@pytest.mark.parametrize("inflation_rate", [-1, -1.5, 1, 3])
def test_R1_load_refuses_inflation_rate_out_of_range(
    model_path: Path, inflation_rate: float, today: date
) -> None:
    document = model_w_document()
    document["inflation_rate"] = inflation_rate
    original = write_text(model_path, json.dumps(document)).read_bytes()

    with pytest.raises(ModelFileError) as raised:
        load_model(model_path, today)

    assert str(model_path) in str(raised.value)
    assert '"inflation_rate"' in str(raised.value)
    assert "0.03 means 3%" in str(raised.value)
    assert model_path.read_bytes() == original


def test_R1_load_accepts_inflation_rate_just_inside_the_range(
    model_path: Path, today: date
) -> None:
    document = model_w_document()
    document["inflation_rate"] = -0.99
    write_text(model_path, json.dumps(document))

    assert load_model(model_path, today).inflation_rate == -0.99


@pytest.mark.parametrize("date_text", ["20261101", "2026-W45-7", "2026-11-01T00:00"])
def test_R1_load_refuses_dates_not_in_yyyy_mm_dd_form(
    model_path: Path, date_text: str, today: date
) -> None:
    document = model_w_document()
    document["flows"][1]["start_date"] = date_text
    write_text(model_path, json.dumps(document))

    with pytest.raises(ModelFileError) as raised:
        load_model(model_path, today)

    assert str(model_path) in str(raised.value)
    assert '"start_date" is not a YYYY-MM-DD date' in str(raised.value)


def test_R1_known_keys_are_the_keys_the_writer_emits(model_w_file: Path) -> None:
    document = json.loads(model_w_file.read_text())

    assert set(document) == DOCUMENT_KEYS
    assert all(set(account) == ACCOUNT_KEYS for account in document["accounts"])
    assert all(set(flow) == FLOW_KEYS for flow in document["flows"])
