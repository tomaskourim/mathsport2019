# This is a support file used only for one time extraction of a database from a larger and more complex database

import argparse
import logging
import os
import re
from datetime import datetime
from typing import Tuple

from database_operations import execute_sql, create_connection, execute_many_sql

ORIGINAL_DATABASE_PATH = 'C://tennis//tennis.sqlite'


# function used for removing nested lists in python.
def remove_nestings(l: list, output: list) -> list:
    for i in l:
        if type(i) == list:
            remove_nestings(i, output)
        else:
            output.append(i)
    return output


def translate_month(text: str) -> str:
    text = text.replace('Led', 'Jan')
    text = text.replace('Úno', 'Feb')
    text = text.replace('Bře', 'Mar')
    text = text.replace('Dub', 'Apr')
    text = text.replace('Kvě', 'May')
    text = text.replace('Čer', 'Jun')
    text = text.replace('Čvc', 'Jul')
    text = text.replace('Srp', 'Aug')
    text = text.replace('Zář', 'Sep')
    text = text.replace('Říj', 'Oct')
    text = text.replace('Lis', 'Nov')
    text = text.replace('Pro', 'Dec')
    return text


def get_matchids(matches: list) -> Tuple[list, list]:
    matchids = []
    unnested_matches = []
    for val in matches:
        for val2 in val:
            matchids.append(val2[0])
            unnested_matches.append(val2)
    return matchids, unnested_matches


def get_tournaments(first_year: int, last_year: int) -> list:
    sql = "select * from turnaje where pohlavi=\'men\' and typ=\'dvouhra\' and rok>=? and rok<=? and (nazev like \
    '%Australian open%' or nazev like '%French open%' or nazev like '%Wimbledon%' or nazev like '%US open%')"

    tournaments = execute_sql(ORIGINAL_DATABASE_PATH, sql, [first_year, last_year])
    cleaned_tournaments = []
    for tournament in tournaments:
        tour = list(tournament[:len(tournament) - 1])
        tour[3] = "singles"
        tour[1] = re.sub('ATP ', '', tour[1])
        tour[1] = re.sub('\\d*', '', tour[1])
        tour[1] = tour[1].strip()
        cleaned_tournaments.append(tour)

    return cleaned_tournaments


def get_matches(tournament: list, first_year: int) -> list:
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
                        1499078400, 1530527700, 1561975500)
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
        logging.error(len(matches), tournament)

    cleaned_matches = []
    for mat in matches:
        match = [mat[0], mat[2], list(mat[6:22])]  # id, tournament, players, time, match and sets results
        match = remove_nestings(match, [])
        match[4] = translate_month(match[4])
        # other result
        if mat[22] == 'null':
            match.append(None)
        else:
            match.append(mat[22])
        match.append(list(mat[23:33]))  # tiebreak results
        match = remove_nestings(match, [])

        cleaned_matches.append(match)

    return cleaned_matches


def get_odds(bookmaker: str, matchids_original: list) -> list:
    step_size = 425
    odds = []
    for i in range(0, len(matchids_original), step_size):
        matchids = matchids_original[i:i + step_size]

        questionmarks = '?' * len(matchids)
        sql = f"select home.id as id, home.id_matchids as id_match, home.sazkovka as bookmaker, \
                home.usek as match_part, home.odds_1 as odds_home, away.odds_2 as odds_away, \
                max(home.termin,away.termin) as 'date', max(home.utime,away.utime) as utime from \
                (select * from home_away \
                    where \
                        (usek='fulltime' or usek='1.set') and \
                        (aktivni='true' or aktivni='false') and \
                        sazkovka=? and \
                        id_matchids in ({','.join(questionmarks)}) and \
                        odds_1 not null \
                ) home \
                inner join \
                (select * from home_away \
                    where \
                        (usek='fulltime' or usek='1.set') and \
                        (aktivni='true' or aktivni='false') and \
                        sazkovka=? and \
                        id_matchids in ({','.join(questionmarks)}) and \
                        odds_2 not null \
                ) away \
                on home.id_matchids=away.id_matchids and home.usek=away.usek"

        params = remove_nestings([bookmaker, matchids, bookmaker, matchids], [])
        odds.append(execute_sql(ORIGINAL_DATABASE_PATH, sql, params))

    cleaned_odds = []
    for oddpart in odds:
        for oddrow in oddpart:
            odd = list(oddrow)
            odd[6] = translate_month(odd[6])
            cleaned_odds.append(odd)

    return cleaned_odds


