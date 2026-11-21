"""Verifie que le coordinator passe bien par le filtre de plausibilite.

Lecon SRM : un test vert sur une fonction pure ne prouve rien si le code de
production ne l'appelle pas. Le coordinator depend de Home Assistant, absent
de l'environnement de test : on verifie donc son cablage par analyse
syntaxique (AST), sans l'importer.
"""

from __future__ import annotations

import ast
import os

COORDINATOR = os.path.join(
    os.path.dirname(__file__),
    "..",
    "custom_components",
    "smart_pool_manager",
    "coordinator.py",
)


def _method(name: str) -> ast.AsyncFunctionDef | ast.FunctionDef:
    with open(COORDINATOR, encoding="utf-8") as handle:
        tree = ast.parse(handle.read())
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and (
            node.name == name
        ):
            return node
    raise AssertionError(f"methode {name} introuvable")


def _call_lines(func, attr: str) -> list[int]:
    return [
        node.lineno
        for node in ast.walk(func)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == attr
    ]


def test_filtre_appele_avant_calculs_et_securite():
    update = _method("_async_update_data")
    sanitize = _call_lines(update, "sanitize_measures")
    assert sanitize, "sanitize_measures n'est pas appele dans le cycle"
    first = min(sanitize)
    for later in (
        "calculate_ph_dose",
        "calculate_cl_dose",
        "evaluate_safety",
        "compute_recommendations",
    ):
        lines = _call_lines(update, later)
        assert lines, f"{later} introuvable"
        assert min(lines) > first, f"{later} appele avant le filtre"


def test_rejets_transmis_a_la_securite_et_aux_recos():
    update = _method("_async_update_data")
    keys = {
        node.value
        for node in ast.walk(update)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    assert "probe_out_of_range" in keys
    assert "rejected" in keys
