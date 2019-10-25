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
WHERE name = 'US Open' AND sex = 'men' AND type = 'singles'
ORDER BY start_time_utc, home, match_part;


-- US Open men single matches - results and expected results
SELECT sum(probability) AS expected_wins, sum(CASE WHEN result IS TRUE THEN 1 ELSE 0 END) AS actual_wins
FROM matches
         JOIN tournament t ON matches.tournament_id = t.id
         JOIN matches_bookmaker mb ON matches.id = mb.match_id
         JOIN bet b ON mb.bookmaker_id = b.bookmaker_id AND mb.match_bookmaker_id = b.match_bookmaker_id
WHERE name = 'US Open' AND sex = 'men' AND type = 'singles';

-- expected money wins and actual wins - naive betting
SELECT home, away, bet_type, match_part, odd, probability, result,
    probability * (odd - 1) - (1 - probability) AS expected_win,
    CASE WHEN result IS TRUE
             THEN odd - 1
         ELSE CASE WHEN result IS FALSE THEN -1 ELSE 0 END END AS win
FROM matches
         JOIN tournament t ON matches.tournament_id = t.id
         JOIN matches_bookmaker mb ON matches.id = mb.match_id
         JOIN bet b ON mb.bookmaker_id = b.bookmaker_id AND mb.match_bookmaker_id = b.match_bookmaker_id
WHERE name = 'US Open' AND sex = 'men' AND type = 'singles'
ORDER BY start_time_utc, home, match_part;


-- expected money wins and actual wins - naive betting summed
SELECT sum(probability * (odd - 1) - (1 - probability)) AS expected_win,
    sum(CASE WHEN result IS TRUE
                 THEN odd - 1
             ELSE CASE WHEN result IS FALSE THEN -1 ELSE 0 END END) AS win
FROM matches
         JOIN tournament t ON matches.tournament_id = t.id
         JOIN matches_bookmaker mb ON matches.id = mb.match_id
         JOIN bet b ON mb.bookmaker_id = b.bookmaker_id AND mb.match_bookmaker_id = b.match_bookmaker_id
WHERE name = 'US Open' AND sex = 'men' AND type = 'singles';


-- expected money wins and actual wins - advanced betting
SELECT home, away, bet_type, match_part, odd, probability, result,
    probability * (probability * odd - probability) - (1 - probability) * probability AS expected_win,
    CASE WHEN result IS TRUE
             THEN probability * odd - probability
         ELSE CASE WHEN result IS FALSE THEN -probability ELSE 0 END END AS win
FROM matches
         JOIN tournament t ON matches.tournament_id = t.id
         JOIN matches_bookmaker mb ON matches.id = mb.match_id
         JOIN bet b ON mb.bookmaker_id = b.bookmaker_id AND mb.match_bookmaker_id = b.match_bookmaker_id
WHERE name = 'US Open' AND sex = 'men' AND type = 'singles'
ORDER BY start_time_utc, home, match_part;


-- expected money wins and actual wins - advanced betting summed
SELECT sum((probability * odd - probability) - (1 - probability) * probability) AS expected_win,
    sum(CASE WHEN result IS TRUE
                 THEN probability * odd - probability
             ELSE CASE WHEN result IS FALSE THEN -probability ELSE 0 END END) AS win
FROM matches
         JOIN tournament t ON matches.tournament_id = t.id
         JOIN matches_bookmaker mb ON matches.id = mb.match_id
         JOIN bet b ON mb.bookmaker_id = b.bookmaker_id AND mb.match_bookmaker_id = b.match_bookmaker_id
WHERE name = 'US Open' AND sex = 'men' AND type = 'singles';




-- Berrettini Matteo	Popyrin Alexei	home	set4	1.53	0.6363185834612604	true	-0.026432567304271626	2019-08-31 21:15:00.000000
-- original odds (acounted by the algo) 1.58

-- Lopez Feliciano	Nishioka Yoshihito	away	set2	1.5	0.6552895891572497	false	-0.017065616264125505	2019-08-29 17:35:00.000000
-- original odds (acounted by the algo) 1.53

-- najit neshody a manualni upravy a do clanku asi pocitat s origo cisly