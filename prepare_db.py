# This is a support file used only for one time extraction of a database from a larger and more complex database

import argparse
import csv
import os

from database_operations import execute_sql

ORIGINAL_DATABASE_PATH = 'C://tennis.sqlite'


def export_tournaments(first_year, last_year):
    sql = "select * from turnaje where pohlavi=\'men\' and typ=\'dvouhra\' and rok>=? and rok<=? and (nazev like \
    '%Australian open%' or nazev like '%French open%' or nazev like '%Wimbledon%' or nazev like '%US open%')"

    tournaments = execute_sql(ORIGINAL_DATABASE_PATH, sql, [first_year, last_year])
    with open('tournaments.csv', 'w', encoding="utf-8") as myfile:
        wr = csv.writer(myfile, lineterminator='\n')
        for tournament in tournaments:
            wr.writerow(tournament)
    return tournaments


def export_matches_from_tournament(tournament, first_year, matches_filename):
    # qualification is considered part of the tournament, however, it is played as best-of-three only and thus
    # not interesting for this case
    sql = "select min(utime) from( \
            (select * from matchids_vlozeno where id_turnaj=?) a \
            join \
            (select * from zapasy) b \
            on  a.id=b.id_matchids \
           ) where max(sety_dom, sety_host)=3"
    utime_of_first_game_of_tournament = execute_sql(ORIGINAL_DATABASE_PATH, sql, tournament[0])[0][0]

    # last round of Wimbledon qualification is sometimes played as best-of-five. Starting times obtained manually
    wimbledon_utimes = (1245657600, 1277114400, 1308567600, 1340620500, 1372070400, 1403520000, 1435574400, 1467024000,
                        1499078400, 1530527700)
    if 'Wimbledon' in tournament[1]:
        utime_of_first_game_of_tournament = wimbledon_utimes[tournament[4] - first_year]

    sql = "select * from( \
                (select * from matchids_vlozeno where id_turnaj=?) a \
                join \
                (select * from zapasy where utime>=? and jiny_vysledek <> 'Canceled') b \
                on  a.id=b.id_matchids) \
            order by utime asc"
    matches = execute_sql(ORIGINAL_DATABASE_PATH, sql, [tournament[0], utime_of_first_game_of_tournament])

    # check for data inconsistencies
    if len(matches) != 127:
        print(len(matches), tournament)

    with open(matches_filename, 'a', encoding="utf-8") as myfile:
        wr = csv.writer(myfile, lineterminator='\n')
        for match in matches:
            wr.writerow(match)

    return matches


def get_matchids(matches):
    matchids = []
    for val in matches:
        for val2 in val:
            matchids.append(val2[0])
    return matchids


def prepare_database(first_year, last_year, bookmaker):
    # select tournaments, export (10 years, 40 tournaments)
    tournaments = export_tournaments(first_year, last_year)
    matches = []

    # iterate over each tournament, select matches (filter out errors), export (40 * 127 = 5 080 matches)
    matches_filename = 'matches.csv'
    if os.path.isfile(matches_filename):
        os.remove(matches_filename)
    for tournament in tournaments:
        matches.append(export_matches_from_tournament(tournament, first_year, matches_filename))

    # get matchids
    matchids = get_matchids(matches)

    # select odds for each match, export (which odds?)

    # create new DB, import data (rename columns?)
    pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Prepares a relevant, lightweight database for the purpose of this project out of a much larger \
        and complex database available to the author.")
    parser.add_argument("--first_year", help="The first tennis season to be considered", default=2009, required=False)
    parser.add_argument("--last_year", help="The last tennis season to be considered", default=2018, required=False)
    parser.add_argument("--bookmaker", help="The bookmaker to be considered", default='pinnacle-sports', required=False)
    parser.add_argument("--original_database_path", help="Path to the original database", required=False)

    args = parser.parse_args()

    first_year = args.first_year
    last_year = args.last_year
    bookmaker = args.bookmaker
    if args.original_database_path is not None:
        ORIGINAL_DATABASE_PATH = args.original_database_path

    prepare_database(first_year, last_year, bookmaker)
