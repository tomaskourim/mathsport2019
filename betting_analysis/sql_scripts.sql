-- US Open men single matches - odds
SELECT home, away, start_time_utc, match_part, odd1, odd2, utc_time_recorded
FROM matches
         JOIN tournament t ON matches.tournament_id = t.id
         JOIN matches_bookmaker mb ON matches.id = mb.match_id
         JOIN odds o ON mb.bookmaker_id = o.bookmaker_id AND mb.match_bookmaker_id = o.match_bookmaker_id
WHERE name = 'US Open' AND sex = 'men' AND type = 'singles'
ORDER BY start_time_utc, home, match_part;

-- US Open men single matches - bets
SELECT home, away, start_time_utc, bet_type, match_part, odd, probability, result, utc_time_recorded
FROM matches
         JOIN tournament t ON matches.tournament_id = t.id
         JOIN matches_bookmaker mb ON matches.id = mb.match_id
         JOIN bet b ON mb.bookmaker_id = b.bookmaker_id AND mb.match_bookmaker_id = b.match_bookmaker_id
WHERE name = 'US Open' AND sex = 'men' AND type = 'singles' AND result NOTNULL
ORDER BY utc_time_recorded;


-- US Open men single matches - results and expected results
SELECT sum(probability) AS expected_wins, sum(CASE WHEN result IS TRUE THEN 1 ELSE 0 END) AS actual_wins
FROM matches
         JOIN tournament t ON matches.tournament_id = t.id
         JOIN matches_bookmaker mb ON matches.id = mb.match_id
         JOIN bet b ON mb.bookmaker_id = b.bookmaker_id AND mb.match_bookmaker_id = b.match_bookmaker_id
WHERE name = 'US Open' AND sex = 'men' AND type = 'singles' AND result NOTNULL;

-- expected money wins and actual wins - naive betting
SELECT home, away, bet_type, match_part, odd, probability, result,
    probability * (odd - 1) - (1 - probability) AS expected_win,
    CASE WHEN result IS TRUE THEN odd - 1 ELSE -1 END AS win
FROM matches
         JOIN tournament t ON matches.tournament_id = t.id
         JOIN matches_bookmaker mb ON matches.id = mb.match_id
         JOIN bet b ON mb.bookmaker_id = b.bookmaker_id AND mb.match_bookmaker_id = b.match_bookmaker_id
WHERE name = 'US Open' AND sex = 'men' AND type = 'singles' AND result NOTNULL
ORDER BY utc_time_recorded;


-- expected money wins and actual wins - naive betting summed
SELECT sum(probability * (odd - 1) - (1 - probability)) AS expected_win,
    sum(CASE WHEN result IS TRUE THEN odd - 1 ELSE -1 END) AS win
FROM matches
         JOIN tournament t ON matches.tournament_id = t.id
         JOIN matches_bookmaker mb ON matches.id = mb.match_id
         JOIN bet b ON mb.bookmaker_id = b.bookmaker_id AND mb.match_bookmaker_id = b.match_bookmaker_id
WHERE name = 'US Open' AND sex = 'men' AND type = 'singles' AND result NOTNULL;


-- expected money wins and actual wins - advanced betting
SELECT home, away, bet_type, match_part, odd, probability, result,
    probability * (probability * odd - probability) - (1 - probability) * probability AS expected_win,
    CASE WHEN result IS TRUE
             THEN probability * odd - probability
         ELSE -probability END AS win
FROM matches
         JOIN tournament t ON matches.tournament_id = t.id
         JOIN matches_bookmaker mb ON matches.id = mb.match_id
         JOIN bet b ON mb.bookmaker_id = b.bookmaker_id AND mb.match_bookmaker_id = b.match_bookmaker_id
WHERE name = 'US Open' AND sex = 'men' AND type = 'singles' AND result NOTNULL
ORDER BY utc_time_recorded;


-- expected money wins and actual wins - advanced betting summed
SELECT sum(probability * (probability * odd - probability) - (1 - probability) * probability) AS expected_win,
    sum(CASE WHEN result IS TRUE
                 THEN probability * odd - probability
             ELSE -probability END) AS win
FROM matches
         JOIN tournament t ON matches.tournament_id = t.id
         JOIN matches_bookmaker mb ON matches.id = mb.match_id
         JOIN bet b ON mb.bookmaker_id = b.bookmaker_id AND mb.match_bookmaker_id = b.match_bookmaker_id
WHERE name = 'US Open' AND sex = 'men' AND type = 'singles' AND result NOTNULL;



---------------------------------------------------------------
---------- database manipulations -----------------------------
-- manually updated odds
INSERT INTO bet_manually_updated
SELECT *
FROM bet
WHERE id IN (
    SELECT id
    FROM (
        SELECT home, away, bet_type, o.match_part, odd, probability, result, odd1, odd2,
            CASE WHEN bet_type = 'home' AND odd = odd1 OR bet_type = 'away' AND odd = odd2
                     THEN TRUE
                 ELSE FALSE END AS odds_match, b.id, CASE WHEN bet_type = 'home'
                                                              THEN odd1
                                                          ELSE odd2 END AS or_odds
        FROM matches
                 JOIN tournament t ON matches.tournament_id = t.id
                 JOIN matches_bookmaker mb ON matches.id = mb.match_id
                 JOIN bet b ON mb.bookmaker_id = b.bookmaker_id AND mb.match_bookmaker_id = b.match_bookmaker_id
                 INNER JOIN odds o
        ON b.bookmaker_id = o.bookmaker_id AND b.match_bookmaker_id = o.match_bookmaker_id
                AND b.match_part = o.match_part
        WHERE name = 'US Open' AND sex = 'men' AND type = 'singles'
        ORDER BY odds_match, start_time_utc, home, o.match_part) AS aa
    WHERE odds_match IS FALSE);

-- change odds to originals
SELECT *
FROM (
    SELECT home, away, bet_type, o.match_part, odd, probability, result, odd1, odd2,
        CASE WHEN bet_type = 'home' AND odd = odd1 OR bet_type = 'away' AND odd = odd2
                 THEN TRUE
             ELSE FALSE END AS odds_match, b.id, CASE WHEN bet_type = 'home'
                                                          THEN odd1
                                                      ELSE odd2 END AS or_odds
    FROM matches
             JOIN tournament t ON matches.tournament_id = t.id
             JOIN matches_bookmaker mb ON matches.id = mb.match_id
             JOIN bet b ON mb.bookmaker_id = b.bookmaker_id AND mb.match_bookmaker_id = b.match_bookmaker_id
             INNER JOIN odds o
    ON b.bookmaker_id = o.bookmaker_id AND b.match_bookmaker_id = o.match_bookmaker_id
            AND b.match_part = o.match_part
    WHERE name = 'US Open' AND sex = 'men' AND type = 'singles'
    ORDER BY odds_match, start_time_utc, home, o.match_part) AS aa
WHERE odds_match IS FALSE;