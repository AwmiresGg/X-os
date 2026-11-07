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


class DesktopSessionTests(unittest.TestCase):
    def test_detects_wayland_user_session(self):
        def _sh(*cmd, timeout=60):
            if cmd[:2] == ("loginctl", "list-sessions"):
                return 0, "3 1000 xos seat0 tty2\nc1 102 sddm seat0 tty1\n"
            if cmd[:2] == ("loginctl", "show-session"):
                return 0, ("Type=wayland\nClass=user\nState=active\nName=xos" if cmd[2] == "3"
                           else "Type=wayland\nClass=greeter\nState=online\nName=sddm")
            raise AssertionError(cmd)
        with mock.patch.object(selftest, "_sh", _sh), \
             mock.patch.object(selftest.Path, "exists", return_value=True):
            status, detail = selftest.check_desktop_session()
        self.assertEqual(status, "PASS")
        self.assertIn("wayland session for xos", detail)

    def test_greeter_only_is_failure_with_log(self):
        def _sh(*cmd, timeout=60):
            if cmd[:2] == ("loginctl", "list-sessions"):
                return 0, "c1 102 sddm seat0 tty1\n"
            if cmd[:2] == ("loginctl", "show-session"):
                return 0, "Type=wayland\nClass=greeter\nState=online\nName=sddm"
            if cmd[0] == "journalctl":
                return 0, "Autologin failed: session not found"
            raise AssertionError(cmd)
        with mock.patch.object(selftest, "_sh", _sh), mock.patch.object(selftest.time, "sleep"), \
             mock.patch.object(selftest.Path, "exists", return_value=True):
            status, detail = selftest.check_desktop_session(timeout=0.01)
        self.assertEqual(status, "FAIL")
        self.assertIn("Autologin failed", detail)
