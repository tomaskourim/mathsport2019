-- match detail
SELECT *
FROM matches_bookmaker
         JOIN matches m ON matches_bookmaker.match_id = m.id
WHERE match_bookmaker_id = '3787900';

SELECT DISTINCT home, away, start_time_utc, name
FROM match_course
         JOIN matches m ON match_course.match_id = m.id
         JOIN tournament t ON m.tournament_id = t.id
WHERE name IN ('ATP Australian Open', 'ATP US Open', 'ATP French Open', 'ATP Wimbledon') AND
    utc_time_recorded > '2021-02-10 22:00:00.000000'
GROUP BY match_id, home, away, start_time_utc, name
ORDER BY start_time_utc;

-- matches to start
SELECT home, away, start_time_utc, match_bookmaker_id
FROM matches
         JOIN matches_bookmaker mb ON matches.id = mb.match_id
WHERE match_bookmaker_id IN (SELECT match_bookmaker_id
                             FROM (SELECT *
                                   FROM matches
                                   WHERE start_time_utc > '2021-02-08 16:00:00.000000' AND
                                       start_time_utc < '2021-02-09 08:00:00.000000') AS matches
                                      JOIN matches_bookmaker ON matches.id = match_id
                                      JOIN
                             tournament ON matches.tournament_id = tournament.id
                             WHERE name IN ('ATP Australian Open', 'ATP US Open', 'ATP French Open',
                                            'ATP Wimbledon') AND sex = 'men' AND
                                 type = 'singles'
                                 EXCEPT
                             SELECT match_bookmaker_id
                             FROM inplay);

-- matches overview
SELECT home, away, start_time_utc, name, sex, type, surface, year
FROM matches
         JOIN tournament t ON matches.tournament_id = t.id
WHERE start_time_utc > '2021-02-10 22:00:00.000000' AND
    name IN ('ATP Australian Open', 'ATP US Open', 'ATP French Open', 'ATP Wimbledon') AND sex = 'men' AND
    type = 'singles'
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
WHERE start_time_utc >= '2021-02-10 22:00:00.000000'
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
WHERE start_time_utc >= '2021-02-10 22:00:00.000000'
ORDER BY tournament_name, sex, type, book_id, start_time_utc DESC, match_part;

-- match course
SELECT match_bookmaker_id AS book_id, mb.match_id, home, away, result, name AS tournament_name, start_time_utc,
    set_number,
    utc_time_recorded
FROM match_course
         JOIN matches m ON match_course.match_id = m.id
         JOIN matches_bookmaker mb ON m.id = mb.match_id
         JOIN tournament t ON m.tournament_id = t.id
WHERE start_time_utc > '2021-02-10 22:00:00.000000'
ORDER BY name, sex, type, match_bookmaker_id, start_time_utc, match_bookmaker_id, set_number;

--incorrect results
SELECT match_id, match_bookmaker_id, home, away, start_time_utc
FROM matches_bookmaker
         JOIN matches m ON matches_bookmaker.match_id = m.id
WHERE match_bookmaker_id IN (
    SELECT match_bookmaker_id
    FROM (
        SELECT match_id, max(sets_won) AS winning_sets
        FROM (
            SELECT match_id, result, count(*) AS sets_won
            FROM match_course
            WHERE utc_time_recorded > '2021-02-10 22:00:00.000000'
            GROUP BY match_id, result) AS gid
        GROUP BY match_id) AS gwin
             JOIN matches ON gwin.match_id = matches.id
             JOIN matches_bookmaker mb ON matches.id = mb.match_id
    WHERE winning_sets != 3 EXCEPT
    SELECT match_bookmaker_id
    FROM inplay)
ORDER BY match_bookmaker_id;

--missing odds
SELECT *
FROM (SELECT *,
          CASE
              WHEN match_part = 'set1'
                  THEN 1
              WHEN match_part = 'set2'
                  THEN 2
              WHEN match_part = 'set3'
                  THEN 3
              WHEN match_part = 'set4'
                  THEN 4
              WHEN match_part = 'set5'
                  THEN 5
              END AS set_number
      FROM odds) AS o
         RIGHT JOIN
(SELECT *
 FROM match_course
          JOIN matches_bookmaker ON match_course.match_id = matches_bookmaker.match_id
          JOIN matches m ON match_course.match_id = m.id
) AS mc
ON mc.bookmaker_id = o.bookmaker_id AND mc.match_bookmaker_id = o.match_bookmaker_id AND mc.set_number = o.set_number
WHERE mc.start_time_utc > '2021-02-10 22:00:00.000000' AND o.id ISNULL;

--missing match course
SELECT match_id, match_bookmaker_id, home, away, start_time_utc
FROM matches_bookmaker
         JOIN matches m ON matches_bookmaker.match_id = m.id
