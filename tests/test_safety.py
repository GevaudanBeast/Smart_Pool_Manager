"""Tests des regles de securite.

Couvre evaluate_safety pour chaque regle : niveau bas, filtration arretee,
sonde indisponible, watchdog, delai entre doses, et cas nominal.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "custom_components",
        "smart_pool_manager",
    ),
)

from calculations.safety import evaluate_safety  # noqa: E402

CONFIG = {"delay_between_doses_min": 60}


def _base_data():
    """Etat de base sain : tout permet le dosage."""
    return {
        "level_low": False,
        "filtration_running": True,
        "ph": 7.4,
        "cl": 2.0,
        "last_dose_ph": None,
        "last_dose_cl": None,
        "dosing_ph_running_since_s": 0,
        "dosing_cl_running_since_s": 0,
    }


def test_level_low_blocks_everything():
    data = _base_data()
    data["level_low"] = True
    result = evaluate_safety(data, CONFIG)
    assert result.dosing_ok is False
    assert result.filtration_ok is False
    assert "Insufficient water level" in result.reasons


def test_filtration_stopped_blocks_dosing_only():
    data = _base_data()
    data["filtration_running"] = False
    result = evaluate_safety(data, CONFIG)
    assert result.dosing_ok is False
    assert result.filtration_ok is True
    assert "Filtration stopped - dosing forbidden" in result.reasons


def test_probe_unavailable_blocks_dosing():
    data = _base_data()
    data["ph"] = None
    result = evaluate_safety(data, CONFIG)
    assert result.dosing_ok is False
    assert "Probe unavailable - auto dosing suspended" in result.reasons


def test_watchdog_forces_stop():
    data = _base_data()
    data["dosing_ph_running_since_s"] = 4000
    result = evaluate_safety(data, CONFIG)
    assert result.force_stop_dosing is True
    assert result.dosing_ok is False
    assert "Watchdog: pump active for more than 1 hour" in result.reasons


def test_delay_not_elapsed_adds_reason():
    data = _base_data()
    data["last_dose_ph"] = datetime.now() - timedelta(minutes=10)
    result = evaluate_safety(data, CONFIG)
    assert any("pH dose delay not elapsed" in r for r in result.reasons)


def test_delay_elapsed_no_reason():
    data = _base_data()
    data["last_dose_ph"] = datetime.now() - timedelta(minutes=90)
    result = evaluate_safety(data, CONFIG)
    assert not any("pH dose delay not elapsed" in r for r in result.reasons)


def test_all_ok():
    data = _base_data()
    result = evaluate_safety(data, CONFIG)
    assert result.dosing_ok is True
    assert result.filtration_ok is True
    assert result.force_stop_dosing is False
    assert result.reasons == []
