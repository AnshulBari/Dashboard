"""
Main Pipeline Runner
====================

Orchestrates the full ETL pipeline:

1. INGEST   → Download/extract Cricsheet data
2. READ     → Load into Spark DataFrames
3. VALIDATE → Check data quality
4. NORMALIZE → Map to canonical entities
5. TRANSFORM → Add computed columns
6. AGGREGATE → Compute analytics
7. FEATURE  → Form scores, matchups
8. WRITE    → Export to PostgreSQL / Parquet

Usage:
    python -m data-pipeline.jobs.run_pipeline --format t20i --sample 100
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F

from data_pipeline.spark.session import create_spark_session, stop_spark_session
from data_pipeline.spark.read import read_matches_batch, flatten_match_data
from data_pipeline.spark.normalize import normalize_deliveries, create_player_registry
from data_pipeline.spark.transform import (
    add_cumulative_stats,
    compute_player_innings_stats,
    compute_bowler_innings_stats,
    compute_matchups,
    compute_match_results,
)
from data_pipeline.spark.player_stats import (
    compute_career_batting_stats,
    compute_career_bowling_stats,
    compute_batting_by_phase,
    compute_batting_by_situation,
    compute_consistency_score,
)
from data_pipeline.spark.team_stats import (
    compute_team_match_results,
    compute_team_performance,
    compute_team_bowling_stats,
    compute_team_strength_score,
)
from data_pipeline.spark.venue_stats import (
    compute_comprehensive_venue_stats,
)
from data_pipeline.analytics.form_score import compute_form_score
from data_pipeline.ingestion.cricsheet import CricsheetIngestor

logger = logging.getLogger(__name__)


class CricketPipeline:
    """
    Main orchestrator for the Cricket Intelligence data pipeline.
    
    Coordinates ingestion, transformation, and analytics computation.
    """
    
    def __init__(
        self,
        data_dir: str = "data/raw",
        output_dir: str = "data/processed",
        analytics_dir: str = "data/analytics",
    ):
        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir)
        self.analytics_dir = Path(analytics_dir)
        
        # Create output directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.analytics_dir.mkdir(parents=True, exist_ok=True)
        
        self.spark = None
        self.ingestor = CricsheetIngestor(str(self.data_dir))
        
        # Pipeline statistics
        self.stats = {
            "records_processed": 0,
            "records_rejected": 0,
            "records_duplicated": 0,
            "processing_time_seconds": 0,
        }
    
    def initialize(self):
        """Initialize Spark session."""
        logger.info("Initializing Spark session...")
        self.spark = create_spark_session(app_name="CricketIntelligencePipeline")
        logger.info(f"Spark session created: {self.spark.sparkContext.appName}")
    
    def ingest(self, format_type: str, force: bool = False):
        """
        Stage 1: Download and extract Cricsheet data.
        """
        logger.info(f"[Stage 1] Ingesting {format_type} data from Cricsheet...")
        
        zip_path = self.ingestor.download(format_type, force=force)
        extract_dir = self.ingestor.extract(format_type, force=force)
        
        match_count = self.ingestor.get_match_count(format_type)
        logger.info(f"[Stage 1] Ingested {match_count} matches for {format_type}")
        return extract_dir
    
    def read_and_flatten(self, extract_dir: Path) -> DataFrame:
        """
        Stage 2: Read JSON files into Spark and flatten.
        """
        logger.info(f"[Stage 2] Reading match files from {extract_dir}...")
        
        raw_df = read_matches_batch(self.spark, extract_dir)
        flat_df = flatten_match_data(self.spark, raw_df)
        
        self.stats["records_processed"] = flat_df.count()
        logger.info(f"[Stage 2] Flattened to {self.stats['records_processed']} deliveries")
        
        return flat_df
    
    def validate(self, df: DataFrame) -> DataFrame:
        """
        Stage 3: Validate data quality.
        
        Checks:
        - Required fields are not null
        - Runs are non-negative
        - Over numbers are valid
        - No impossible values
        """
        logger.info("[Stage 3] Validating data quality...")
        
        initial_count = df.count()
        
        # Basic validation
        validated = df.filter(
            # Batter must be present
            F.col("batter").isNotNull() &
            # Bowler must be present
            F.col("bowler").isNotNull() &
            # Runs cannot be negative
            (F.col("runs_batter") >= 0) &
            (F.col("runs_total") >= 0) &
            # Over number must be reasonable (0-50 for Test, 0-20 for limited overs)
            (F.col("over_number") >= 0) &
            (F.col("over_number") <= 50) &
            # Ball in over must be 1-6
            (F.col("ball_in_over") >= 1) &
            (F.col("ball_in_over") <= 9)  # 9 because of extras
        )
        
        final_count = validated.count()
        rejected = initial_count - final_count
        
        self.stats["records_rejected"] = rejected
        logger.info(
            f"[Stage 3] Validation: {final_count} valid, {rejected} rejected "
            f"({rejected/initial_count*100:.1f}% rejection rate)"
        )
        
        return validated
    
    def normalize(self, df: DataFrame) -> DataFrame:
        """
        Stage 4: Normalize data to canonical entities.
        """
        logger.info("[Stage 4] Normalizing data...")
        
        normalized = normalize_deliveries(df)
        
        # Show sample of normalized data
        logger.info("[Stage 4] Sample normalized teams:")
        normalized.select(
            "batting_team", "canonical_batting_team",
            "bowling_team", "canonical_bowling_team"
        ).distinct().show(10, truncate=False)
        
        return normalized
    
    def transform(self, normalized_df: DataFrame) -> DataFrame:
        """
        Stage 5: Add computed fields and transform data.
        """
        logger.info("[Stage 5] Transforming data...")
        
        transformed = add_cumulative_stats(normalized_df)
        
        logger.info(f"[Stage 5] Added cumulative stats to {transformed.count()} rows")
        return transformed
    
    def aggregate(self, transformed_df: DataFrame):
        """
        Stage 6: Compute aggregated statistics.
        """
        logger.info("[Stage 6] Computing aggregations...")
        
        # Player innings stats
        player_batting = compute_player_innings_stats(transformed_df)
        logger.info(f"  Player batting innings: {player_batting.count()} records")
        
        player_bowling = compute_bowler_innings_stats(transformed_df)
        logger.info(f"  Player bowling innings: {player_bowling.count()} records")
        
        # Career stats
        career_batting = compute_career_batting_stats(player_batting)
        career_bowling = compute_career_bowling_stats(player_bowling)
        
        # Phase stats
        batting_by_phase = compute_batting_by_phase(transformed_df)
        
        # Situation stats
        batting_by_situation = compute_batting_by_situation(transformed_df)
        
        # Consistency
        consistency = compute_consistency_score(player_batting)
        
        # Team stats
        team_perf = compute_team_performance(
            compute_team_match_results(transformed_df)
        )
        
        team_bowling = compute_team_bowling_stats(transformed_df)
        team_strength = compute_team_strength_score(team_perf, team_bowling)
        
        # Venue stats
        venue_stats = compute_comprehensive_venue_stats(transformed_df, transformed_df)
        
        # Matchups
        matchups = compute_matchups(transformed_df)
        
        return {
            "player_batting_innings": player_batting,
            "player_bowling_innings": player_bowling,
            "career_batting": career_batting,
            "career_bowling": career_bowling,
            "batting_by_phase": batting_by_phase,
            "batting_by_situation": batting_by_situation,
            "consistency": consistency,
            "team_performance": team_perf,
            "team_bowling": team_bowling,
            "team_strength": team_strength,
            "venue_stats": venue_stats,
            "matchups": matchups,
        }
    
    def compute_analytics(self, transformed_df: DataFrame, aggregations: dict):
        """
        Stage 7: Compute advanced analytics (form scores, etc).
        """
        logger.info("[Stage 7] Computing advanced analytics...")
        
        # Player Form Score
        player_batting = aggregations["player_batting_innings"]
        form_scores = compute_form_score(player_batting)
        
        logger.info(f"  Form scores computed for {form_scores.count()} player-format combos")
        
        return {
            "form_scores": form_scores,
        }
    
    def write_results(self, aggregations: dict, analytics: dict):
        """
        Stage 8: Write results to output files (Parquet + JSON).
        
        In production, this would write to PostgreSQL via JDBC.
        For local development, we write to Parquet for efficiency.
        """
        logger.info("[Stage 8] Writing results...")
        
        # Write aggregations as Parquet
        for name, df in aggregations.items():
            output_path = self.output_dir / f"{name}.parquet"
            df.write.mode("overwrite").parquet(str(output_path))
            logger.info(f"  Written: {output_path} ({df.count()} rows)")
        
        # Write analytics
        for name, df in analytics.items():
            output_path = self.analytics_dir / f"{name}.parquet"
            df.write.mode("overwrite").parquet(str(output_path))
            logger.info(f"  Written: {output_path} ({df.count()} rows)")
        
        # Write summary stats as JSON
        summary_path = self.output_dir / "pipeline_summary.json"
        with open(summary_path, "w") as f:
            json.dump(self.stats, f, indent=2, default=str)
        
        logger.info(f"  Pipeline summary: {summary_path}")
    
    def run(
        self,
        format_type: str = "t20i",
        force: bool = False,
        sample_limit: int = None,
    ):
        """
        Run the complete pipeline.
        
        Args:
            format_type: Cricket format to process (t20i, odi, test, ipl)
            force: Force re-download and re-processing
            sample_limit: Limit number of matches to process (for testing)
        """
        start_time = time.time()
        
        try:
            self.initialize()
            
            # Stage 1: Ingest
            extract_dir = self.ingest(format_type, force=force)
            
            # Stage 2: Read and flatten
            raw_df = self.read_and_flatten(extract_dir)
            
            # Optional: limit for testing
            if sample_limit:
                raw_df = raw_df.limit(sample_limit)
                logger.info(f"  Limited to {sample_limit} records for testing")
            
            # Stage 3: Validate
            validated_df = self.validate(raw_df)
            
            # Stage 4: Normalize
            normalized_df = self.normalize(validated_df)
            
            # Stage 5: Transform
            transformed_df = self.transform(normalized_df)
            
            # Stage 6: Aggregate
            aggregations = self.aggregate(transformed_df)
            
            # Stage 7: Analytics
            analytics = self.compute_analytics(transformed_df, aggregations)
            
            # Stage 8: Write
            self.write_results(aggregations, analytics)
            
            # Report
            self.stats["processing_time_seconds"] = round(time.time() - start_time, 2)
            logger.info("=" * 60)
            logger.info("Pipeline completed successfully!")
            logger.info(f"  Total time: {self.stats['processing_time_seconds']}s")
            logger.info(f"  Records processed: {self.stats['records_processed']}")
            logger.info(f"  Records rejected: {self.stats['records_rejected']}")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            raise
        finally:
            stop_spark_session()


def main():
    parser = argparse.ArgumentParser(
        description="Cricket Intelligence Platform — Data Pipeline"
    )
    parser.add_argument(
        "--format", "-f",
        default="t20i",
        choices=["t20i", "odi", "test", "ipl", "t20s"],
        help="Cricket format to process",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-download and re-processing",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=None,
        help="Limit number of matches (for testing)",
    )
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    
    pipeline = CricketPipeline()
    pipeline.run(
        format_type=args.format,
        force=args.force,
        sample_limit=args.sample,
    )


if __name__ == "__main__":
    main()
