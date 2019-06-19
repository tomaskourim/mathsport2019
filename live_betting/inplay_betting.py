import argparse

from live_betting.tipsport import Tipsport

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="")

    # initialize bookmaker bettor
    book = Tipsport()
    # login
    book.login()
    # get matches with betting potential
    tournaments = book.get_inplay_tournaments()
    print("Live")
    print(tournaments)

    tournaments = book.get_tournaments()
    print("------------------------------------------------------\nPrematch")
    print(tournaments)

    # compute internal odds
    # observe matches and wait for betting opportunity
    # if possible, bet
    # save all odds, bets and results
    # evaluate betting
    book.close()
