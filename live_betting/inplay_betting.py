import argparse
import datetime

from psycopg2._psycopg import IntegrityError
from selenium.common.exceptions import StaleElementReferenceException

from database_operations import execute_sql_postgres
from live_betting.tipsport import Tipsport


def get_tournament_id(book_id, tournament_bookmaker_id, tournament_bookmaker_year_id):
    query = "SELECT tournament_id FROM tournament_bookmaker WHERE bookmaker_id=%s AND tournament_bookmaker_id=%s AND \
                tournament_bookmaker_extra_id=%s"
    return execute_sql_postgres(query, [book_id, tournament_bookmaker_id, tournament_bookmaker_year_id])


def save_tournament(params):
    query_tournament = f"INSERT INTO tournament (name, sex, type, surface, year) VALUES ({', '.join(['%s'] * 5)}) \
                        RETURNING id"
    return execute_sql_postgres(query_tournament, params, True)


def save_tournament_bookmaker(params):
    query_tournament_book = f"INSERT INTO tournament_bookmaker (tournament_id, bookmaker_id, \
            tournament_bookmaker_id, tournament_bookmaker_extra_id) VALUES ({', '.join(['%s'] * 4)}) RETURNING id"
    return execute_sql_postgres(query_tournament_book, params, True)


def get_save_tournaments(book):
    tournaments = book.get_tournaments()
    print("------------------------------------------------------\nPrematch")
    print(tournaments)

    book_id = book.database_id
    year = datetime.datetime.now().year

    for i, tournament in tournaments.iterrows():
        if tournament['sex'] is None or tournament['type'] is None or tournament['surface'] is None:
            continue
        params = tournament[['name', 'sex', 'type', 'surface']].tolist()
        params.append(year)
        db_returned = save_tournament(params)
        if type(db_returned) == IntegrityError:
            if 'duplicate key value violates unique constraint' in db_returned.args[0]:
                continue
            else:
                raise db_returned
        elif type(db_returned == tuple) and type(db_returned[0] == int):
            params = [db_returned[0], book_id, tournament.tournament_bookmaker_id,
                      tournament.tournament_bookmaker_year_id]
            save_tournament_bookmaker(params)
        else:
            raise db_returned

    return tournaments


def save_matches(matches, tournament_id):
    pass


def process_tournaments_save_matches(book, tournaments):
    for i,tournament in tournaments.iterrows():
        # print("------------------------------------------------------")
        try:
            matches = main_book.get_matches_tournament(tournament)
            if len(matches) > 0:
                tournament_id = get_tournament_id(book.database_id, tournament.tournament_bookmaker_id,
                                                  tournament.tournament_bookmaker_year_id)
                if tournament_id is None:
                    continue
                save_matches(matches, tournament_id[0])
        except StaleElementReferenceException as error:
            print(f"Imposible to parse tournament {tournament[1]['name']}. Error: {error}")
            continue
    pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="")

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

    # initialize Postgres DB, connect, create tables
    # prematch:
    # get tournaments & their IDs. Check database, save new ones.
    main_tournaments = get_save_tournaments(main_book)

    # for each tournament, get matches and their IDs. Check database, save new ones, update starting times
    # optional save odds (all or many or some) to DB
    process_tournaments_save_matches(main_book, main_tournaments)

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
    main_book.close()
