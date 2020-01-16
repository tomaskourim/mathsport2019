-- matches overview
SELECT home, away, start_time_utc, name, sex, type, surface, year
FROM matches
         JOIN tournament t ON matches.tournament_id = t.id
WHERE start_time_utc > '2020-01-01 00:00:00.000000'
ORDER BY name, type, start_time_utc;

-- bets overview
SELECT book_id, home, away, name AS tournament_name, sex, type, surface, start_time_utc, bet_type, match_part, odd,
    probability, result, utc_time_recorded
FROM (SELECT *, mb.match_bookmaker_id AS book_id
      FROM bet
               JOIN matches_bookmaker mb
      ON bet.bookmaker_id = mb.bookmaker_id AND bet.match_bookmaker_id = mb.match_bookmaker_id
               JOIN matches m ON mb.match_id = m.id
               JOIN tournament t ON m.tournament_id = t.id) AS r
WHERE start_time_utc >= '2020-01-01 00:00:00.000000'
ORDER BY utc_time_recorded DESC, book_id, match_part;

-- odds
SELECT book_id, home, away, name AS tournament_name, sex, type, surface, start_time_utc, odds_type, match_part, odd1,
    odd2
FROM (
    SELECT *, mb.match_bookmaker_id AS book_id
    FROM odds
             JOIN matches_bookmaker mb
    ON odds.bookmaker_id = mb.bookmaker_id AND odds.match_bookmaker_id = mb.match_bookmaker_id
             JOIN matches m ON mb.match_id = m.id
             JOIN tournament t ON m.tournament_id = t.id) AS r
WHERE start_time_utc >= '2020-01-01 00:00:00.000000'
ORDER BY start_time_utc, book_id, match_part;

-- inplay
SELECT book_id, home, away, name AS tournament_name, sex, type, surface, start_time_utc, utc_time_recorded
FROM (
    SELECT *, mb.match_bookmaker_id AS book_id
    FROM inplay
             JOIN matches_bookmaker mb
    ON inplay.bookmaker_id = mb.bookmaker_id AND inplay.match_bookmaker_id = mb.match_bookmaker_id
             JOIN matches m ON mb.match_id = m.id
             JOIN tournament t ON m.tournament_id = t.id) AS r
ORDER BY start_time_utc DESC, home;

-- match course
SELECT match_bookmaker_id, home, away, start_time_utc, set_number, result, utc_time_recorded
FROM match_course
         JOIN matches m ON match_course.match_id = m.id
         JOIN matches_bookmaker mb ON m.id = mb.match_id
WHERE start_time_utc > '2020-01-01 00:00:00.000000'
ORDER BY start_time_utc, match_bookmaker_id, set_number;
