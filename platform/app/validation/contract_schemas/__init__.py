"""ContractSchema registry — Phase E Stage E.1.

Concrete contracts per (task_type, ceremony_level) combination.
Importing this package registers all schemas in CONTRACT_REGISTRY
(in app.validation.contract_schema). Idempotent: multiple imports
register once via the duplicate-guard in register().

Schemas seeded to match the 4 existing output_contracts rows
(per IMPLEMENTATION_TRACKER.md): default, feature/STANDARD,
feature/FULL, bug/LIGHT.
"""

from app.validation.contract_schema import register
from app.validation.contract_schemas.default import DEFAULT_CONTRACT
from app.validation.contract_schemas.feature_standard import FEATURE_STANDARD_CONTRACT
from app.validation.contract_schemas.feature_full import FEATURE_FULL_CONTRACT
from app.validation.contract_schemas.bug_light import BUG_LIGHT_CONTRACT

# Idempotent registration guarded by CONTRACT_REGISTRY duplicate check.
# If imported twice in the same process, register() raises and we catch.
for _schema in (
    DEFAULT_CONTRACT,
    FEATURE_STANDARD_CONTRACT,
    FEATURE_FULL_CONTRACT,
    BUG_LIGHT_CONTRACT,
):
    try:
        register(_schema)
    except ValueError:
        # Already registered (re-import). Silent — registration is the
        # idempotent intent.
        pass

__all__ = [
    "DEFAULT_CONTRACT",
    "FEATURE_STANDARD_CONTRACT",
    "FEATURE_FULL_CONTRACT",
    "BUG_LIGHT_CONTRACT",
]
