"""Shared surfaces, controls, and marks that views compose but do not own."""

from __future__ import annotations

from sieve.gui.primitives.banner import DONE, FAIL, NOTE, WARN, Banner
from sieve.gui.primitives.button import DEFAULT, GHOST, PRIMARY, SUBTLE, Button
from sieve.gui.primitives.card import Card
from sieve.gui.primitives.check import Check
from sieve.gui.primitives.empty import Empty
from sieve.gui.primitives.facts import Fact, Facts
from sieve.gui.primitives.field import Field, LineField
from sieve.gui.primitives.menu import Menu
from sieve.gui.primitives.meter import Meter
from sieve.gui.primitives.nav import SectionNav
from sieve.gui.primitives.pill import IDLE, LIVE, OFF, Pill
from sieve.gui.primitives.sections import Section, SectionCard
from sieve.gui.primitives.segmented import Segmented
from sieve.gui.primitives.select import Select
from sieve.gui.primitives.slider import Slider
from sieve.gui.primitives.stack import CardStack
from sieve.gui.primitives.table import Column, Table
from sieve.gui.primitives.tabs import Tabs
from sieve.gui.primitives.view import View

__all__ = [
    "DEFAULT",
    "DONE",
    "FAIL",
    "GHOST",
    "IDLE",
    "LIVE",
    "NOTE",
    "OFF",
    "PRIMARY",
    "SUBTLE",
    "WARN",
    "Banner",
    "Button",
    "Card",
    "CardStack",
    "Check",
    "Column",
    "Empty",
    "Fact",
    "Facts",
    "Field",
    "LineField",
    "Menu",
    "Meter",
    "Pill",
    "Section",
    "SectionCard",
    "SectionNav",
    "Segmented",
    "Select",
    "Slider",
    "Table",
    "Tabs",
    "View",
]
