-- Backend correctness migration (idempotent)
-- Apply before recomputing analytics with the corrected pipeline.

ALTER TABLE venue_stats
    ADD COLUMN IF NOT EXISTS defending_win_pct DECIMAL(5,2);

UPDATE format_config
SET powerplay_end = CASE format
        WHEN 'T20' THEN 5
        WHEN 'T20I' THEN 5
        WHEN 'ODI' THEN 9
        ELSE powerplay_end
    END,
    middle_end = CASE format
        WHEN 'T20' THEN 14
        WHEN 'T20I' THEN 14
        WHEN 'ODI' THEN 39
        ELSE middle_end
    END
WHERE format IN ('T20', 'T20I', 'ODI');

UPDATE matches
SET result_type = REPLACE(LOWER(result_type), ' ', '_')
WHERE result_type IS NOT NULL;
