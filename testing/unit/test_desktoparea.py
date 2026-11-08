import unittest

from xos import desktoparea as D


class DesktopAreaTests(unittest.TestCase):
    def test_bar_sizes_from_tokens(self):
        self.assertEqual(D.bar_sizes({"bar": {"menuBarHeight": 34, "dockHeight": 64, "edgeMargin": 8}}), (34, 80))
        top, bottom = D.bar_sizes()          # the repository's tokens
        self.assertGreater(top, 0)
        self.assertGreater(bottom, top)

    def test_available_rect_excludes_bars(self):
        self.assertEqual(D.available_rect(0, 0, 1920, 1080, 34, 80), (0, 34, 1920, 966))
        # second monitor to the right keeps its own origin
        self.assertEqual(D.available_rect(1920, 0, 1280, 800, 34, 80), (1920, 34, 1280, 686))

    def test_tiny_screen_is_left_alone(self):
        self.assertEqual(D.available_rect(0, 0, 100, 100, 60, 60), (0, 0, 100, 100))


if __name__ == "__main__":
    unittest.main()
