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