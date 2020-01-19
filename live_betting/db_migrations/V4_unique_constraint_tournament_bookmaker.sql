ALTER TABLE tournament_bookmaker
    ADD CONSTRAINT bookid_tourn_bookid_tourn_bookextraid_unique UNIQUE (bookmaker_id, tournament_bookmaker_id, tournament_bookmaker_extra_id)

-- todo do it actually