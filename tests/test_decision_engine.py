from __future__ import annotations

import unittest

from jarvis.core.config import ProactivityLevel
from jarvis.core.decision_engine import Decision, DecisionContext, DecisionEngine


class DecisionEngineTests(unittest.TestCase):
    def test_off_always_ignores(self) -> None:
        decision = DecisionEngine().decide(DecisionContext(100, ProactivityLevel.OFF))
        self.assertIs(decision, Decision.IGNORE)

    def test_critical_event_speaks(self) -> None:
        decision = DecisionEngine().decide(DecisionContext(100, ProactivityLevel.NORMAL))
        self.assertIs(decision, Decision.SPEAK)

    def test_silent_mode_never_speaks(self) -> None:
        decision = DecisionEngine().decide(DecisionContext(100, ProactivityLevel.NORMAL, mode="SILENT"))
        self.assertIs(decision, Decision.NOTIFY)


if __name__ == "__main__":
    unittest.main()

