"""
Cricket Intelligence Platform — Batch Processing Module
=======================================================

Production-grade historical batch ingestion infrastructure.

Supports:
- Format-specific batch processing (T20I, ODI, Test, IPL)
- Checkpoint/resume for failed batches
- Idempotent ingestion
- Batch manifest tracking in PostgreSQL
- Configurable batch sizes
- Dry-run mode

Usage:
    python -m data_pipeline.batch --format odi --batch-size 250
    python -m data_pipeline.batch --format odi --resume
    python -m data_pipeline.batch --format odi --batch-id 3 --resume
    python -m data_pipeline.batch --format ipl --batch-size 500 --dry-run
"""