def prepare_database(first_year: int, last_year: int, bookmaker: str):
    # select tournaments (12 years, 47 tournaments - no Wimbledon in 2020)
    tournaments = get_tournaments(first_year, last_year)
    matches = []

    # iterate over each tournament, select matches, (47 * 127 = 5 969 matches)
    for tournament in tournaments:
        matches.append(get_matches(tournament, first_year))

    # get matchids
    matchids, matches = get_matchids(matches)

    # select odds for each match
    odds = get_odds(bookmaker, matchids)

    # create new DB
    new_database_path = "mathsport2019.sqlite"
    if os.path.isfile(new_database_path):
        os.remove(new_database_path)
    create_connection(new_database_path)

    sql = "CREATE TABLE `tournaments` ( \
            `id`	INTEGER NOT NULL UNIQUE, \
            `name`	TEXT NOT NULL, \
            `competition_type`	TEXT NOT NULL, \
            `match_type`	TEXT NOT NULL, \
            `year`	INTEGER NOT NULL, \
            `country`	TEXT NOT NULL, \
            `gender`	TEXT NOT NULL, \
            `surface`	TEXT, \
            `prize_money`	INTEGER, \
            `prize_money_currency`	TEXT, \
            `tournament_link`	TEXT NOT NULL, \
            PRIMARY KEY(`id`) \
        );"
    execute_sql(new_database_path, sql, None, modifying=True)

    sql = "CREATE TABLE `matches` ( \
            `id`	INTEGER NOT NULL UNIQUE, \
            `id_tournament` INTEGER NOT NULL, \
            `home`	TEXT NOT NULL, \
            `away`	TEXT NOT NULL, \
            `date`	TEXT NOT NULL, \
            `utime`	INTEGER NOT NULL, \
            `home_sets`	INTEGER, \
            `away_sets`	INTEGER, \
            `set1home`	INTEGER, \
            `set1away`	INTEGER, \
            `set2home`	INTEGER, \
            `set2away`	INTEGER, \
            `set3home`	INTEGER, \
            `set3away`	INTEGER, \
            `set4home`	INTEGER, \
            `set4away`	INTEGER, \
            `set5home`	INTEGER, \
            `set5away`	INTEGER, \
            `other_result`	TEXT, \
            `tiebreak1home`	INTEGER, \
            `tiebreak1away`	INTEGER, \
            `tiebreak2home`	INTEGER, \
            `tiebreak2away`	INTEGER, \
            `tiebreak3home`	INTEGER, \
            `tiebreak3away`	INTEGER, \
            `tiebreak4home`	INTEGER, \
            `tiebreak4away`	INTEGER, \
            `tiebreak5home`	INTEGER, \
            `tiebreak5away`	INTEGER, \
            PRIMARY KEY(`id`), \
            FOREIGN KEY(`id_tournament`) REFERENCES tournaments(`id`) \
        );"

    execute_sql(new_database_path, sql, None, modifying=True)

    sql = "CREATE TABLE `home_away` ( \
            `id`	INTEGER NOT NULL UNIQUE, \
            `id_match`	INTEGER NOT NULL, \
            `bookmaker`	TEXT NOT NULL, \
            `match_part`	TEXT NOT NULL, \
            `odds_home`	REAL, \
            `odds_away`	REAL, \
            `date`	TEXT NOT NULL, \
            `utime`	INTEGER NOT NULL, \
            PRIMARY KEY(`id`), \
            FOREIGN KEY(`id_match`) REFERENCES matches(`id`) \
        );"

    execute_sql(new_database_path, sql, None, modifying=True)

    # import data
    questionmarks = '?' * len(tournaments[0])
    sql = f"INSERT INTO tournaments ( id,name,competition_type,match_type,year,country,gender,surface,prize_money,\
            prize_money_currency,tournament_link) VALUES ({','.join(questionmarks)})"
    execute_many_sql(new_database_path, sql, tournaments, True)

    questionmarks = '?' * len(matches[0])
    sql = f"INSERT INTO matches (id,id_tournament,home,away,date,utime,home_sets,away_sets,\
                set1home,set1away,set2home,set2away,set3home,set3away,set4home,set4away,set5home,set5away,\
                other_result,tiebreak1home,tiebreak1away,tiebreak2home,tiebreak2away,tiebreak3home,tiebreak3away,\
                tiebreak4home,tiebreak4away,tiebreak5home,tiebreak5away) VALUES ({','.join(questionmarks)})"
    execute_many_sql(new_database_path, sql, matches, True)

    questionmarks = '?' * len(odds[0])
    sql = f"INSERT INTO home_away (id,id_match,bookmaker,match_part,odds_home,odds_away,date,utime) \
            VALUES ({','.join(questionmarks)})"
    execute_many_sql(new_database_path, sql, odds, True)

    pass


if __name__ == '__main__':
    start_time = datetime.now()

    parser = argparse.ArgumentParser(
        description="Prepares a relevant, lightweight database for the purpose of this project out of a much larger \
        and complex database available to the author.")
    parser.add_argument("--first_year", help="The first tennis season to be considered", default=2009, required=False)
    parser.add_argument("--last_year", help="The last tennis season to be considered", default=2020, required=False)
    parser.add_argument("--bookmaker", help="The bookmaker to be considered", default='pinnacle-sports', required=False)
    parser.add_argument("--original_database_path", help="Path to the original database", required=False)

    args = parser.parse_args()

    input_first_year = args.first_year
    input_last_year = args.last_year
    input_bookmaker = args.bookmaker
    if args.original_database_path is not None:
        ORIGINAL_DATABASE_PATH = args.original_database_path

    prepare_database(input_first_year, input_last_year, input_bookmaker)

    end_time = datetime.now()
    logging.info(f"Duration: {(end_time - start_time)}")
