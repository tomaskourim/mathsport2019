import argparse

from selenium.common.exceptions import StaleElementReferenceException

from live_betting.tipsport import Tipsport

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="")

    # initialize bookmaker bettor
    book = Tipsport()
    # login
    # book.login()
    # get matches with betting potential

    # initialize Postgres DB, connect, create tables
    # prematch:
    # get tournaments & their IDs. Check database, save new ones
    tournaments = book.get_tournaments()
    print("------------------------------------------------------\nPrematch")
    print(tournaments)

    # for each tournament, get matches and their IDs. Check database, save new ones, update starting times
    # optional save odds (all or many or some) to DB
    for tournament in tournaments.iterrows():
        # print("------------------------------------------------------")
        try:
            matches = book.get_matches_tournament(tournament[1])
            print(f"Parsed tournament {tournament[1]['name']}")
        except StaleElementReferenceException:
            print(f"Imposible to parse tournament {tournament[1]['name']}")
            continue

    # for matches about to start, get first set odds & save to DB
    # regularly repeat (especially to update starting times)

    # TODO handle multithreading
    # get lambda coefficient from somewhere (asi z optimalizace 2018)

    # in-play
    # get tournaments & pair with prematch
    # tournaments = book.get_inplay_tournaments()
    # print("------------------------------------------------------\nLive")
    # print(tournaments)

    # for each tournament, get matches & pair with prematch
    # for each match, get 1.set odds & compute probabilities
    # observe for end of a set
    # once a set is over, compute next set probabilities & compare them with odds
    # if applicable, bet
    # repeat regularly

    # compute internal odds
    # observe matches and wait for betting opportunity
    # if possible, bet
    # save all odds, bets and results
    # evaluate betting
    book.close()
