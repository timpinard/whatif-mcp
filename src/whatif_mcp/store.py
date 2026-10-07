import json
import math
import os
import tempfile
from collections.abc import Callable, Mapping
from datetime import date
from pathlib import Path
from typing import Any

from whatif_mcp.core.errors import WhatIfError
from whatif_mcp.core.model import Account, AccountKind, Flow, Frequency, Model

MODEL_PATH_VARIABLE = "WHATIF_MODEL_PATH"
DEFAULT_MODEL_PATH = Path(".whatif") / "model.json"
FILE_VERSION = 1
FILE_MODE = 0o600
TEMP_SUFFIX = ".tmp"


class ModelFileError(WhatIfError):
    pass


def resolve_model_path() -> Path:
    configured = os.environ.get(MODEL_PATH_VARIABLE)
    if configured:
        return Path(configured)
    return Path.home() / DEFAULT_MODEL_PATH


def load_model(path: Path) -> Model:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return Model()
    try:
        document = json.loads(text)
    except json.JSONDecodeError as error:
        raise ModelFileError(f"The model file {path} is not valid JSON: {error}.") from error
    if not isinstance(document, dict):
        raise _shape_error(path, "the top level is not an object")
    _check_version(path, document)
    try:
        model = _model_from_document(document)
        _check_names(model)
    except _ShapeProblem as problem:
        raise _shape_error(path, str(problem)) from problem
    return model


def save_model(path: Path, model: Model) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(_document_from_model(model), indent=2) + "\n"
    descriptor, temp_name = tempfile.mkstemp(dir=path.parent, suffix=TEMP_SUFFIX)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as temp_file:
            temp_file.write(content)
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.chmod(temp_name, FILE_MODE)
        os.replace(temp_name, path)
    except BaseException:
        Path(temp_name).unlink(missing_ok=True)
        raise


class _ShapeProblem(Exception):
    pass


def _shape_error(path: Path, problem: str) -> ModelFileError:
    return ModelFileError(
        f"The model file {path} does not match the version {FILE_VERSION} shape: {problem}."
    )


def _check_version(path: Path, document: Mapping[str, Any]) -> None:
    if "version" not in document:
        raise ModelFileError(
            f"The model file {path} has no version; this server reads version {FILE_VERSION}."
        )
    version = document["version"]
    if type(version) is not int or version != FILE_VERSION:
        raise ModelFileError(
            f"The model file {path} has version {json.dumps(version)}; this server reads "
            f"version {FILE_VERSION} only."
        )


def _check_names(model: Model) -> None:
    _check_unique("account", [account.name for account in model.accounts])
    _check_unique("flow", [flow.name for flow in model.flows])
    account_names = {account.name for account in model.accounts}
    for flow in model.flows:
        for key, account_name in (
            ("from", flow.from_account),
            ("to", flow.to_account),
            ("rate_of", flow.rate_of),
        ):
            if account_name is not None and account_name not in account_names:
                raise _ShapeProblem(
                    f'flow "{flow.name}" has "{key}" "{account_name}", which is not an account'
                )


def _check_unique(entity: str, names: list[str]) -> None:
    seen: set[str] = set()
    for name in names:
        matching_key = name.strip().casefold()
        if matching_key in seen:
            raise _ShapeProblem(f'{entity} name "{name}" is used more than once')
        seen.add(matching_key)


def _document_from_model(model: Model) -> dict[str, Any]:
    return {
        "version": FILE_VERSION,
        "inflation_rate": model.inflation_rate,
        "accounts": [_document_from_account(account) for account in model.accounts],
        "flows": [_document_from_flow(flow) for flow in model.flows],
    }


def _document_from_account(account: Account) -> dict[str, Any]:
    return {
        "name": account.name,
        "kind": account.kind.value,
        "balance": float(account.balance),
        "balance_as_of": account.balance_as_of.isoformat(),
        "growth_rate": float(account.growth_rate),
        "volatility": float(account.volatility),
    }


