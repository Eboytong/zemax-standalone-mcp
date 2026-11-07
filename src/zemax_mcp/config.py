import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INSTALL = Path(r"C:\Program Files\ANSYS Inc\v242\Zemax OpticStudio")


@dataclass(frozen=True)
class Config:
    install_dir: Path
    output_dir: Path

    @classmethod
    def from_env(cls):
        return cls(
            Path(os.environ.get("ZEMAX_INSTALL_DIR", str(DEFAULT_INSTALL))).resolve(),
            Path(os.environ.get("ZEMAX_OUTPUT_DIR", str(PROJECT_ROOT / ".local" / "runs"))).resolve(),
        )