WHERE match_bookmaker_id IN (
    SELECT o.match_bookmaker_id AS match_bookmaker_id
    FROM (SELECT odds.*, m2.start_time_utc,
              CASE
                  WHEN match_part = 'set1'
                      THEN 1
                  WHEN match_part = 'set2'
                      THEN 2
                  WHEN match_part = 'set3'
                      THEN 3
                  WHEN match_part = 'set4'
                      THEN 4
                  WHEN match_part = 'set5'
                      THEN 5
                  END AS set_number
          FROM odds
                   JOIN matches_bookmaker mb
          ON odds.bookmaker_id = mb.bookmaker_id AND odds.match_bookmaker_id = mb.match_bookmaker_id
                   JOIN matches m2 ON mb.match_id = m2.id) AS o
             LEFT JOIN
    (SELECT *
     FROM match_course
              JOIN matches_bookmaker ON match_course.match_id = matches_bookmaker.match_id
    ) AS mc
    ON mc.bookmaker_id = o.bookmaker_id AND mc.match_bookmaker_id = o.match_bookmaker_id
            AND mc.set_number = o.set_number
    WHERE start_time_utc > '2021-02-10 22:00:00.000000' AND mc.utc_time_recorded ISNULL EXCEPT
    SELECT match_bookmaker_id
    FROM inplay)
ORDER BY match_bookmaker_id;

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
WHERE utc_time_recorded >= '2021-02-10 22:00:00.000000' AND result_corrected NOTNULL;

--------------------------------------------------------------
--theoretical results (if odds were as algorithms expected)
-- edge
SELECT *, probability - 1 / odd AS edge
FROM bet
WHERE utc_time_recorded >= '2021-02-10 22:00:00.000000' AND result_corrected NOTNULL
ORDER BY edge DESC;

-- expected money wins and actual wins - naive betting summed
SELECT sum(probability * (odd - 1) - (1 - probability)) AS expected_win,
    sum(CASE WHEN result_corrected IS TRUE THEN odd - 1 ELSE -1 END) AS win
FROM bet
WHERE utc_time_recorded >= '2021-02-10 22:00:00.000000' AND result_corrected NOTNULL;

-- expected money wins and actual wins - probability betting summed
SELECT sum(probability * (probability * odd - probability) - (1 - probability) * probability) AS expected_win,
    sum(CASE WHEN result_corrected IS TRUE
                 THEN probability * odd - probability
             ELSE -probability END) AS win
FROM bet
WHERE utc_time_recorded >= '2021-02-10 22:00:00.000000' AND result_corrected NOTNULL;

-- expected money wins and actual wins - 1/odds betting summed
SELECT sum(probability * (1 - 1 / odd) - (1 - probability) * (1 / odd)) AS expected_win,
    sum(CASE WHEN result_corrected IS TRUE
                 THEN (1 - 1 / odd)
             ELSE (-1 / odd) END) AS win
FROM bet
WHERE utc_time_recorded >= '2021-02-10 22:00:00.000000' AND result_corrected NOTNULL;

--actual results (actual bet odds)
-- edge
SELECT *, probability - 1 / actual_odd AS edge
FROM (
    SELECT *, CASE WHEN odd_corrected NOTNULL THEN odd_corrected ELSE odd END AS actual_odd
    FROM bet) AS bet_with_actual_odds
WHERE utc_time_recorded >= '2021-02-10 22:00:00.000000' AND result_corrected NOTNULL
ORDER BY edge DESC;

-- expected money wins and actual wins - naive betting summed
SELECT sum(probability * (actual_odd - 1) - (1 - probability)) AS expected_win,
    sum(CASE WHEN result_corrected IS TRUE THEN actual_odd - 1 ELSE -1 END) AS win
FROM (
    SELECT *, CASE WHEN odd_corrected NOTNULL THEN odd_corrected ELSE odd END AS actual_odd
    FROM bet) AS bet_with_actual_odds
WHERE utc_time_recorded >= '2021-02-10 22:00:00.000000' AND result_corrected NOTNULL;

-- expected money wins and actual wins - probability betting summed
SELECT sum(probability * (probability * actual_odd - probability) - (1 - probability) * probability) AS expected_win,
    sum(CASE WHEN result_corrected IS TRUE
                 THEN probability * actual_odd - probability
             ELSE -probability END) AS win
FROM (
    SELECT *, CASE WHEN odd_corrected NOTNULL THEN odd_corrected ELSE odd END AS actual_odd
    FROM bet) AS bet_with_actual_odds
WHERE utc_time_recorded >= '2021-02-10 22:00:00.000000' AND result_corrected NOTNULL;

-- expected money wins and actual wins - 1/odds betting summed
SELECT sum(probability * (1 - 1 / actual_odd) - (1 - probability) * (1 / actual_odd)) AS expected_win,
    sum(CASE WHEN result_corrected IS TRUE
                 THEN (1 - 1 / actual_odd)
             ELSE (-1 / actual_odd) END) AS win
FROM (
    SELECT *, CASE WHEN odd_corrected NOTNULL THEN odd_corrected ELSE odd END AS actual_odd
    FROM bet) AS bet_with_actual_odds
WHERE utc_time_recorded >= '2021-02-10 22:00:00.000000' AND result_corrected NOTNULL;
