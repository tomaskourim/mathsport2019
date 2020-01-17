ALTER TABLE bet
    ADD COLUMN odd_corrected    FLOAT,
    ADD COLUMN result_corrected BOOLEAN;

UPDATE bet set result_corrected=result;

