"""Forge error hierarchy.

Replaces scattered sys.exit(1) calls with structured exceptions.
Each module's main() catches ForgeError and exits cleanly.
Internal code raises specific subclasses instead of printing + exiting.
"""


class ForgeError(Exception):
    """Base for all Forge errors. Contains user-facing message."""

    def __init__(self, message: str, exit_code: int = 1):
        super().__init__(message)
        self.exit_code = exit_code


class EntityNotFound(ForgeError):
    """Entity (task, decision, guideline, etc.) not found by ID."""
    pass


class ValidationError(ForgeError):
    """Contract validation or input parsing failure."""
    pass


class GateFailure(ForgeError):
    """A required gate (test, lint, etc.) failed."""
    pass


class PreconditionError(ForgeError):
    """Precondition not met (wrong task state, missing reasoning, etc.)."""
    pass


class StorageError(ForgeError):
    """Storage read/write failure."""
    pass


class ConflictError(ForgeError):
    """Conflicting state (task claimed by another agent, etc.)."""
    pass
