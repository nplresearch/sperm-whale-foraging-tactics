"""M0 has no recomputation: it audits inputs. Run its tests instead:
    pytest review_r1/m0_data_audit
Steward re-export (needs raw tag files, see scripts/export_steward_kinematics.py --help).
"""
import subprocess
import sys
from pathlib import Path

raise SystemExit(subprocess.run([sys.executable, "-m", "pytest", "-q", str(Path(__file__).parent)]).returncode)
