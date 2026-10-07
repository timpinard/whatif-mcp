from pathlib import Path

from whatif_mcp.core.model import Model
from whatif_mcp.store import ModelFileError, save_model


def write_model_file(path: Path, model: Model) -> None:
    try:
        save_model(path, model)
    except OSError as error:
        raise ModelFileError(
            f"Could not write the model file {path}: {error}. The file was not changed; "
            "check that its directory is writable and try again."
        ) from error
