-- matches to start
SELECT match_bookmaker_id
FROM (SELECT *
      FROM matches
      WHERE start_time_utc > '2020-01-23 20:00:00.000000' AND
          start_time_utc < '2020-01-23 23:00:00.000000') AS matches
         JOIN matches_bookmaker ON matches.id = match_id EXCEPT
SELECT match_bookmaker_id
FROM inplay;

-- matches overview
SELECT home, away, start_time_utc, name, sex, type, surface, year
FROM matches
         JOIN tournament t ON matches.tournament_id = t.id
WHERE start_time_utc > '2020-01-24 15:00:00.000000' AND name = 'ATP Australian Open' AND type = 'singles'
ORDER BY start_time_utc;

-- bets overview
SELECT book_id, home, away, name AS tournament_name, start_time_utc, bet_type, result, match_part, odd, probability,
    odd_corrected, result_corrected, utc_time_recorded
FROM (SELECT *, mb.match_bookmaker_id AS book_id
      FROM bet
               JOIN matches_bookmaker mb
      ON bet.bookmaker_id = mb.bookmaker_id AND bet.match_bookmaker_id = mb.match_bookmaker_id
               JOIN matches m ON mb.match_id = m.id
               JOIN tournament t ON m.tournament_id = t.id) AS r
WHERE start_time_utc >= '2020-01-23 20:00:00.000000'
ORDER BY utc_time_recorded DESC, book_id, match_part;

-- odds
SELECT book_id, home, away, match_part, odd1, odd2, name AS tournament_name, start_time_utc, odds_type,
    utc_time_recorded
FROM (
    SELECT *, mb.match_bookmaker_id AS book_id
    FROM odds
             JOIN matches_bookmaker mb
    ON odds.bookmaker_id = mb.bookmaker_id AND odds.match_bookmaker_id = mb.match_bookmaker_id
             JOIN matches m ON mb.match_id = m.id
             JOIN tournament t ON m.tournament_id = t.id) AS r
WHERE start_time_utc >= '2020-01-23 20:00:00.000000'
ORDER BY tournament_name, sex, type, book_id, start_time_utc DESC, match_part;

-- match course
SELECT match_bookmaker_id AS book_id, mb.match_id, home, away, result, name AS tournament_name, start_time_utc,
    set_number,
    utc_time_recorded
FROM match_course
         JOIN matches m ON match_course.match_id = m.id
         JOIN matches_bookmaker mb ON m.id = mb.match_id
         JOIN tournament t ON m.tournament_id = t.id
WHERE start_time_utc > '2020-01-19 20:00:00.000000'
ORDER BY name, sex, type, match_bookmaker_id, start_time_utc, match_bookmaker_id, set_number;

--incorrect results
SELECT *
FROM (
    SELECT match_id, max(sets_won) AS winning_sets
    FROM (
        SELECT match_id, result, count(*) AS sets_won
        FROM match_course
        WHERE utc_time_recorded > '2020-01-19 20:00:00.000000'
        GROUP BY match_id, result) AS gid
    GROUP BY match_id) AS gwin
WHERE winning_sets != 3;

--missing odds

--missing match course

-- inplay
SELECT book_id, home, away, name AS tour_name, sex, type, surface, start_time_utc, utc_time_recorded
FROM (
    SELECT *, mb.match_bookmaker_id AS book_id
    FROM inplay
             JOIN matches_bookmaker mb
    ON inplay.bookmaker_id = mb.bookmaker_id AND inplay.match_bookmaker_id = mb.match_bookmaker_id
             JOIN matches m ON mb.match_id = m.id
             JOIN tournament t ON m.tournament_id = t.id) AS r
ORDER BY book_id, start_time_utc DESC, home;


-- results and expected results
SELECT sum(probability) AS expected_wins, sum(CASE WHEN result_corrected IS TRUE THEN 1 ELSE 0 END) AS actual_wins
FROM bet
WHERE utc_time_recorded >= '2020-01-23 20:00:00.000000' AND result_corrected NOTNULL;

