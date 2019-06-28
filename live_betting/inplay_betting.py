import argparse
import datetime
import logging
import threading
from typing import List

import pytz

from database_operations import execute_sql_postgres
from live_betting.bookmaker import Bookmaker
from live_betting.config_betting import TIME_TO_MATCHSTART_MINUTES
from live_betting.prematch_operations import get_save_tournaments, process_tournaments_save_matches
from live_betting.tipsport import Tipsport


def scan_update(book: Bookmaker):
    # get tournaments & their IDs. Check database, save new ones.
    main_tournaments = get_save_tournaments(book)

    # for each tournament, get matches and their IDs. Check database, save new ones, update starting times
    # optional save odds (all or many or some) to DB
    process_tournaments_save_matches(book, main_tournaments)
    pass


def get_starting_matches() -> List[tuple]:
    utc_time = pytz.utc.localize(datetime.datetime.utcnow())
    limit_start_time = utc_time + datetime.timedelta(minutes=TIME_TO_MATCHSTART_MINUTES)
    query = "SELECT match_bookmaker_id FROM \
                (SELECT * FROM matches WHERE start_time_utc > %s AND start_time_utc < %s) AS matches \
                JOIN \
                matches_bookmaker ON matches.id = match_id"  # TODO except already in-play
    params = [utc_time, limit_start_time]
    return execute_sql_postgres(query, params, False, True)


def handle_match(bookmaker_matchid: str):
    logging.info(f"Handling match:{bookmaker_matchid}")
    book = Tipsport()
    book.handle_match(bookmaker_matchid)

    logging.info(f"Finished handling match: {bookmaker_matchid}")

    pass


if __name__ == '__main__':
    start_time = datetime.datetime.now()
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(
        description="")

    starting_matches_ids = get_starting_matches()
    for bookmaker_match_id_tuple in starting_matches_ids:
        # handle_match(bookmaker_match_id_tuple[0])
        thread = threading.Thread(target=handle_match, args=(bookmaker_match_id_tuple[0],))
        thread.start()
        logging.info(f"{bookmaker_match_id_tuple[0]} Main thread handling match: {bookmaker_match_id_tuple[0]}")

    logging.info(f"Main thread finish")

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
    start_time_run = datetime.datetime.now()

    scan_update(main_book)
    end_time = datetime.datetime.now()
    logging.info(f"\nDuration first run: {(end_time - start_time_run)}")

    # start_time_run = datetime.datetime.now()
    # scan_update(main_book)
    # end_time = datetime.datetime.now()
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
    end_time = datetime.datetime.now()
    logging.info(f"\nDuration: {(end_time - start_time)}")
