import itertools
import unittest
from unittest import mock

from xos import selftest


def fake_systemctl(states, jobs, failed=""):
    """Return a _sh replacement that replays is-system-running states."""
    seq = itertools.chain(states, itertools.repeat(states[-1]))

    def _sh(*cmd, timeout=60):
        if cmd[:2] == ("systemctl", "is-system-running"):
            return 0, next(seq)
        if cmd[:2] == ("systemctl", "list-jobs"):
            return 0, jobs
        if cmd[:2] == ("systemctl", "--failed"):
            return 0, failed
        raise AssertionError(cmd)
    return _sh


class SystemdCheckTests(unittest.TestCase):
    def test_only_own_job_pending_counts_as_running(self):
        jobs = "42 xos-selftest.service start running\n"
        with mock.patch.object(selftest, "_sh", fake_systemctl(["starting"], jobs)):
            self.assertEqual(selftest.check_systemd()[0], "PASS")

    def test_waits_for_other_jobs(self):
        jobs = "42 xos-selftest.service start running\n43 sddm.service start waiting\n"
        with mock.patch.object(selftest, "_sh", fake_systemctl(["starting", "running"], jobs)), \
             mock.patch.object(selftest.time, "sleep"):
            self.assertEqual(selftest.check_systemd()[0], "PASS")

    def test_degraded_reports_failed_units(self):
        with mock.patch.object(selftest, "_sh", fake_systemctl(["degraded"], "", "foo.service loaded failed failed Foo\n")):
            status, detail = selftest.check_systemd()
        self.assertEqual(status, "FAIL")
        self.assertIn("foo.service", detail)

    def test_timeout_is_failure(self):
        jobs = "43 sddm.service start waiting\n"
        with mock.patch.object(selftest, "_sh", fake_systemctl(["starting"], jobs)), \
             mock.patch.object(selftest.time, "sleep"):
            status, _ = selftest.check_systemd(timeout=0.01)
        self.assertEqual(status, "FAIL")


class SummaryTests(unittest.TestCase):
    def test_summary_has_machine_readable_result(self):
        report = {"overall": "PASS", "uptime_seconds": 12.0, "recommended_profile": "lite",
                  "profile_reasons": ["x"], "checks": {"a": {"status": "PASS", "detail": "ok"}},
                  "hardware": {"problems": [{"status": "no-driver", "category": "Other hardware", "vendor": "V",
                                             "name": "N", "bus": "pci", "address": "0000:00:01.0",
                                             "vendor_id": "1234", "device_id": "5678"}]}}
        text = selftest.format_summary(report)
        self.assertTrue(text.splitlines()[-1] == "XOS-SELFTEST-RESULT: PASS")
        self.assertIn("1234:5678", text)


if __name__ == "__main__":
    unittest.main()