--------------------------------------------------------------
--theoretical results (if odds were as algorithms expected)
-- edge
SELECT *, probability - 1 / odd AS edge
FROM bet
WHERE utc_time_recorded >= '2020-01-23 20:00:00.000000' AND result_corrected NOTNULL
ORDER BY edge DESC;

-- expected money wins and actual wins - naive betting summed
SELECT sum(probability * (odd - 1) - (1 - probability)) AS expected_win,
    sum(CASE WHEN result_corrected IS TRUE THEN odd - 1 ELSE -1 END) AS win
FROM bet
WHERE utc_time_recorded >= '2020-01-23 20:00:00.000000' AND result_corrected NOTNULL;

-- expected money wins and actual wins - probability betting summed
SELECT sum(probability * (probability * odd - probability) - (1 - probability) * probability) AS expected_win,
    sum(CASE WHEN result_corrected IS TRUE
                 THEN probability * odd - probability
             ELSE -probability END) AS win
FROM bet
WHERE utc_time_recorded >= '2020-01-23 20:00:00.000000' AND result_corrected NOTNULL;

-- expected money wins and actual wins - 1/odds betting summed
SELECT sum(probability * (1 - 1 / odd) - (1 - probability) * (1 / odd)) AS expected_win,
    sum(CASE WHEN result_corrected IS TRUE
                 THEN (1 - 1 / odd)
             ELSE (-1 / odd) END) AS win
FROM bet
WHERE utc_time_recorded >= '2020-01-23 20:00:00.000000' AND result_corrected NOTNULL;

--actual results (actual bet odds)
-- edge
SELECT *, probability - 1 / actual_odd AS edge
FROM (
    SELECT *, CASE WHEN odd_corrected NOTNULL THEN odd_corrected ELSE odd END AS actual_odd
    FROM bet) AS bet_with_actual_odds
WHERE utc_time_recorded >= '2020-01-23 20:00:00.000000' AND result_corrected NOTNULL
ORDER BY edge DESC;

-- expected money wins and actual wins - naive betting summed
SELECT sum(probability * (actual_odd - 1) - (1 - probability)) AS expected_win,
    sum(CASE WHEN result_corrected IS TRUE THEN actual_odd - 1 ELSE -1 END) AS win
FROM (
    SELECT *, CASE WHEN odd_corrected NOTNULL THEN odd_corrected ELSE odd END AS actual_odd
    FROM bet) AS bet_with_actual_odds
WHERE utc_time_recorded >= '2020-01-23 20:00:00.000000' AND result_corrected NOTNULL;

-- expected money wins and actual wins - probability betting summed
SELECT sum(probability * (probability * actual_odd - probability) - (1 - probability) * probability) AS expected_win,
    sum(CASE WHEN result_corrected IS TRUE
                 THEN probability * actual_odd - probability
             ELSE -probability END) AS win
FROM (
    SELECT *, CASE WHEN odd_corrected NOTNULL THEN odd_corrected ELSE odd END AS actual_odd
    FROM bet) AS bet_with_actual_odds
WHERE utc_time_recorded >= '2020-01-23 20:00:00.000000' AND result_corrected NOTNULL;

-- expected money wins and actual wins - 1/odds betting summed
SELECT sum(probability * (1 - 1 / actual_odd) - (1 - probability) * (1 / actual_odd)) AS expected_win,
    sum(CASE WHEN result_corrected IS TRUE
                 THEN (1 - 1 / actual_odd)
             ELSE (-1 / actual_odd) END) AS win
FROM (
    SELECT *, CASE WHEN odd_corrected NOTNULL THEN odd_corrected ELSE odd END AS actual_odd
    FROM bet) AS bet_with_actual_odds
WHERE utc_time_recorded >= '2020-01-23 20:00:00.000000' AND result_corrected NOTNULL;
