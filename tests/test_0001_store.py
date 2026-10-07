import os
from dataclasses import replace
from pathlib import Path

import pytest

from whatif_mcp.core.model import Model
from whatif_mcp.store import save_model


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
