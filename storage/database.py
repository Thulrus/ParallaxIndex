"""
Storage layer for Parallax Index.

Handles all database operations for sources and distilled snapshots.
Uses SQLite with async support via aiosqlite.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import UUID

import aiosqlite

from core.schemas import DistilledSnapshot, SourceInstance, TermStat


class Database:
    """
    Async SQLite database manager.
    
    Handles schema creation and provides data access methods for:
    - Source instances (CRUD operations)
    - Distilled snapshots (append-only storage)
    """
    
    def __init__(self, db_path: str = "parallax_index.db"):
        """
        Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._initialized = False
    
    async def initialize(self) -> None:
        """
        Initialize database schema.
        
        Creates tables if they don't exist. Safe to call multiple times.
        """
        if self._initialized:
            return
        
        # Ensure directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        async with aiosqlite.connect(self.db_path) as db:
            # Enable foreign keys
            await db.execute("PRAGMA foreign_keys = ON")
            
            # Create source instances table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS source_instances (
                    source_id TEXT PRIMARY KEY,
                    plugin_id TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    config TEXT NOT NULL,
                    weight REAL NOT NULL DEFAULT 1.0,
                    sentiment_polarity TEXT NOT NULL,
                    schedule TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # Create distilled snapshots table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS distilled_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    sentiment REAL NOT NULL,
                    sentiment_confidence REAL NOT NULL,
                    volatility REAL NOT NULL,
                    terms TEXT NOT NULL,
                    term_entropy REAL NOT NULL,
                    anomaly_score REAL NOT NULL,
                    coverage REAL NOT NULL,
                    metadata TEXT,
                    FOREIGN KEY (source_id) REFERENCES source_instances (source_id)
                        ON DELETE CASCADE
                )
            """)
            
            # Create index on source_id and timestamp for efficient queries
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_snapshots_source_time 
                ON distilled_snapshots (source_id, timestamp DESC)
            """)
            
            await db.commit()
        
        self._initialized = True
        print(f"Database initialized: {self.db_path}")
    
    # Source Instance Operations
    
    async def create_source(self, source: SourceInstance) -> None:
        """
        Create a new source instance.
        
        Args:
            source: SourceInstance to create
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO source_instances (
                    source_id, plugin_id, display_name, enabled, config,
                    weight, sentiment_polarity, schedule, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(source.source_id),
                source.plugin_id,
                source.display_name,
                1 if source.enabled else 0,
                json.dumps(source.config),
                source.weight,
                source.sentiment_polarity.value,
                source.schedule,
                source.created_at.isoformat(),
                datetime.utcnow().isoformat()
            ))
            await db.commit()
    
    async def get_source(self, source_id: UUID) -> Optional[SourceInstance]:
        """
        Get a source instance by ID.
        
        Args:
            source_id: UUID of the source
            
        Returns:
            SourceInstance or None if not found
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM source_instances WHERE source_id = ?
            """, (str(source_id),))
            row = await cursor.fetchone()
            
            if row:
                return self._row_to_source(row)
            return None
    
    async def list_sources(self, enabled_only: bool = False) -> list[SourceInstance]:
        """
        List all source instances.
        
        Args:
            enabled_only: If True, return only enabled sources
            
        Returns:
            List of SourceInstance objects
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            query = "SELECT * FROM source_instances"
            if enabled_only:
                query += " WHERE enabled = 1"
            query += " ORDER BY created_at DESC"
            
            cursor = await db.execute(query)
            rows = await cursor.fetchall()
            
            return [self._row_to_source(row) for row in rows]
    
    async def update_source(self, source: SourceInstance) -> None:
        """
        Update an existing source instance.
        
        Args:
            source: SourceInstance with updated values
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE source_instances
                SET plugin_id = ?, display_name = ?, enabled = ?, config = ?,
                    weight = ?, sentiment_polarity = ?, schedule = ?, updated_at = ?
                WHERE source_id = ?
            """, (
                source.plugin_id,
                source.display_name,
                1 if source.enabled else 0,
                json.dumps(source.config),
                source.weight,
                source.sentiment_polarity.value,
                source.schedule,
                datetime.utcnow().isoformat(),
                str(source.source_id)
            ))
            await db.commit()
    
    async def delete_source(self, source_id: UUID) -> None:
        """
        Delete a source instance and all its snapshots.
        
        Args:
            source_id: UUID of the source to delete
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                DELETE FROM source_instances WHERE source_id = ?
            """, (str(source_id),))
            await db.commit()
    
    # Distilled Snapshot Operations
    
    async def save_snapshot(self, snapshot: DistilledSnapshot) -> None:
        """
        Save a distilled snapshot.
        
        Snapshots are append-only and immutable.
        
        Args:
            snapshot: DistilledSnapshot to persist
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO distilled_snapshots (
                    source_id, timestamp, sentiment, sentiment_confidence,
                    volatility, terms, term_entropy, anomaly_score, coverage, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(snapshot.source_id),
                snapshot.timestamp.isoformat(),
                snapshot.sentiment,
                snapshot.sentiment_confidence,
                snapshot.volatility,
                json.dumps([term.model_dump() for term in snapshot.terms]),
                snapshot.term_entropy,
                snapshot.anomaly_score,
                snapshot.coverage,
                json.dumps(snapshot.metadata) if snapshot.metadata else None
            ))
            await db.commit()
    
    async def get_latest_snapshot(
        self,
        source_id: UUID
    ) -> Optional[DistilledSnapshot]:
        """
        Get the most recent snapshot for a source.
        
        Args:
            source_id: UUID of the source
            
        Returns:
            DistilledSnapshot or None if no snapshots exist
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM distilled_snapshots
                WHERE source_id = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (str(source_id),))
            row = await cursor.fetchone()
            
            if row:
                return self._row_to_snapshot(row)
            return None
    
    async def get_snapshot_history(
        self,
        source_id: UUID,
        limit: int = 50
    ) -> list[DistilledSnapshot]:
        """
        Get recent snapshots for a source.
        
        Args:
            source_id: UUID of the source
            limit: Maximum number of snapshots to return
            
        Returns:
            List of DistilledSnapshot objects, newest first
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM distilled_snapshots
                WHERE source_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (str(source_id), limit))
            rows = await cursor.fetchall()
            
            return [self._row_to_snapshot(row) for row in rows]
    
    async def get_all_latest_snapshots(self) -> list[DistilledSnapshot]:
        """
        Get the latest snapshot for each source.
        
        Used for global aggregation.
        
        Returns:
            List of DistilledSnapshot objects
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT ds.*
                FROM distilled_snapshots ds
                INNER JOIN (
                    SELECT source_id, MAX(timestamp) as max_timestamp
                    FROM distilled_snapshots
                    GROUP BY source_id
                ) latest ON ds.source_id = latest.source_id 
                    AND ds.timestamp = latest.max_timestamp
            """)
            rows = await cursor.fetchall()
            
            return [self._row_to_snapshot(row) for row in rows]
    
    # Helper methods
    
    def _row_to_source(self, row: aiosqlite.Row) -> SourceInstance:
        """Convert database row to SourceInstance."""
        return SourceInstance(
            source_id=UUID(row["source_id"]),
            plugin_id=row["plugin_id"],
            display_name=row["display_name"],
            enabled=bool(row["enabled"]),
            config=json.loads(row["config"]),
            weight=row["weight"],
            sentiment_polarity=row["sentiment_polarity"],
            schedule=row["schedule"],
            created_at=datetime.fromisoformat(row["created_at"])
        )
    
    def _row_to_snapshot(self, row: aiosqlite.Row) -> DistilledSnapshot:
        """Convert database row to DistilledSnapshot."""
        terms_data = json.loads(row["terms"])
        terms = [TermStat(**term) for term in terms_data]
        
        metadata = None
        if row["metadata"]:
            metadata = json.loads(row["metadata"])
        
        return DistilledSnapshot(
            source_id=UUID(row["source_id"]),
            timestamp=datetime.fromisoformat(row["timestamp"]),
            sentiment=row["sentiment"],
            sentiment_confidence=row["sentiment_confidence"],
            volatility=row["volatility"],
            terms=terms,
            term_entropy=row["term_entropy"],
            anomaly_score=row["anomaly_score"],
            coverage=row["coverage"],
            metadata=metadata
        )