def _document_from_flow(flow: Flow) -> dict[str, Any]:
    return {
        "name": flow.name,
        "from": flow.from_account,
        "to": flow.to_account,
        "amount": None if flow.amount is None else float(flow.amount),
        "rate": flow.rate,
        "rate_of": flow.rate_of,
        "frequency": flow.frequency.value,
        "start_date": flow.start_date.isoformat(),
        "end_date": None if flow.end_date is None else flow.end_date.isoformat(),
    }


def _model_from_document(document: Mapping[str, Any]) -> Model:
    return Model(
        accounts=tuple(
            _account_from_document(_object(entry, "accounts"))
            for entry in _list(document, "accounts")
        ),
        flows=tuple(
            _flow_from_document(_object(entry, "flows")) for entry in _list(document, "flows")
        ),
        inflation_rate=_number(document, "inflation_rate"),
    )


def _account_from_document(entry: Mapping[str, Any]) -> Account:
    return Account(
        name=_text(entry, "name"),
        kind=_choice(entry, "kind", AccountKind),
        balance=_number(entry, "balance"),
        balance_as_of=_date(entry, "balance_as_of"),
        growth_rate=_number(entry, "growth_rate"),
        volatility=_number(entry, "volatility"),
    )


def _flow_from_document(entry: Mapping[str, Any]) -> Flow:
    flow = Flow(
        name=_text(entry, "name"),
        from_account=_optional(entry, "from", _text),
        to_account=_optional(entry, "to", _text),
        amount=_optional(entry, "amount", _number),
        rate=_optional(entry, "rate", _number),
        rate_of=_optional(entry, "rate_of", _text),
        frequency=_choice(entry, "frequency", Frequency),
        start_date=_date(entry, "start_date"),
        end_date=_optional(entry, "end_date", _date),
    )
    if flow.amount is None and flow.rate is None:
        raise _ShapeProblem(f'flow "{flow.name}" has neither "amount" nor "rate"')
    if flow.rate is not None and flow.rate_of is None:
        raise _ShapeProblem(f'flow "{flow.name}" has "rate" but no "rate_of"')
    return flow


def _field(entry: Mapping[str, Any], key: str) -> Any:
    if key not in entry:
        raise _ShapeProblem(f'"{key}" is missing')
    return entry[key]


def _list(entry: Mapping[str, Any], key: str) -> list[Any]:
    value = _field(entry, key)
    if not isinstance(value, list):
        raise _ShapeProblem(f'"{key}" is not a list')
    return value


def _object(value: Any, container: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise _ShapeProblem(f'an entry in "{container}" is not an object')
    return value


def _number(entry: Mapping[str, Any], key: str) -> float:
    value = _field(entry, key)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise _ShapeProblem(f'"{key}" is not a number')
    try:
        number = float(value)
    except OverflowError as error:
        raise _ShapeProblem(f'"{key}" is too large to be a number') from error
    if not math.isfinite(number):
        raise _ShapeProblem(f'"{key}" is {json.dumps(number)}, not a finite number')
    return number


def _text(entry: Mapping[str, Any], key: str) -> str:
    value = _field(entry, key)
    if not isinstance(value, str):
        raise _ShapeProblem(f'"{key}" is not a string')
    return value


def _date(entry: Mapping[str, Any], key: str) -> date:
    text = _text(entry, key)
    try:
        return date.fromisoformat(text)
    except ValueError as error:
        raise _ShapeProblem(f'"{key}" is not a YYYY-MM-DD date') from error


def _choice[ChoiceT: AccountKind | Frequency](
    entry: Mapping[str, Any], key: str, choices: type[ChoiceT]
) -> ChoiceT:
    text = _text(entry, key)
    try:
        return choices(text)
    except ValueError as error:
        raise _ShapeProblem(
            f'"{key}" is not one of {", ".join(choice.value for choice in choices)}'
        ) from error


def _optional[ValueT](
    entry: Mapping[str, Any], key: str, read: Callable[[Mapping[str, Any], str], ValueT]
) -> ValueT | None:
    if _field(entry, key) is None:
        return None
    return read(entry, key)
