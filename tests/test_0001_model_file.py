import json
import os
import stat
from collections.abc import Iterator
from pathlib import Path

import pytest
from helpers import fail, succeed
from mcp import Client

from whatif_mcp.core.model import Model
from whatif_mcp.store import save_model


@pytest.mark.anyio
@pytest.mark.integration
async def test_AC29_unknown_key_does_not_match_the_shape(
    client: Client, model_w_file: Path
) -> None:
    document = json.loads(model_w_file.read_text())
    document["comment"] = "note"
    model_w_file.write_text(json.dumps(document))
    original_bytes = model_w_file.read_bytes()

    message = await fail(client, "show_model", {})

    assert str(model_w_file) in message
    assert '"comment"' in message
    assert model_w_file.read_bytes() == original_bytes


@pytest.mark.anyio
@pytest.mark.integration
async def test_AC29_repeated_key_does_not_match_the_shape(
    client: Client, model_w_file: Path
) -> None:
    checking_balance = '"balance": 5000.0,'
    text = model_w_file.read_text()
    assert text.count(checking_balance) == 1
    model_w_file.write_text(text.replace(checking_balance, '"balance": 5000.0, "balance": 1.0,'))
    original_bytes = model_w_file.read_bytes()

    message = await fail(client, "show_model", {})

    assert str(model_w_file) in message
    assert '"balance"' in message
    assert model_w_file.read_bytes() == original_bytes


@pytest.mark.anyio
@pytest.mark.integration
async def test_AC30_write_through_a_symlink_replaces_the_target(
    client: Client, model_w: Model, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "synced" / "model.json"
    link = tmp_path / "link" / "model.json"
    save_model(target, model_w)
    link.parent.mkdir()
    link.symlink_to(target)
    monkeypatch.setenv("WHATIF_MODEL_PATH", str(link))

    await succeed(client, "set_inflation_rate", {"rate": 0.02})

    assert link.is_symlink()
    assert link.readlink() == target
    assert json.loads(target.read_text())["inflation_rate"] == 0.02


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home_path = tmp_path / "home"
    home_path.mkdir()
    monkeypatch.setenv("HOME", str(home_path))
    return home_path


@pytest.mark.anyio
@pytest.mark.integration
async def test_AC31_leading_tilde_expands_to_home(
    client: Client, home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("WHATIF_MODEL_PATH", "~/fin/model.json")

    shown = await succeed(client, "show_model", {})

    assert shown["model_path"] == f"{home}/fin/model.json"


@pytest.mark.anyio
@pytest.mark.integration
async def test_AC31_empty_value_counts_as_unset(
    client: Client, home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("WHATIF_MODEL_PATH", "")

    shown = await succeed(client, "show_model", {})

    assert shown["model_path"] == f"{home}/.whatif/model.json"


@pytest.mark.anyio
@pytest.mark.integration
async def test_AC31_relative_path_is_refused_naming_the_variable(
    client: Client, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    working_directory = tmp_path / "cwd"
    working_directory.mkdir()
    monkeypatch.chdir(working_directory)
    monkeypatch.setenv("WHATIF_MODEL_PATH", "model.json")

    message = await fail(client, "show_model", {})

    assert "WHATIF_MODEL_PATH" in message
    assert list(working_directory.iterdir()) == []


@pytest.fixture
def umask_022() -> Iterator[None]:
    previous_umask = os.umask(0o022)
    yield
    os.umask(previous_umask)


@pytest.mark.anyio
@pytest.mark.integration
@pytest.mark.usefixtures("umask_022")
async def test_AC31_created_directories_are_owner_only(
    client: Client, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "a" / "b" / "model.json"
    monkeypatch.setenv("WHATIF_MODEL_PATH", str(path))

    await succeed(client, "set_account", {"name": "Checking", "kind": "asset", "balance": 1})

    assert stat.S_IMODE((tmp_path / "a").stat().st_mode) == 0o700
    assert stat.S_IMODE((tmp_path / "a" / "b").stat().st_mode) == 0o700
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


@pytest.mark.anyio
@pytest.mark.integration
async def test_R1_tilde_with_a_user_name_is_refused_as_relative(
    client: Client, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    working_directory = tmp_path / "cwd"
    working_directory.mkdir()
    monkeypatch.chdir(working_directory)
    monkeypatch.setenv("WHATIF_MODEL_PATH", "~nobody/model.json")

    message = await fail(client, "show_model", {})

    assert "WHATIF_MODEL_PATH" in message
    assert list(working_directory.iterdir()) == []
