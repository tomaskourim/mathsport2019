import argparse
import logging
from datetime import datetime

from live_betting.bookmaker import Bookmaker
from live_betting.prematch_operations import get_save_tournaments, process_tournaments_save_matches
from live_betting.tipsport import Tipsport


def scan_update(book: Bookmaker):
    # get tournaments & their IDs. Check database, save new ones.
    main_tournaments = get_save_tournaments(book)

    # for each tournament, get matches and their IDs. Check database, save new ones, update starting times
    # optional save odds (all or many or some) to DB
    process_tournaments_save_matches(book, main_tournaments)
    pass


def get_starting_matches():
    pass


if __name__ == '__main__':
    start_time = datetime.now()
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(
        description="")

    # TODO use logging

    # crone 1x za N minut.
    # Podivam, jeslti mam neco v live nebo jestli mi zacina zapas. Kdyz ne, pustim update databaze.
    #
    # Kdyz mi zacina zapas, podivam se na dany zapas (pustim extra vlakno a driver?). 1.set kurzy parsuju a aktualizuju
    # a znovu parsuju az do chvile, kdy zapas zmizi z prematch a zacne live. Do DB si ulozim starting odds
    # (jake vsechny?) a v pameti si drzim dany zapas (pres ID) a jeho starting odds na prvni set.
    #
    # Kdyz mam neco v live, zkontroluju, jestli se blizi konec setu.
    #
    # Kdyz se blizi konec setu, podivam se na dany zapas (pustim extra vlakno a driver?). Sleduju, dokud set nekonci.
    # Jakmile skonci, prepocitam prst vyhry v dalsim setu, ulozim ji do DB, a porovnam s nabizenymi kurzy (ty rovnez
    # ulozim). Pokud to nekde jde, sazim (a sazku ulozim do DB). Jakmile set zacne, prestavam zapas aktivne sledovat.

    # initialize bookmaker bettor
    main_book = Tipsport()
    # login
    # book.login()
    # get matches with betting potential
    start_time_run = datetime.now()
    
    starting_matches=get_starting_matches()
    
    scan_update(main_book)
    end_time = datetime.now()
    logging.info(f"\nDuration first run: {(end_time - start_time_run)}")

    # start_time_run = datetime.now()
    # scan_update(main_book)
    # end_time = datetime.now()
    # logging.info(f"\nDuration second run: {(end_time - start_time_run)}")

    # for matches about to start, get first set odds & save to DB
    # regularly repeat (especially to update starting times)

    # TODO handle multithreading
    # get lambda coefficient from somewhere (asi z optimalizace 2018)

    # in-play
    # get tournaments & pair with prematch
    # tournaments = book.get_inplay_tournaments()
    # logging.info("------------------------------------------------------\nLive")
    # logging.info(tournaments)

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
    main_book.close()
    end_time = datetime.now()
    logging.info(f"\nDuration: {(end_time - start_time)}")
