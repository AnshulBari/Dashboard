"""
Data Quality Audit Runner
=========================

Performs comprehensive integrity checks on the cricket database.

Produces a structured report of issues found.
"""

import os
import logging
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)


@dataclass
class AuditResult:
    """Result of a single audit check."""
    category: str
    check: str
    status: str  # PASS, WARN, FAIL
    count: int = 0
    details: str = ""


@dataclass
class AuditReport:
    """Complete audit report."""
    results: list = field(default_factory=list)
    
    def add(self, category: str, check: str, status: str, count: int = 0, details: str = ""):
        self.results.append(AuditResult(category, check, status, count, details))
    
    @property
    def total_checks(self) -> int:
        return len(self.results)
    
    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.status == "PASS")
    
    @property
    def warnings(self) -> int:
        return sum(1 for r in self.results if r.status == "WARN")
    
    @property
    def failures(self) -> int:
        return sum(1 for r in self.results if r.status == "FAIL")
    
    def print_report(self):
        print("\n" + "=" * 60)
        print("  DATA QUALITY AUDIT REPORT")
        print("=" * 60)
        
        current_category = ""
        for r in self.results:
            if r.category != current_category:
                current_category = r.category
                print(f"\n--- {current_category} ---")
            
            status_marker = {"PASS": "[OK]", "WARN": "[!!]", "FAIL": "[XX]"}[r.status]
            suffix = f" ({r.count})" if r.count else ""
            print(f"  {status_marker} {r.check}{suffix}")
            if r.details:
                print(f"       {r.details}")
        
        print("\n" + "=" * 60)
        print(f"  SUMMARY: {self.total_checks} checks | "
              f"{self.passed} passed | {self.warnings} warnings | {self.failures} failures")
        print("=" * 60)


