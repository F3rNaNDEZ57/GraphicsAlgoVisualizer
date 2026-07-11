from algoviz.engine.playback import PlaybackState
from algoviz.engine.runner import Runner
from algoviz.pseudocode.errors import PseudocodeError


class FakeScheduler:
    """Runs callbacks synchronously and records cancellations, instead of
    a real event loop -- keeps Runner tests headless."""

    def __init__(self):
        self.calls: list[tuple[int, object]] = []
        self.cancelled: list[object] = []
        self._next_token = 0

    def after(self, delay_ms, callback):
        self._next_token += 1
        token = self._next_token
        self.calls.append((delay_ms, callback))
        return token

    def after_cancel(self, token):
        self.cancelled.append(token)

    def run_pending(self):
        # Drain calls in FIFO order, as if each after() fired once.
        while self.calls:
            _, callback = self.calls.pop(0)
            callback()


def counting_steps(n):
    for _ in range(n):
        yield


def labeled_steps(labels):
    yield from labels


def test_step_advances_generator_once():
    runner = Runner(FakeScheduler(), counting_steps(3), PlaybackState())
    runner.step()
    runner.step()
    runner.step()
    assert not runner.finished
    runner.step()  # 4th call: the 3 yields are exhausted, generator raises StopIteration
    assert runner.finished


def test_play_schedules_and_drains_to_completion():
    scheduler = FakeScheduler()
    finished = []
    runner = Runner(scheduler, counting_steps(2), PlaybackState(delay_ms=10), on_finish=lambda: finished.append(True))
    runner.play()
    assert scheduler.calls  # scheduled at least one tick
    for _ in range(10):
        if runner.finished:
            break
        scheduler.run_pending()
    assert runner.finished
    assert finished == [True]


def test_pause_cancels_pending_tick():
    scheduler = FakeScheduler()
    runner = Runner(scheduler, counting_steps(5), PlaybackState(delay_ms=10))
    runner.play()
    runner.pause()
    assert scheduler.cancelled
    assert runner.state.playing is False


def test_error_in_steps_invokes_on_error_and_stops():
    def bad_steps():
        yield
        raise PseudocodeError("boom")

    errors = []
    runner = Runner(FakeScheduler(), bad_steps(), PlaybackState(), on_error=errors.append)
    runner.step()
    assert not runner.finished
    runner.step()
    assert runner.finished
    assert len(errors) == 1
    assert "boom" in str(errors[0])


def test_on_step_receives_each_yielded_value():
    received = []
    runner = Runner(
        FakeScheduler(), labeled_steps(["a", "b", "c"]), PlaybackState(), on_step=received.append
    )
    runner.step()
    runner.step()
    runner.step()
    assert received == ["a", "b", "c"]
