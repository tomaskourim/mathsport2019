from live_betting.bookmaker import Bookmaker


class Tipsport(Bookmaker):
    def __init__(self):
        Bookmaker.__init__(self, "https://www.tipsport.cz/")
