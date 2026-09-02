"""Unit tests for the ticket state machine."""
import pytest

from app.enums import Estado
from app.state_machine import (
    InvalidTransitionError,
    assert_transition,
    can_transition,
)


@pytest.mark.parametrize(
    "current,requested",
    [
        (Estado.abierto, Estado.en_progreso),
        (Estado.en_progreso, Estado.resuelto),
        (Estado.resuelto, Estado.cerrado),
        (Estado.resuelto, Estado.reabierto),  # reopen
        (Estado.reabierto, Estado.en_progreso),  # se retoma el trabajo
        (Estado.reabierto, Estado.cerrado),
    ],
)
def test_valid_transitions(current, requested):
    assert can_transition(current, requested) is True
    assert_transition(current, requested)  # should not raise


@pytest.mark.parametrize(
    "current,requested",
    [
        (Estado.abierto, Estado.cerrado),
        (Estado.abierto, Estado.resuelto),
        (Estado.en_progreso, Estado.cerrado),
        (Estado.resuelto, Estado.abierto),  # ya no: la reapertura va a "reabierto"
        (Estado.cerrado, Estado.abierto),
        (Estado.cerrado, Estado.en_progreso),
    ],
)
def test_invalid_transitions(current, requested):
    assert can_transition(current, requested) is False
    with pytest.raises(InvalidTransitionError) as exc_info:
        assert_transition(current, requested)
    err = exc_info.value
    assert err.current == current
    assert err.requested == requested
    assert isinstance(err.allowed, list)


def test_accepts_string_inputs_like_the_database():
    # Tickets loaded from the DB carry the estado as a plain string, not the
    # Estado enum. The state machine must handle that without raising
    # AttributeError (regression: previously produced a 500 instead of 409).
    assert can_transition("abierto", "en_progreso") is True
    assert can_transition("abierto", "cerrado") is False
    with pytest.raises(InvalidTransitionError) as exc_info:
        assert_transition("abierto", "cerrado")
    assert exc_info.value.current == Estado.abierto
    assert exc_info.value.requested == Estado.cerrado
