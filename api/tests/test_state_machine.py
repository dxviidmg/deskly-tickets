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
        (Estado.resuelto, Estado.abierto),  # reopen
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
