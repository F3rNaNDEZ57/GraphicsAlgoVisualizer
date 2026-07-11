import pytest


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
