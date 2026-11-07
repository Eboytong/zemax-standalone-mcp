from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).parents[2]/"tests"/"support"/"development_status.py"),run_name="__main__")
