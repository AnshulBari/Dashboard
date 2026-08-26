"""
Format Configuration
====================

Centralizes format-specific rules and boundaries.

This module provides a single source of truth for:
- Phase definitions (powerplay, middle, death)
- Standard overs
- Max innings
- Multi-day support
- First-class classification

Used by:
- Analytics computation (phase-specific stats)
- API filtering
- Frontend display logic

Design principle:
Format config GUIDES analytics and UI.
It does NOT reject source data.
The Cricsheet source remains authoritative.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class FormatRules:
    """Immutable rules for a cricket format."""
    
    format: str
    standard_overs: Optional[int]  # None = unlimited
    powerplay_end: int             # Last over of powerplay (0-indexed)
    middle_end: int                # Last over of middle phase (0-indexed)
    max_innings: int               # Maximum innings per match
    is_multi_day: bool
    is_first_class: bool
    
    @property
    def death_start(self) -> int:
        """First over of death phase (1-indexed for display)."""
        return self.middle_end + 1
    
    def classify_phase(self, over_number: int) -> str:
        """
        Classify an over number into a match phase.
        
        Args:
            over_number: 0-indexed over number
            
        Returns:
            'powerplay', 'middle', or 'death'
        """
        if self.format in ("Test",):
            # Test cricket doesn't use T20-style phases
            return "general"
        
        if over_number <= self.powerplay_end:
            return "powerplay"
        elif over_number <= self.middle_end:
            return "middle"
        else:
            return "death"
    
    def get_phase_label(self, over_number: int) -> str:
        """Get human-readable phase label."""
        phase = self.classify_phase(over_number)
        if phase == "general":
            return "match play"
        return phase


# ============================================================
# Format Definitions
# ============================================================

FORMATS = {
    "T20": FormatRules(
        format="T20",
        standard_overs=20,
        powerplay_end=5,      # Overs 0-5 (6 overs)
        middle_end=14,        # Overs 6-14 (9 overs)
        max_innings=2,
        is_multi_day=False,
        is_first_class=False,
    ),
    "T20I": FormatRules(
        format="T20I",
        standard_overs=20,
        powerplay_end=5,      # Overs 0-5 (6 overs)
        middle_end=14,        # Overs 6-14 (9 overs)
        max_innings=2,
        is_multi_day=False,
        is_first_class=False,
    ),
    "ODI": FormatRules(
        format="ODI",
        standard_overs=50,
        powerplay_end=9,      # Overs 0-9 (10 overs) — first powerplay
        middle_end=39,        # Overs 10-39 (30 overs)
        max_innings=2,
        is_multi_day=False,
        is_first_class=False,
    ),
    "Test": FormatRules(
        format="Test",
        standard_overs=None,  # Unlimited
        powerplay_end=0,      # No powerplay concept
        middle_end=0,         # No middle phase concept
        max_innings=4,
        is_multi_day=True,
        is_first_class=True,
    ),
}


def get_format_rules(format_str: str) -> FormatRules:
    """
    Get format rules for a given format string.
    
    Falls back to T20 rules if format not recognized.
    """
    normalized = format_str.strip() if format_str else "T20"
    return FORMATS.get(normalized, FORMATS["T20"])


def classify_phase(over_number: int, format_str: str = "T20") -> str:
    """
    Convenience function: classify an over into a phase.
    
    Returns 'powerplay', 'middle', 'death', or 'general' (for Test).
    """
    rules = get_format_rules(format_str)
    return rules.classify_phase(over_number)


def is_format_multi_day(format_str: str) -> bool:
    """Check if a format is multi-day."""
    return get_format_rules(format_str).is_multi_day


def is_format_first_class(format_str: str) -> bool:
    """Check if a format is first-class (Test)."""
    return get_format_rules(format_str).is_first_class
