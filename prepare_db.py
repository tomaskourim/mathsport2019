# This is a support file used only for one time extraction of a database from a larger and more complex database

import argparse
import csv

from database_operations import execute_sql


def export_tournaments(first_year, last_year, original_database_path):
    sql = "select * from turnaje where pohlavi=\'men\' and typ=\'dvouhra\' and rok>=? and rok<=? and (nazev like \
    '%Australian open%' or nazev like '%French open%' or nazev like '%Wimbledon%' or nazev like '%US open%')"

    tournaments = execute_sql(original_database_path, sql, [first_year, last_year])
    with open('tournaments.csv', 'w', encoding="utf-8") as myfile:
        wr = csv.writer(myfile, lineterminator='\n')
        for tournament in tournaments:
            wr.writerow(tournament)
    return tournaments


def export_matches_from_tournament(tournament):
    sql = ""


def prepare_database(first_year, last_year, bookmaker, original_database_path):
    # select tournaments, export (10 years, 40 tournaments)
    tournaments = export_tournaments(first_year, last_year, original_database_path)

    # iterate over each tournament, select matches (filter out errors), export (40 * 127 = 5 080 matches)
    for tournament in tournaments:
        export_matches_from_tournament(tournament)
    
    
    # select odds for each match, export (which odds?)ø
    # create new DB, import data (rename columns?)
    pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Prepares a relevant, lightweight database for the purpose of this project out of a much larger \
        and complex database available to the author.")
    parser.add_argument("--first_year", help="The first tennis season to be considered", default=2009, required=False)
    parser.add_argument("--last_year", help="The last tennis season to be considered", default=2018, required=False)
    parser.add_argument("--bookmaker", help="The bookmaker to be considered", default='pinnacle-sports', required=False)
    parser.add_argument("--original_database_path", help="Path to the original database", default='C://tennis.sqlite',
                        required=False)

    args = parser.parse_args()

    first_year = args.first_year
    last_year = args.last_year
    bookmaker = args.bookmaker
    original_database_path = args.original_database_path

    prepare_database(first_year, last_year, bookmaker, original_database_path)
