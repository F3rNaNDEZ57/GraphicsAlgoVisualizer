import pytest

from algoviz.preset_loader import BUNDLED_PRESETS_DIR, LoadedPreset, load_all_presets


def bundled_preset(name: str) -> LoadedPreset:
    """Loads one bundled preset by name -- used by algorithm tests that
    need the real shipped pseudocode source, not a hand-copied duplicate."""
    presets, errors = load_all_presets(bundled_dir=BUNDLED_PRESETS_DIR, user_dir=BUNDLED_PRESETS_DIR.parent / "__no_user_dir__")
    assert not errors, f"bundled preset load errors: {errors}"
    return presets[name]


class RecordingCanvas:
    """Headless double: records every canvas method call instead of drawing.

    Used to test the interpreter/algorithms with zero GUI dependency.
    """

    def __init__(self):
        self.calls: list[tuple[str, tuple, dict]] = []

    def __getattr__(self, name: str):
        def method(*args, **kwargs):
            self.calls.append((name, args, kwargs))

        return method


@pytest.fixture
def recording_canvas() -> RecordingCanvas:
    return RecordingCanvas()
