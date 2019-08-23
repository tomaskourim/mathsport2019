-- bets overview
SELECT home, away, name AS tournament_name, sex, type, surface, start_time_utc, bet_type, match_part, odd, probability,
    result
FROM (SELECT *
      FROM bet
               JOIN matches_bookmaker mb
      ON bet.bookmaker_id = mb.bookmaker_id AND bet.match_bookmaker_id = mb.match_bookmaker_id
               JOIN matches m ON mb.match_id = m.id
               JOIN tournament t ON m.tournament_id = t.id) AS r
ORDER BY start_time_utc DESC;

-- odds
SELECT home, away, name AS tournament_name, sex, type, surface, start_time_utc, odds_type, match_part, odd1, odd2
FROM (
    SELECT *
    FROM odds
             JOIN matches_bookmaker mb
    ON odds.bookmaker_id = mb.bookmaker_id AND odds.match_bookmaker_id = mb.match_bookmaker_id
             JOIN matches m ON mb.match_id = m.id
             JOIN tournament t ON m.tournament_id = t.id) AS r
WHERE start_time_utc >= '2019-08-22 12:40:00.000000'
ORDER BY start_time_utc DESC, home, match_part;

-- inplay
SELECT home, away, name AS tournament_name, sex, type, surface, start_time_utc
FROM (
    SELECT *
    FROM inplay
             JOIN matches_bookmaker mb
    ON inplay.bookmaker_id = mb.bookmaker_id AND inplay.match_bookmaker_id = mb.match_bookmaker_id
             JOIN matches m ON mb.match_id = m.id
             JOIN tournament t ON m.tournament_id = t.id) AS r
ORDER BY start_time_utc DESC, home;