# Analytics Methodology

## Player Form Score

### Concept

The Form Score is an original, explainable metric that quantifies a player's current form based on multiple statistical dimensions.

### Formula

```
Form_Score = Σ(component_i × weight_i) for i in {recent, consistency, opposition, venue, situation, efficiency}
```

### Components

| # | Component | Weight | Method |
|---|-----------|--------|--------|
| 1 | Recent Performance | 35% | Average of last 10 innings, min-max normalized |
| 2 | Consistency | 20% | 1 - Coefficient of Variation, normalized |
| 3 | Opposition Strength | 15% | Weighted avg performance by opponent strength |
| 4 | Venue Performance | 10% | Cross-venue coefficient of variation |
| 5 | Match Situation | 10% | Chasing avg / Overall avg ratio |
| 6 | Efficiency | 10% | Strike Rate × Average / 100 |

### Normalization

Each component is normalized to 0-100 using min-max scaling:

```
normalized = (value - min) / (max - min) × 100
```

This means:
- A player with the best value gets 100
- A player with the worst gets 0
- The median player gets roughly 50

### Weight Justification

Weights were chosen based on cricket analytics literature and domain knowledge:

- **Recent Performance (35%)**: Most heavily weighted because current form is the primary concern
- **Consistency (20%)**: Reliable performers are more valuable than volatile ones
- **Opposition Strength (15%)**: Performance against strong teams is more meaningful
- **Other components (10% each)**: Contextual factors that provide nuance

### Limitations

1. Requires minimum 5 innings for statistical significance
2. Min-max scaling is sensitive to outliers
3. Weights are initial estimates, not empirically validated
4. Cold start problem for players with limited data
5. Does not account for match importance or pressure situations

## Team Strength Score

### Formula

```
Team_Strength = 0.35 × Batting_Score + 0.35 × Bowling_Score + 0.30 × Win_Score
```

### Components

- **Batting Score**: Normalized average total score (0-100)
- **Bowling Score**: Inverse normalized economy rate (0-100)
- **Win Score**: Win percentage (0-100)

### Rationale

- Batting and bowling are equally important (35% each)
- Winning is slightly less important because it's an outcome of batting + bowling
- All components are normalized to comparable scales

## Player Impact (Planned)

### Concept

Measures actual performance vs expected performance:

```
Impact = Actual Performance - Expected Performance
```

### Expected Performance Model

For batting:
```
Expected Runs = f(format, over, wickets_remaining, current_score, venue, opposition, bowling_type)
```

For bowling:
```
Expected Runs_Conceded = f(format, over, batting_strength, venue, match_situation)
```

### Training Data

Historical match states from Cricsheet data, using:
- Score at delivery point
- Wickets in hand
- Overs remaining
- Target (if chasing)
- Venue average
- Opposition strength

### Model Options

1. **Logistic Regression** — interpretable, fast
2. **Random Forest** — handles non-linear relationships
3. **XGBoost** — potentially highest accuracy

**Status**: This metric is planned for Phase 9 of the development roadmap.

## Consistency Score

### Formula

```
CV = stddev(runs) / mean(runs)
Consistency_Score = (1 - CV) × 100
```

### Interpretation

- Higher score = more consistent (lower variance relative to mean)
- A player who scores 30±5 is more consistent than one who scores 40±20
- Minimum 5 innings required for statistical validity

## Matchup Analytics

### Direct Matchups (Batter vs Bowler)

Requires minimum 10 balls for statistical significance.

Metrics: balls, runs, wickets, strike_rate, batting_average, dot_ball_pct, boundary_pct

### Contextual Matchups

- **vs Pace/Spin**: Aggregated by bowling type
- **vs Left/Right Arm**: Aggregated by bowling arm

### Statistical Significance

Matchups with fewer than 10 balls are excluded from the platform to prevent misleading small-sample statistics.

## Implementation Notes

### Current Implementation (pandas)

The active pipeline uses pandas for all analytics computation. The key functions are in `data_pipeline/pipeline/analytics.py`:

- `compute_player_batting_stats()` — Career and phase-specific batting statistics
- `compute_player_bowling_stats()` — Career and phase-specific bowling statistics
- `compute_player_form_scores()` — Weighted composite form score
- `compute_team_performance()` — Win rates, strength scores, phase performance
- `compute_venue_stats()` — Average scores, phase-wise statistics
- `compute_matchups()` — Head-to-head batter vs bowler statistics

### Reference Implementation (PySpark)

PySpark implementations exist in `data_pipeline/spark/` and can be activated if:
- Data volumes exceed pandas memory capacity
- A compatible Java version (8–17) is installed
- Distributed processing is needed

### Performance Comparison

For the Cricsheet IPL dataset (200 matches, ~47K deliveries):

| Operation | pandas (current) | Notes |
|-----------|-----------------|-------|
| Download + extract | ~15s | Network-dependent |
| Read + flatten | ~2s | JSON parsing |
| Entity resolution | ~5s | DB lookups |
| Write core data | ~25s | Bulk inserts |
| Compute analytics | ~3s | In-memory |
| Write analytics | ~2s | Truncate + insert |
| **Total** | **~50s** | End-to-end |

For larger datasets (full IPL: 1,243 matches, ~350K deliveries), the pipeline takes ~10 minutes.
