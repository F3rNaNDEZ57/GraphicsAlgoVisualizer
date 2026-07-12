"""Drives a pseudocode interpreter's step generator against any scheduler
that looks like Tkinter's after()/after_cancel() — structurally typed, so
this module never imports tkinter and stays testable headless.
"""

from __future__ import annotations

from typing import Any, Callable, Iterator, Optional, Protocol

from ..pseudocode.errors import PseudocodeError
from .playback import PlaybackState


class Scheduler(Protocol):
    def after(self, delay_ms: int, callback: Callable[[], None]) -> object: ...
    def after_cancel(self, token: object) -> None: ...


class Runner:
    def __init__(
        self,
        scheduler: Scheduler,
        steps: Iterator[Any],
        state: PlaybackState,
        on_finish: Optional[Callable[[], None]] = None,
        on_error: Optional[Callable[[PseudocodeError], None]] = None,
        on_step: Optional[Callable[[Any], None]] = None,
    ):
        self.scheduler = scheduler
        self._steps = steps
        self.state = state
        self.on_finish = on_finish
        self.on_error = on_error
        self.on_step = on_step
        self._after_token: object | None = None
        self._finished = False

    @property
    def finished(self) -> bool:
        return self._finished

    def play(self) -> None:
        if self._finished:
            return
        self.state.playing = True
        self._schedule_next()

    def pause(self) -> None:
        self.state.playing = False
        if self._after_token is not None:
            self.scheduler.after_cancel(self._after_token)
            self._after_token = None

    def step(self) -> None:
        self._advance_once()

    def _schedule_next(self) -> None:
        if not self.state.playing or self._finished:
            return
        self._after_token = self.scheduler.after(self.state.delay_ms, self._tick)

    def _tick(self) -> None:
        self._advance_once()
        self._schedule_next()

    def _advance_once(self) -> None:
        if self._finished:
            return
        try:
            event = next(self._steps)
        except StopIteration:
            self._finish(self.on_finish)
        except PseudocodeError as exc:
            if self.on_error is None:
                self._finished = True
                self.state.playing = False
                raise
            self._finish(lambda: self.on_error(exc))
        else:
            if self.on_step:
                self.on_step(event)

    def _finish(self, callback: Optional[Callable[[], None]]) -> None:
        self._finished = True
        self.state.playing = False
        if callback:
            callback()
