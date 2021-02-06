import unittest

from live_betting.tipsport import Tipsport


class testTipsport(unittest.TestCase):
    def test_get_score_from_video_raw_text(self):
        main_book = Tipsport()
        # score = main_book.get_score_from_video_raw_text(3, "1:1super tiebreak - 5:7, 6:4, 11:10*", "11:10*")
        # self.assertEqual(((1, 1), (11, 10), '11:10'), score)

        score = main_book.get_score_from_video_raw_text(3, "2:1(5:7, 6:4, 12:10)", "11:10")
        self.assertEqual(((2, 1), (12, 10), '11:10'), score)


if __name__ == '__main__':
    unittest.main()
