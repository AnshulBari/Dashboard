"""
Batch Manifest — Checkpoint & Resume Tracking
==============================================

Tracks batch processing state in PostgreSQL.

Table: batch_manifest
- Records each batch's status, timing, and statistics
- Enables resume from failed batches
- Provides audit trail for historical ingestion

Status lifecycle:
    PENDING → RUNNING → COMPLETED
                         ↘ FAILED (with error info)
"""

import uuid
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

# Status constants
PENDING = "PENDING"
RUNNING = "RUNNING"
COMPLETED = "COMPLETED"
FAILED = "FAILED"

# Table SQL (created on first use)
MANIFEST_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS batch_manifest (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    dataset VARCHAR(20) NOT NULL,          -- 't20i', 'odi', 'test', 'ipl'
    batch_id INTEGER NOT NULL,
    batch_size INTEGER NOT NULL,
    file_count INTEGER DEFAULT 0,
    match_count INTEGER DEFAULT 0,
    delivery_count INTEGER DEFAULT 0,
    innings_count INTEGER DEFAULT 0,
    player_count INTEGER DEFAULT 0,
    team_count INTEGER DEFAULT 0,
    venue_count INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'PENDING',
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    processing_duration_seconds DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(dataset, batch_id)
);

CREATE INDEX IF NOT EXISTS idx_batch_manifest_status ON batch_manifest(status);
CREATE INDEX IF NOT EXISTS idx_batch_manifest_dataset ON batch_manifest(dataset);
"""


class BatchManifest:
    """
    Manages batch processing state in PostgreSQL.

    Provides:
    - Table creation (idempotent)
    - Batch status tracking
    - Resume-from-failure support
    - Statistics recording
    """

    def __init__(self, engine):
        self.engine = engine

    def ensure_table(self):
        """Create the manifest table if it doesn't exist."""
        with self.engine.connect() as conn:
            conn.execute(text(MANIFEST_TABLE_SQL))
            conn.commit()
        logger.debug("Batch manifest table ensured")

    def create_batch(
        self,
        dataset: str,
        batch_id: int,
        batch_size: int,
        file_count: int = 0,
    ) -> str:
        """Register a new batch as PENDING."""
        batch_id_uuid = str(uuid.uuid4())
        with self.engine.connect() as conn:
            # Check if batch already exists
            existing = conn.execute(
                text(
                    "SELECT id, status FROM batch_manifest "
                    "WHERE dataset = :ds AND batch_id = :bid"
                ),
                {"ds": dataset, "bid": batch_id},
            ).fetchone()

            if existing:
                logger.debug(
                    f"Batch {dataset}/{batch_id} already exists (status={existing[1]})"
                )
                return str(existing[0])

            conn.execute(
                text(
                    "INSERT INTO batch_manifest "
                    "(id, dataset, batch_id, batch_size, file_count, status) "
                    "VALUES (:id, :ds, :bid, :bs, :fc, :status)"
                ),
                {
                    "id": batch_id_uuid,
                    "ds": dataset,
                    "bid": batch_id,
                    "bs": batch_size,
                    "fc": file_count,
                    "status": PENDING,
                },
            )
            conn.commit()

        logger.debug(f"Created batch manifest: {dataset}/{batch_id}")
        return batch_id_uuid

    def start_batch(self, dataset: str, batch_id: int) -> Optional[str]:
        """Mark a batch as RUNNING. Returns the manifest row ID or None."""
        with self.engine.connect() as conn:
            result = conn.execute(
                text(
                    "UPDATE batch_manifest "
                    "SET status = :status, started_at = :now "
                    "WHERE dataset = :ds AND batch_id = :bid "
                    "AND status IN ('PENDING', 'FAILED') "
                    "RETURNING id"
                ),
                {
                    "status": RUNNING,
                    "now": datetime.utcnow(),
                    "ds": dataset,
                    "bid": batch_id,
                },
            )
            row = result.fetchone()
            conn.commit()
            return str(row[0]) if row else None

    def complete_batch(
        self,
        dataset: str,
        batch_id: int,
        match_count: int = 0,
        delivery_count: int = 0,
        innings_count: int = 0,
        player_count: int = 0,
        team_count: int = 0,
        venue_count: int = 0,
    ):
        """Mark a batch as COMPLETED with statistics."""
        with self.engine.connect() as conn:
            conn.execute(
                text(
                    "UPDATE batch_manifest "
                    "SET status = :status, "
                    "  completed_at = :now, "
                    "  processing_duration_seconds = EXTRACT(EPOCH FROM (NOW() - started_at)), "
                    "  match_count = :mc, delivery_count = :dc, innings_count = :ic, "
                    "  player_count = :pc, team_count = :tc, venue_count = :vc "
                    "WHERE dataset = :ds AND batch_id = :bid"
                ),
                {
                    "status": COMPLETED,
                    "now": datetime.utcnow(),
                    "mc": match_count,
                    "dc": delivery_count,
                    "ic": innings_count,
                    "pc": player_count,
                    "tc": team_count,
                    "vc": venue_count,
                    "ds": dataset,
                    "bid": batch_id,
                },
            )
            conn.commit()
        logger.info(f"Batch {dataset}/{batch_id} marked COMPLETED")

    def fail_batch(self, dataset: str, batch_id: int, error: str):
        """Mark a batch as FAILED with error message."""
        with self.engine.connect() as conn:
            conn.execute(
                text(
                    "UPDATE batch_manifest "
                    "SET status = :status, error_message = :err, "
                    "  completed_at = NOW() "
                    "WHERE dataset = :ds AND batch_id = :bid"
                ),
                {
                    "status": FAILED,
                    "err": error[:2000],  # Truncate long errors
                    "ds": dataset,
                    "bid": batch_id,
                },
            )
            conn.commit()
        logger.error(f"Batch {dataset}/{batch_id} marked FAILED: {error[:200]}")

    def get_batch_status(self, dataset: str, batch_id: int) -> Optional[dict]:
        """Get status of a specific batch."""
        with self.engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT id, dataset, batch_id, batch_size, file_count, "
                    "  match_count, delivery_count, innings_count, "
                    "  status, error_message, started_at, completed_at, "
                    "  processing_duration_seconds "
                    "FROM batch_manifest "
                    "WHERE dataset = :ds AND batch_id = :bid"
                ),
                {"ds": dataset, "bid": batch_id},
            )
            row = result.fetchone()
            if not row:
                return None
            return {
                "id": str(row[0]),
                "dataset": row[1],
                "batch_id": row[2],
                "batch_size": row[3],
                "file_count": row[4],
                "match_count": row[5],
                "delivery_count": row[6],
                "innings_count": row[7],
                "status": row[8],
                "error_message": row[9],
                "started_at": row[10],
                "completed_at": row[11],
                "processing_duration_seconds": row[12],
            }

    def get_next_pending_batch(self, dataset: str) -> Optional[int]:
        """Get the next PENDING or FAILED batch ID for a dataset."""
        with self.engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT batch_id FROM batch_manifest "
                    "WHERE dataset = :ds AND status IN ('PENDING', 'FAILED') "
                    "ORDER BY batch_id ASC LIMIT 1"
                ),
                {"ds": dataset},
            )
            row = result.fetchone()
            return row[0] if row else None

    def get_all_batches(self, dataset: str) -> list[dict]:
        """Get all batches for a dataset, ordered by batch_id."""
        with self.engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT batch_id, batch_size, file_count, match_count, "
                    "  delivery_count, status, error_message, "
                    "  processing_duration_seconds, started_at, completed_at "
                    "FROM batch_manifest "
                    "WHERE dataset = :ds "
                    "ORDER BY batch_id ASC"
                ),
                {"ds": dataset},
            )
            rows = result.fetchall()
            return [
                {
                    "batch_id": r[0],
                    "batch_size": r[1],
                    "file_count": r[2],
                    "match_count": r[3],
                    "delivery_count": r[4],
                    "status": r[5],
                    "error_message": r[6],
                    "duration_seconds": r[7],
                    "started_at": r[8],
                    "completed_at": r[9],
                }
                for r in rows
            ]

    def get_completed_count(self, dataset: str) -> int:
        """Count how many batches are COMPLETED for a dataset."""
        with self.engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT COUNT(*) FROM batch_manifest "
                    "WHERE dataset = :ds AND status = 'COMPLETED'"
                ),
                {"ds": dataset},
            )
            return result.scalar()

    def get_total_files_processed(self, dataset: str) -> int:
        """Get total file_count across all completed batches."""
        with self.engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT COALESCE(SUM(file_count), 0) FROM batch_manifest "
                    "WHERE dataset = :ds AND status = 'COMPLETED'"
                ),
                {"ds": dataset},
            )
            return result.scalar()

    def reset_batch(self, dataset: str, batch_id: int):
        """Reset a batch to PENDING for re-processing."""
        with self.engine.connect() as conn:
            conn.execute(
                text(
                    "UPDATE batch_manifest "
                    "SET status = 'PENDING', error_message = NULL, "
                    "  started_at = NULL, completed_at = NULL "
                    "WHERE dataset = :ds AND batch_id = :bid"
                ),
                {"ds": dataset, "bid": batch_id},
            )
            conn.commit()
        logger.info(f"Batch {dataset}/{batch_id} reset to PENDING")

    def print_summary(self, dataset: str):
        """Print a human-readable summary of all batches."""
        batches = self.get_all_batches(dataset)
        if not batches:
            print(f"No batches found for {dataset}")
            return

        print(f"\n{'='*60}")
        print(f"Batch Manifest: {dataset.upper()}")
        print(f"{'='*60}")
        print(
            f"{'Batch':>6} {'Files':>6} {'Matches':>8} {'Deliveries':>12} "
            f"{'Status':>12} {'Duration':>10}"
        )
        print(f"{'-'*60}")

        total_matches = 0
        total_deliveries = 0
        for b in batches:
            status_icon = {
                COMPLETED: "OK",
                RUNNING: "..",
                FAILED: "!!",
                PENDING: "--",
            }.get(b["status"], "??")
            dur = f"{b['duration_seconds']:.1f}s" if b["duration_seconds"] else "-"
            print(
                f"{b['batch_id']:>6} {b['file_count']:>6} "
                f"{b['match_count'] or 0:>8} {b['delivery_count'] or 0:>12} "
                f"{status_icon} {b['status']:>10} {dur:>10}"
            )
            if b["status"] == COMPLETED:
                total_matches += b["match_count"] or 0
                total_deliveries += b["delivery_count"] or 0

        print(f"{'-'*60}")
        print(
            f"{'TOTAL':>6} {'':>6} {total_matches:>8} {total_deliveries:>12} "
            f"{'':>12}"
        )
        print(f"{'='*60}")
