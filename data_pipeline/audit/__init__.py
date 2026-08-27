"""
Data Quality Audit
==================

Reusable audit for validating database integrity.

Checks:
- Player identity: duplicates, orphaned aliases, unresolved names
- Team integrity: duplicates, invalid affiliations
- Match integrity: duplicates, invalid formats, missing references
- Delivery integrity: orphaned records, invalid values
- Analytics integrity: orphaned stats, duplicates
- Foreign-key integrity across all tables

Usage:
    python -m data_pipeline.audit
"""
