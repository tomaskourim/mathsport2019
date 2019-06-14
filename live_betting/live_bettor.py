import argparse

from live_betting.tipsport import Tipsport

if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description="")

    # initialize bookmaker bettor
    book = Tipsport()
    # login
    # get matches with betting potential
    # compute internal odds
    # observe matches and wait for betting opportunity
    # if possible, bet
    # save all odds, bets and results
    # evaluate betting