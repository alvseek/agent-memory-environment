"""Evidence-classifier unit tests; these do not hold requests or lock the host."""

import unittest

from battery_endurance_probe import evaluate


def sample(t, awake=None, **changes):
    return {"uptime_s": t, "awake_s": t if awake is None else awake,
            "ac": 0, "locked": True, "critical_battery": False, "console_session": 1, **changes}


class EnduranceEvidenceTests(unittest.TestCase):
    def test_full_synthetic_observation_is_not_causal_or_watcher_proof(self):
        result = evaluate([sample(t) for t in range(11)], 10)
        self.assertTrue(result["observation_passed"])
        self.assertFalse(result["causal_attribution_verified"])
        self.assertFalse(result["watcher_verified"])

    def test_short_or_empty_run_is_not_success(self):
        self.assertFalse(evaluate([], 10)["observation_passed"])
        self.assertFalse(evaluate([sample(0), sample(1)], 10)["observation_passed"])

    def test_power_or_lock_changes_invalidate_observation(self):
        for change in ({"ac": 1}, {"locked": False}, {"critical_battery": True}, {"console_session": 2}):
            values = [sample(t) for t in range(11)]
            values[5].update(change)
            self.assertFalse(evaluate(values, 10)["observation_passed"])

    def test_sleep_or_scheduling_stall_is_not_a_pass(self):
        self.assertFalse(evaluate([sample(0), sample(10, awake=1)], 10)["observation_passed"])
        self.assertFalse(evaluate([sample(0), sample(10)], 10)["observation_passed"])


if __name__ == "__main__":
    unittest.main()
