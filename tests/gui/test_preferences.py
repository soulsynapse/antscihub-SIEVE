"""Preferences: defaults, coercion of whatever the store hands back, clamping.

Run against a temporary INI file rather than the real store. That is not only
isolation — an INI backing store returns *strings*, which is exactly the case
the coercion in `preferences.py` exists for and which a native-format store
would hide.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QSettings

from sieve.gui.preferences import (
    ADAPTIVE_SCRUB,
    COARSE_INTERVAL_SECONDS,
    DEFAULT_ADAPTIVE_SCRUB,
    DEFAULT_COARSE_INTERVAL_SECONDS,
    DEFAULT_PROXY_WIDTH,
    MAX_PROXY_WIDTH,
    MIN_PROXY_WIDTH,
    PROXY_WIDTH,
    Preferences,
)

pytestmark = pytest.mark.gui


@pytest.fixture
def settings(qapp: object, tmp_path: Path) -> QSettings:
    del qapp
    return QSettings(str(tmp_path / "sieve.ini"), QSettings.Format.IniFormat)


@pytest.fixture
def preferences(settings: QSettings) -> Preferences:
    return Preferences(settings)


class TestDefaults:
    def test_an_empty_store_yields_the_defaults(self, preferences: Preferences) -> None:
        assert preferences.adaptive_scrub is DEFAULT_ADAPTIVE_SCRUB
        assert preferences.coarse_interval_seconds == DEFAULT_COARSE_INTERVAL_SECONDS
        assert preferences.proxy_width == DEFAULT_PROXY_WIDTH


class TestRoundTrip:
    def test_values_survive_a_new_store_over_the_same_file(
        self, preferences: Preferences, settings: QSettings
    ) -> None:
        preferences.adaptive_scrub = False
        preferences.coarse_interval_seconds = 2.5
        preferences.proxy_width = 1920

        reopened = Preferences(QSettings(settings.fileName(), QSettings.Format.IniFormat))
        assert reopened.adaptive_scrub is False
        assert reopened.coarse_interval_seconds == pytest.approx(2.5)
        assert reopened.proxy_width == 1920


class TestChangeSignal:
    def test_writing_a_new_value_emits_changed(self, preferences: Preferences) -> None:
        seen: list[int] = []
        preferences.changed.connect(lambda: seen.append(1))
        preferences.proxy_width = 1920
        assert len(seen) == 1

    def test_writing_the_same_value_is_silent(self, preferences: Preferences) -> None:
        preferences.proxy_width = 1920
        seen: list[int] = []
        preferences.changed.connect(lambda: seen.append(1))
        preferences.proxy_width = 1920
        assert seen == []

    def test_restore_defaults_emits_once_and_resets_everything(
        self, preferences: Preferences
    ) -> None:
        preferences.adaptive_scrub = False
        preferences.proxy_width = 1920
        seen: list[int] = []
        preferences.changed.connect(lambda: seen.append(1))

        preferences.restore_defaults()

        assert len(seen) == 1
        assert preferences.adaptive_scrub is DEFAULT_ADAPTIVE_SCRUB
        assert preferences.proxy_width == DEFAULT_PROXY_WIDTH


class TestCoercion:
    """An INI store returns strings; a hand-edited one can return nonsense."""

    def test_string_booleans_are_understood(
        self, preferences: Preferences, settings: QSettings
    ) -> None:
        settings.setValue(ADAPTIVE_SCRUB, "false")
        assert preferences.adaptive_scrub is False
        settings.setValue(ADAPTIVE_SCRUB, "true")
        assert preferences.adaptive_scrub is True

    def test_string_numbers_are_understood(
        self, preferences: Preferences, settings: QSettings
    ) -> None:
        settings.setValue(PROXY_WIDTH, "1600")
        assert preferences.proxy_width == 1600

    def test_junk_falls_back_to_the_default(
        self, preferences: Preferences, settings: QSettings
    ) -> None:
        settings.setValue(PROXY_WIDTH, "not a number")
        assert preferences.proxy_width == DEFAULT_PROXY_WIDTH
        settings.setValue(ADAPTIVE_SCRUB, "maybe")
        assert preferences.adaptive_scrub is DEFAULT_ADAPTIVE_SCRUB

    def test_out_of_range_values_are_clamped_on_read(
        self, preferences: Preferences, settings: QSettings
    ) -> None:
        # A value left by an older build, or edited by hand, must not put the
        # application somewhere its own UI cannot express.
        settings.setValue(PROXY_WIDTH, 99_999)
        assert preferences.proxy_width == MAX_PROXY_WIDTH
        settings.setValue(PROXY_WIDTH, 1)
        assert preferences.proxy_width == MIN_PROXY_WIDTH

    def test_out_of_range_values_are_clamped_on_write(self, preferences: Preferences) -> None:
        preferences.proxy_width = 99_999
        assert preferences.proxy_width == MAX_PROXY_WIDTH

    def test_a_missing_interval_does_not_clamp_to_the_minimum(
        self, preferences: Preferences, settings: QSettings
    ) -> None:
        settings.remove(COARSE_INTERVAL_SECONDS)
        assert preferences.coarse_interval_seconds == DEFAULT_COARSE_INTERVAL_SECONDS
