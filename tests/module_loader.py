"""Helpers for loading Object Monitor modules without Home Assistant installed."""

from __future__ import annotations

import importlib
import sys
from types import ModuleType
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPONENT_DIR = ROOT / "custom_components" / "object_monitor"


def prepare_object_monitor_package() -> None:
    """Create namespace package stubs without executing integration __init__."""
    custom_components = sys.modules.setdefault(
        "custom_components",
        ModuleType("custom_components"),
    )
    custom_components.__path__ = [str(ROOT / "custom_components")]

    object_monitor = sys.modules.setdefault(
        "custom_components.object_monitor",
        ModuleType("custom_components.object_monitor"),
    )
    object_monitor.__path__ = [str(COMPONENT_DIR)]


def import_object_monitor_module(name: str) -> ModuleType:
    """Import an Object Monitor submodule without loading HA lifecycle glue."""
    prepare_object_monitor_package()
    return importlib.import_module(f"custom_components.object_monitor.{name}")
