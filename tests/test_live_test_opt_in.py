from types import SimpleNamespace

import conftest


class DummyConfig:
    def __init__(self, *, run_live=False, markexpr=""):
        self.option = SimpleNamespace(markexpr=markexpr)
        self._run_live = run_live

    def getoption(self, name):
        if name == "--run-live":
            return self._run_live
        raise ValueError(name)


def test_live_tests_stay_disabled_by_default():
    assert not conftest._live_tests_requested(DummyConfig())


def test_run_live_flag_enables_live_tests():
    assert conftest._live_tests_requested(DummyConfig(run_live=True))


def test_real_mark_expression_enables_live_tests():
    assert conftest._live_tests_requested(DummyConfig(markexpr="real"))


def test_compound_mark_expression_can_enable_live_tests():
    assert conftest._live_tests_requested(DummyConfig(markexpr="smoke or real"))


def test_unrelated_mark_expression_does_not_enable_live_tests():
    assert not conftest._live_tests_requested(DummyConfig(markexpr="smoke"))
