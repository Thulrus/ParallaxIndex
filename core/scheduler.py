"""
Scheduler for Parallax Index.

Manages periodic collection and distillation of data sources.
"""

import asyncio
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from core.schemas import RawSnapshot
from plugins.registry import get_registry
from storage.database import Database


class CollectionScheduler:
    """
    Scheduler for periodic data collection and distillation.
    
    Manages scheduled tasks for each enabled source instance.
    """
    
    def __init__(self, db: Database):
        """
        Initialize scheduler.
        
        Args:
            db: Database instance
        """
        self.db = db
        self.scheduler = AsyncIOScheduler()
        self.registry = get_registry()
        self._job_ids: dict[str, str] = {}  # source_id -> job_id mapping
    
    async def start(self) -> None:
        """
        Start the scheduler.
        
        Loads all enabled sources and schedules their collection jobs.
        """
        # Load and schedule all enabled sources
        await self._schedule_all_sources()
        
        # Start the scheduler
        self.scheduler.start()
        print("Collection scheduler started")
    
    def stop(self) -> None:
        """Stop the scheduler."""
        self.scheduler.shutdown(wait=False)
        print("Collection scheduler stopped")
    
    async def _schedule_all_sources(self) -> None:
        """Schedule collection jobs for all enabled sources."""
        sources = await self.db.list_sources(enabled_only=True)
        
        for source in sources:
            await self.schedule_source(str(source.source_id))
    
    async def schedule_source(self, source_id: str) -> None:
        """
        Schedule a source for periodic collection.
        
        Args:
            source_id: UUID string of the source
        """
        from uuid import UUID
        source = await self.db.get_source(UUID(source_id))
        
        if not source or not source.enabled:
            return
        
        # Remove existing job if any
        if source_id in self._job_ids:
            self.scheduler.remove_job(self._job_ids[source_id])
        
        # Parse schedule (cron format)
        trigger = CronTrigger.from_crontab(source.schedule)
        
        # Add job
        job = self.scheduler.add_job(
            self._collect_and_distill,
            trigger=trigger,
            args=[source_id],
            id=f"collect_{source_id}",
            name=f"Collect: {source.display_name}",
            max_instances=1,  # Prevent overlapping runs
            coalesce=True  # Combine missed runs
        )
        
        self._job_ids[source_id] = job.id
        print(f"Scheduled source: {source.display_name} ({source.schedule})")
    
    async def unschedule_source(self, source_id: str) -> None:
        """
        Unschedule a source from periodic collection.
        
        Args:
            source_id: UUID string of the source
        """
        if source_id in self._job_ids:
            try:
                self.scheduler.remove_job(self._job_ids[source_id])
                del self._job_ids[source_id]
                print(f"Unscheduled source: {source_id}")
            except Exception as e:
                print(f"Error unscheduling source {source_id}: {e}")
    
    async def collect_now(self, source_id: str) -> Optional[str]:
        """
        Trigger immediate collection for a source.
        
        Args:
            source_id: UUID string of the source
            
        Returns:
            Success message or None if failed
        """
        try:
            await self._collect_and_distill(source_id)
            return f"Collection completed for {source_id}"
        except Exception as e:
            import traceback
            error_msg = f"Collection failed: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            return error_msg
    
    async def _collect_and_distill(self, source_id: str) -> None:
        """
        Execute collection and distillation for a source.
        
        This is the core pipeline:
        1. Load source instance
        2. Get plugin
        3. Collect raw data
        4. Get historical context
        5. Distill into snapshot
        6. Save snapshot
        7. Discard raw data
        
        Args:
            source_id: UUID string of the source
        """
        start_time = datetime.utcnow()
        
        try:
            # Load source
            from uuid import UUID
            source = await self.db.get_source(UUID(source_id))
            if not source:
                print(f"Source {source_id} not found")
                return
            
            if not source.enabled:
                print(f"Source {source_id} is disabled, skipping")
                return
            
            # Get plugin
            plugin = self.registry.get_plugin(source.plugin_id)
            if not plugin:
                print(f"Plugin {source.plugin_id} not found for source {source_id}")
                return
            
            # Collect raw data
            print(f"Collecting: {source.display_name}")
            raw = await plugin.collect(source)
            
            # Get history for distillation
            history = await self.db.get_snapshot_history(source.source_id, limit=50)
            
            # Distill
            distilled = await plugin.distill(raw, list(reversed(history)), source)
            
            # Save distilled snapshot
            await self.db.save_snapshot(distilled)
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            print(
                f"✓ {source.display_name}: "
                f"sentiment={distilled.sentiment:.3f}, "
                f"confidence={distilled.sentiment_confidence:.3f}, "
                f"volatility={distilled.volatility:.3f} "
                f"({duration:.2f}s)"
            )
            
            # Raw data is now discarded (Python GC handles this)
        
        except Exception as e:
            print(f"✗ Collection failed for {source_id}: {e}")
            # In production, would log to monitoring system
