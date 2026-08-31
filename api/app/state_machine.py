"""Explicit ticket state machine.

The allowed transitions are declared as data, so the rule lives in a single
place and is trivially testable. Any transition not present in the map is
rejected with :class:`InvalidTransitionError`.
"""
from app.enums import Estado

# state -> set of states reachable from it
ALLOWED_TRANSITIONS: dict[Estado, set[Estado]] = {
    Estado.abierto: {Estado.en_progreso},
    Estado.en_progreso: {Estado.resuelto},
    # from "resuelto" a ticket can be closed or reopened
    Estado.resuelto: {Estado.cerrado, Estado.abierto},
    Estado.cerrado: set(),
}


class InvalidTransitionError(Exception):
    """Raised when a state transition is not allowed."""

    def __init__(self, current: Estado, requested: Estado) -> None:
        current = Estado(current)
        requested = Estado(requested)
        self.current = current
        self.requested = requested
        self.allowed = sorted(
            e.value for e in ALLOWED_TRANSITIONS.get(current, set())
        )
        super().__init__(
            f"Invalid transition {current.value} -> {requested.value}"
        )


def can_transition(current: Estado, requested: Estado) -> bool:
    """Return True if moving from ``current`` to ``requested`` is allowed.

    Accepts either ``Estado`` values or their string equivalents (columns are
    stored as text, so a ticket loaded from the DB carries a plain string).
    """
    current = Estado(current)
    requested = Estado(requested)
    return requested in ALLOWED_TRANSITIONS.get(current, set())


def assert_transition(current: Estado, requested: Estado) -> None:
    """Raise :class:`InvalidTransitionError` if the transition is invalid."""
    if not can_transition(current, requested):
        raise InvalidTransitionError(current, requested)
