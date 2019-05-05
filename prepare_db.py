# This is a support file used only for one time extraction of a database from a larger and more complex database

import argparse
from datetime import datetime
import os
import re

from database_operations import execute_sql, create_connection, execute_many_sql

ORIGINAL_DATABASE_PATH = 'C://tennis.sqlite'


# function used for removing nested lists in python.
def remove_nestings(l, output):
    for i in l:
        if type(i) == list:
            remove_nestings(i, output)
        else:
            output.append(i)
    return output


def translate_month(text):
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


def get_set_results(match, mat, cur_index):
    for i in range(5):
        if mat[2 * i + cur_index] > mat[2 * i + cur_index + 1]:
            match.append(mat[2 * i + cur_index + 1])
        elif mat[2 * i + cur_index] < mat[2 * i + cur_index + 1]:
            match.append(-mat[2 * i + cur_index])
        else:
            match.append(None)
    return match


def get_matchids(matches):
    matchids = []
    unnested_matches = []
    for val in matches:
        for val2 in val:
            matchids.append(val2[0])
            unnested_matches.append(val2)
    return matchids, unnested_matches


def get_tournaments(first_year, last_year):
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


def get_matches(tournament, first_year):
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

    cleaned_matches = []
    for mat in matches:
        match = [mat[0], mat[2], list(mat[6:12])]
        match = remove_nestings(match, [])
        match[4] = translate_month(match[4])
        # only looser's sets
        cur_index = 12
        match = get_set_results(match, mat, cur_index)
        # other result
        if mat[22] == 'null':
            match.append(None)
        else:
            match.append(mat[22])
        # only looser's tiebreaks
        cur_index = 23
        match = get_set_results(match, mat, cur_index)

        cleaned_matches.append(match)

    return cleaned_matches


def get_odds(bookmaker, matchids_original):
    step_size = 425
    odds = []
    for i in range(0, len(matchids_original), step_size):
        matchids = matchids_original[i:i + step_size]

        questionmarks = '?' * len(matchids)
        sql = f"select home.id as id, home.id_matchids as id_match, home.sazkovka as bookmaker, home.usek as match_part, \
                home.odds_1 as odds_home, away.odds_2 as odds_away, max(home.termin,away.termin) as 'date', \
                max(home.utime,away.utime) as utime from \
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


def prepare_database(first_year, last_year, bookmaker):
    # select tournaments (10 years, 40 tournaments)
    tournaments = get_tournaments(first_year, last_year)
    matches = []

    # iterate over each tournament, select matches, (40 * 127 = 5 080 matches)
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
    execute_sql(new_database_path, sql, None, modifiying=True)

    sql = "CREATE TABLE `matches` ( \
            `id`	INTEGER NOT NULL UNIQUE, \
            `id_tournament` INTEGER NOT NULL, \
            `home`	TEXT NOT NULL, \
            `away`	TEXT NOT NULL, \
            `date`	TEXT NOT NULL, \
            `utime`	INTEGER NOT NULL, \
            `home_sets`	INTEGER, \
            `away_sets`	INTEGER, \
            `set1`	INTEGER, \
            `set2`	INTEGER, \
            `set3`	INTEGER, \
            `set4`	INTEGER, \
            `set5`	INTEGER, \
            `other_result`	TEXT, \
            `tiebreak1`	INTEGER, \
            `tiebreak2`	INTEGER, \
            `tiebreak3`	INTEGER, \
            `tiebreak4`	INTEGER, \
            `tiebreak5`	INTEGER, \
            PRIMARY KEY(`id`) \
            FOREIGN KEY(`id_tournament`) REFERENCES tournaments(`id`) \
        );"

    execute_sql(new_database_path, sql, None, modifiying=True)

    sql = "CREATE TABLE `home_away` ( \
            `id`	INTEGER NOT NULL UNIQUE, \
            `id_match`	INTEGER NOT NULL, \
            `bookmaker`	TEXT NOT NULL, \
            `match_part`	TEXT NOT NULL, \
            `odds_home`	REAL, \
            `odds_away`	REAL, \
            `date`	TEXT NOT NULL, \
            `utime`	INTEGER NOT NULL, \
            PRIMARY KEY(`id`) \
            FOREIGN KEY(`id_match`) REFERENCES matches(`id`) \
        );"

    execute_sql(new_database_path, sql, None, modifiying=True)

    # import data
    questionmarks = '?' * len(tournaments[0])
    sql = f"INSERT INTO tournaments ( id,name,competition_type,match_type,year,country,gender,surface,prize_money,\
            prize_money_currency,tournament_link) VALUES ({','.join(questionmarks)})"
    execute_many_sql(new_database_path, sql, tournaments, True)

    questionmarks = '?' * len(matches[0])
    sql = f"INSERT INTO matches (id,id_tournament,home,away,date,utime,home_sets,away_sets,set1,set2,set3,set4,set5,\
                other_result,tiebreak1,tiebreak2,tiebreak3,tiebreak4,tiebreak5) VALUES ({','.join(questionmarks)})"
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

    end_time = datetime.now()
    print(f"Duration: {(end_time - start_time)}")
