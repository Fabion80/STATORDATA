import unittest
from datetime import datetime

from build_data import archive_cutoff, assert_no_regression


class PublicationTests(unittest.TestCase):
    def test_french_day_boundary_in_summer_and_winter(self):
        self.assertEqual("2026-10-12", archive_cutoff(datetime.fromisoformat("2026-10-11T22:05:00+00:00")))
        self.assertEqual("2026-10-11", archive_cutoff(datetime.fromisoformat("2026-10-11T21:55:00+00:00")))
        self.assertEqual("2026-12-12", archive_cutoff(datetime.fromisoformat("2026-12-11T23:05:00+00:00")))
        self.assertEqual("2026-12-11", archive_cutoff(datetime.fromisoformat("2026-12-11T22:55:00+00:00")))

    def test_published_draws_are_preserved(self):
        old = {"id": "loto:2026-10-07", "game": "loto", "date": "2026-10-07", "numbers": [6, 34, 35, 42, 47], "chance": 8}
        new = {"id": "loto:2026-10-10", "game": "loto", "date": "2026-10-10", "numbers": [4, 17, 22, 46, 49], "chance": 4}
        assert_no_regression([old, new], [old])
        with self.assertRaisesRegex(RuntimeError, "missing"):
            assert_no_regression([new], [old])
        for changes in ({"chance": 9}, {"numbers": [7, 34, 35, 42, 47]}):
            with self.assertRaisesRegex(RuntimeError, "changed"):
                assert_no_regression([{**old, **changes}, new], [old])


if __name__ == "__main__":
    unittest.main()