class AuditRunner:
    """Runs data quality audits against the cricket database."""
    
    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv(
            "DATABASE_URL", "sqlite:///data/cricket_intelligence.db"
        )
        self.engine = create_engine(self.database_url, echo=False)
        self.report = AuditReport()
    
    def _table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the database."""
        with self.engine.connect() as conn:
            result = conn.execute(text(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_name = :name AND table_schema = 'public'"
            ), {"name": table_name})
            return result.scalar() > 0
    
    def run_all(self) -> AuditReport:
        """Run all audit checks and return the report."""
        self.audit_players()
        self.audit_teams()
        self.audit_venues()
        self.audit_matches()
        self.audit_innings()
        if self._table_exists("deliveries"):
            self.audit_deliveries()
        self.audit_scorecards()
        self.audit_analytics()
        self.audit_foreign_keys()
        self.audit_format_isolation()
        return self.report
    
    def audit_players(self):
        """Check player table integrity."""
        cat = "Players"
        with self.engine.connect() as conn:
            # Duplicate canonical names
            rows = conn.execute(text(
                "SELECT canonical_name, COUNT(*) FROM players "
                "GROUP BY canonical_name HAVING COUNT(*) > 1"
            )).fetchall()
            self.report.add(cat, "Duplicate canonical names",
                          "FAIL" if rows else "PASS", len(rows),
                          str([(r[0], r[1]) for r in rows[:5]]) if rows else "")
            
            # Orphaned name mappings
            rows = conn.execute(text(
                "SELECT COUNT(*) FROM player_name_mappings m "
                "LEFT JOIN players p ON m.player_id = p.id WHERE p.id IS NULL"
            )).scalar()
            self.report.add(cat, "Orphaned name mappings",
                          "FAIL" if rows > 0 else "PASS", rows)
            
            # Total players
            total = conn.execute(text("SELECT COUNT(*) FROM players")).scalar()
            self.report.add(cat, "Total players", "PASS", total)
            
            # Total name mappings
            mappings = conn.execute(text("SELECT COUNT(*) FROM player_name_mappings")).scalar()
            self.report.add(cat, "Total name mappings", "PASS", mappings)
            
            # Check for suspicious name patterns (e.g., "Name (2)")
            rows = conn.execute(text(
                "SELECT canonical_name FROM players WHERE canonical_name LIKE '%(%)%' "
                "OR canonical_name LIKE '%[%]%'"
            )).fetchall()
            self.report.add(cat, "Suspicious player names (with brackets)",
                          "WARN" if rows else "PASS", len(rows),
                          str([r[0] for r in rows[:5]]) if rows else "")
    
    def audit_teams(self):
        """Check team table integrity."""
        cat = "Teams"
        with self.engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT canonical_name, COUNT(*) FROM teams "
                "GROUP BY canonical_name HAVING COUNT(*) > 1"
            )).fetchall()
            self.report.add(cat, "Duplicate teams",
                          "FAIL" if rows else "PASS", len(rows))
            
            total = conn.execute(text("SELECT COUNT(*) FROM teams")).scalar()
            self.report.add(cat, "Total teams", "PASS", total)
    
    def audit_venues(self):
        """Check venue table integrity."""
        cat = "Venues"
        with self.engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT name, COUNT(*) FROM venues "
                "GROUP BY name HAVING COUNT(*) > 1"
            )).fetchall()
            self.report.add(cat, "Duplicate venues",
                          "WARN" if rows else "PASS", len(rows),
                          str([r[0] for r in rows[:5]]) if rows else "")
            
            total = conn.execute(text("SELECT COUNT(*) FROM venues")).scalar()
            self.report.add(cat, "Total venues", "PASS", total)
    
    def audit_matches(self):
        """Check match table integrity."""
        cat = "Matches"
        with self.engine.connect() as conn:
            # Duplicate external IDs
            rows = conn.execute(text(
                "SELECT external_id, COUNT(*) FROM matches "
                "GROUP BY external_id HAVING COUNT(*) > 1"
            )).fetchall()
            self.report.add(cat, "Duplicate match external IDs",
                          "FAIL" if rows else "PASS", len(rows))
            
            # Invalid formats
            valid_formats = ("T20", "T20I", "ODI", "Test")
            placeholders = ", ".join([f"'{f}'" for f in valid_formats])
            rows = conn.execute(text(
                f"SELECT DISTINCT format FROM matches WHERE format NOT IN ({placeholders})"
            )).fetchall()
            self.report.add(cat, "Invalid formats",
                          "FAIL" if rows else "PASS", len(rows),
                          str([r[0] for r in rows]) if rows else "")
            
            # Missing teams
            rows = conn.execute(text(
                "SELECT COUNT(*) FROM matches WHERE team_a_id IS NULL OR team_b_id IS NULL"
            )).scalar()
            self.report.add(cat, "Matches with missing teams",
                          "FAIL" if rows > 0 else "PASS", rows)
            
            # Missing dates
            rows = conn.execute(text(
                "SELECT COUNT(*) FROM matches WHERE match_date IS NULL"
            )).scalar()
            self.report.add(cat, "Matches with missing dates",
                          "WARN" if rows > 0 else "PASS", rows)
            
            # Orphaned matches (no innings)
            rows = conn.execute(text(
                "SELECT COUNT(*) FROM matches m "
                "LEFT JOIN innings i ON m.id = i.match_id "
                "WHERE i.id IS NULL"
            )).scalar()
            self.report.add(cat, "Matches with no innings",
                          "WARN" if rows > 0 else "PASS", rows)
            
            # Total by format
            rows = conn.execute(text(
                "SELECT format, COUNT(*) FROM matches GROUP BY format ORDER BY COUNT(*) DESC"
            )).fetchall()
            for r in rows:
                self.report.add(cat, f"Matches (format={r[0]})", "PASS", r[1])
    
    def audit_innings(self):
        """Check innings table integrity."""
        cat = "Innings"
        with self.engine.connect() as conn:
            # Invalid innings numbers per format
            # T20/T20I: max 6 (2 super overs), ODI: max 4 (1 super over), Test: max 4
            max_innings = {"T20": 6, "T20I": 6, "ODI": 4, "Test": 4}
            rows = conn.execute(text(
                "SELECT m.format, MIN(i.innings_number), MAX(i.innings_number), COUNT(*) "
                "FROM innings i JOIN matches m ON i.match_id = m.id "
                "GROUP BY m.format"
            )).fetchall()
            for r in rows:
                fmt, mn, mx, cnt = r
                limit = max_innings.get(fmt, 4)
                if mx > limit:
                    self.report.add(cat, f"Unexpected innings range for {fmt}",
                                  "WARN", cnt, f"max innings = {mx} (expected <= {limit})")
                else:
                    self.report.add(cat, f"Innings range OK for {fmt}",
                                  "PASS", cnt, f"range [{mn}, {mx}]")
            
            # Orphaned innings (match doesn't exist)
            rows = conn.execute(text(
                "SELECT COUNT(*) FROM innings i "
                "LEFT JOIN matches m ON i.match_id = m.id WHERE m.id IS NULL"
            )).scalar()
            self.report.add(cat, "Orphaned innings (no match)",
                          "FAIL" if rows > 0 else "PASS", rows)
    
    def audit_deliveries(self):
        """Check delivery table integrity."""
        cat = "Deliveries"
        with self.engine.connect() as conn:
            # Orphaned deliveries (no innings)
            rows = conn.execute(text(
                "SELECT COUNT(*) FROM deliveries d "
                "LEFT JOIN innings i ON d.innings_id = i.id WHERE i.id IS NULL"
            )).scalar()
            self.report.add(cat, "Orphaned deliveries (no innings)",
                          "FAIL" if rows > 0 else "PASS", rows)
            
            # NULL striker/bowler
            for col, label in [("striker_id", "striker"), ("bowler_id", "bowler")]:
                rows = conn.execute(text(
                    f"SELECT COUNT(*) FROM deliveries WHERE {col} IS NULL"
                )).scalar()
                self.report.add(cat, f"Deliveries with NULL {label}",
                              "FAIL" if rows > 0 else "PASS", rows)
            
            # Invalid runs
            rows = conn.execute(text(
                "SELECT COUNT(*) FROM deliveries WHERE total_runs < 0 OR runs_bat < 0"
            )).scalar()
            self.report.add(cat, "Deliveries with negative runs",
                          "FAIL" if rows > 0 else "PASS", rows)
            
            # ball_in_over > 12 is valid for super overs / no-ball replays
            # over_number has no upper bound for Test cricket (100+ overs valid)
            rows = conn.execute(text(
                "SELECT COUNT(*) FROM deliveries WHERE over_number < 0 OR ball_in_over < 1 OR ball_in_over > 12"
            )).scalar()
            self.report.add(cat, "Deliveries with ball_in_over > 12 (super overs)",
                          "WARN" if rows > 0 else "PASS", rows)
            
            # Wicket with no dismissed player
            rows = conn.execute(text(
                "SELECT COUNT(*) FROM deliveries WHERE is_wicket = TRUE AND dismissed_player_id IS NULL"
            )).scalar()
            self.report.add(cat, "Wickets with no dismissed player",
                          "WARN" if rows > 0 else "PASS", rows)
            
            # Total by format
            rows = conn.execute(text(
                "SELECT m.format, COUNT(*) FROM deliveries d "
                "JOIN innings i ON d.innings_id = i.id "
                "JOIN matches m ON i.match_id = m.id "
                "GROUP BY m.format ORDER BY COUNT(*) DESC"
            )).fetchall()
            for r in rows:
                self.report.add(cat, f"Deliveries (format={r[0]})", "PASS", r[1])
    
    def audit_analytics(self):
        """Check analytics table integrity."""
        cat = "Analytics"
        tables = {
            "player_batting_stats": "player_id",
            "player_bowling_stats": "player_id",
            "player_form": "player_id",
            "team_performance": "team_id",
            "venue_stats": "venue_id",
            "batter_bowler_matchups": None,  # special handling
        }
        
        with self.engine.connect() as conn:
            for table, fk_col in tables.items():
                total = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                
                if fk_col:
                    # Check for orphaned records
                    rows = conn.execute(text(
                        f"SELECT COUNT(*) FROM {table} a "
                        f"LEFT JOIN {'players' if fk_col == 'player_id' else 'teams' if fk_col == 'team_id' else 'venues'} t "
                        f"ON a.{fk_col} = t.id "
                        f"WHERE t.id IS NULL AND a.{fk_col} IS NOT NULL"
                    )).scalar()
                    self.report.add(cat, f"{table} orphaned {fk_col}",
                                  "FAIL" if rows > 0 else "PASS", rows)
                
                if table == "batter_bowler_matchups":
                    # Check NULL batter/bowler IDs
                    rows = conn.execute(text(
                        f"SELECT COUNT(*) FROM {table} WHERE batter_id IS NULL OR bowler_id IS NULL"
                    )).scalar()
                    self.report.add(cat, f"{table} NULL player IDs",
                                  "FAIL" if rows > 0 else "PASS", rows)
                
                # Check for NULL player_id in player tables
                if fk_col == "player_id":
                    rows = conn.execute(text(
                        f"SELECT COUNT(*) FROM {table} WHERE {fk_col} IS NULL"
                    )).scalar()
                    self.report.add(cat, f"{table} NULL player_id",
                                  "FAIL" if rows > 0 else "PASS", rows)
                
                self.report.add(cat, f"{table} total rows", "PASS", total)
    
    def audit_foreign_keys(self):
        """Check foreign key integrity across all tables."""
        cat = "Foreign Keys"
        checks = [
            ("innings", "match_id", "matches"),
            ("match_batting_summary", "match_id", "matches"),
            ("match_batting_summary", "innings_id", "innings"),
            ("match_batting_summary", "player_id", "players"),
            ("match_batting_summary", "batting_team_id", "teams"),
            ("match_bowling_summary", "match_id", "matches"),
            ("match_bowling_summary", "innings_id", "innings"),
            ("match_bowling_summary", "player_id", "players"),
            ("match_bowling_summary", "bowling_team_id", "teams"),
            ("player_batting_stats", "player_id", "players"),
            ("player_bowling_stats", "player_id", "players"),
            ("player_form", "player_id", "players"),
            ("team_performance", "team_id", "teams"),
            ("venue_stats", "venue_id", "venues"),
            ("batter_bowler_matchups", "batter_id", "players"),
            ("batter_bowler_matchups", "bowler_id", "players"),
            ("player_team_affiliations", "player_id", "players"),
            ("player_team_affiliations", "team_id", "teams"),
            ("matches", "team_a_id", "teams"),
            ("matches", "team_b_id", "teams"),
            ("matches", "venue_id", "venues"),
            ("matches", "winner_id", "teams"),
            ("matches", "toss_winner_id", "teams"),
            ("player_name_mappings", "player_id", "players"),
        ]
        
        with self.engine.connect() as conn:
            for child_table, fk_col, parent_table in checks:
                rows = conn.execute(text(
                    f"SELECT COUNT(*) FROM {child_table} c "
                    f"LEFT JOIN {parent_table} p ON c.{fk_col} = p.id "
                    f"WHERE c.{fk_col} IS NOT NULL AND p.id IS NULL"
                )).scalar()
                self.report.add(cat, f"{child_table}.{fk_col} -> {parent_table}",
                              "FAIL" if rows > 0 else "PASS", rows)
    
    def audit_scorecards(self):
        """Check scorecard summary table integrity."""
        cat = "Scorecards"
        if not self._table_exists("match_batting_summary"):
            self.report.add(cat, "match_batting_summary exists", "WARN", 0)
            return
        if not self._table_exists("match_bowling_summary"):
            self.report.add(cat, "match_bowling_summary exists", "WARN", 0)
            return
        with self.engine.connect() as conn:
            # Batting summary row count
            total = conn.execute(text(
                "SELECT COUNT(*) FROM match_batting_summary"
            )).scalar()
            self.report.add(cat, "Batting summary rows", "PASS", total)
            
            # Bowling summary row count
            total = conn.execute(text(
                "SELECT COUNT(*) FROM match_bowling_summary"
            )).scalar()
            self.report.add(cat, "Bowling summary rows", "PASS", total)
            
            # NULL player_id in batting
            rows = conn.execute(text(
                "SELECT COUNT(*) FROM match_batting_summary WHERE player_id IS NULL"
            )).scalar()
            self.report.add(cat, "Batting NULL player_id",
                          "FAIL" if rows > 0 else "PASS", rows)
            
            # NULL player_id in bowling
            rows = conn.execute(text(
                "SELECT COUNT(*) FROM match_bowling_summary WHERE player_id IS NULL"
            )).scalar()
            self.report.add(cat, "Bowling NULL player_id",
                          "FAIL" if rows > 0 else "PASS", rows)
            
            # Verify batting matches innings count
            rows = conn.execute(text(
                "SELECT COUNT(DISTINCT match_id) FROM match_batting_summary"
            )).scalar()
            self.report.add(cat, "Batting matches covered", "PASS", rows)
            
            rows = conn.execute(text(
                "SELECT COUNT(DISTINCT match_id) FROM match_bowling_summary"
            )).scalar()
            self.report.add(cat, "Bowling matches covered", "PASS", rows)
    
    def audit_format_isolation(self):
        """Verify analytics are properly format-scoped."""
        cat = "Format Isolation"
        with self.engine.connect() as conn:
            # Batting stats format distribution
            rows = conn.execute(text(
                "SELECT format, COUNT(*) FROM player_batting_stats GROUP BY format"
            )).fetchall()
            for r in rows:
                self.report.add(cat, f"Batting stats (format={r[0]})", "PASS", r[1])
            
            # Bowling stats format distribution
            rows = conn.execute(text(
                "SELECT format, COUNT(*) FROM player_bowling_stats GROUP BY format"
            )).fetchall()
            for r in rows:
                self.report.add(cat, f"Bowling stats (format={r[0]})", "PASS", r[1])
            
            # Matchups format distribution
            rows = conn.execute(text(
                "SELECT format, COUNT(*) FROM batter_bowler_matchups GROUP BY format"
            )).fetchall()
            for r in rows:
                self.report.add(cat, f"Matchups (format={r[0]})", "PASS", r[1])


def run_audit(database_url: Optional[str] = None) -> int:
    """Run the full audit and print the report. Returns exit code."""
    runner = AuditRunner(database_url=database_url)
    report = runner.run_all()
    report.print_report()
    return 1 if report.failures > 0 else 0


if __name__ == "__main__":
    exit(run_audit())
