import unittest

from live_betting.tipsport import Tipsport

main_book = Tipsport()


class testTipsport(unittest.TestCase):
    def test_get_score_from_video_raw_text(self):
        score = main_book.get_score_from_video_raw_text(3, "1:1super tiebreak - 5:7, 6:4, 11:10*", "11:10*")
        self.assertEqual(((1, 1), (11, 10), '11:10'), score)

        score = main_book.get_score_from_video_raw_text(3, "2:1(5:7, 6:4, 12:10)", "11:10")
        self.assertEqual(((2, 1), (12, 10), '11:10'), score)

    def test_compute_bet(self):
        bet_amount = main_book.compute_bet(0.07713517328285746)
        self.assertEqual(str(main_book.minimal_bet_amount), bet_amount)


if __name__ == '__main__':
    unittest.main()
