"""
Aggregation engine for Parallax Index.

Combines distilled snapshots from multiple sources into global sentiment metrics.
"""

import math
from typing import Optional

from core.schemas import DistilledSnapshot, GlobalSentiment, SourceInstance
from storage.database import Database


class AggregationEngine:
    """
    Engine for aggregating source snapshots into global metrics.
    
    Implements weighted aggregation with confidence weighting.
    """
    
    def __init__(self, db: Database):
        """
        Initialize aggregation engine.
        
        Args:
            db: Database instance for fetching sources and snapshots
        """
        self.db = db
    
    async def compute_global_sentiment(self) -> Optional[GlobalSentiment]:
        """
        Compute current global sentiment from all enabled sources.
        
        Algorithm:
        1. Get latest snapshot for each enabled source
        2. Apply source weights and confidence weights
        3. Compute weighted average sentiment
        4. Calculate global volatility and confidence
        
        Returns:
            GlobalSentiment or None if no data available
        """
        # Get all enabled sources
        sources = await self.db.list_sources(enabled_only=True)
        
        if not sources:
            return None
        
        # Get latest snapshot for each source
        snapshots: list[tuple[SourceInstance, DistilledSnapshot]] = []
        
        for source in sources:
            snapshot = await self.db.get_latest_snapshot(source.source_id)
            if snapshot:
                snapshots.append((source, snapshot))
        
        if not snapshots:
            return None
        
        # Compute weighted sentiment
        total_weight = 0.0
        weighted_sentiment = 0.0
        total_volatility = 0.0
        total_confidence_weight = 0.0
        
        for source, snapshot in snapshots:
            # Effective weight is source weight * confidence
            effective_weight = source.weight * snapshot.sentiment_confidence
            
            weighted_sentiment += snapshot.sentiment * effective_weight
            total_volatility += snapshot.volatility * effective_weight
            total_weight += effective_weight
            total_confidence_weight += snapshot.sentiment_confidence * source.weight
        
        if total_weight == 0:
            return None
        
        # Normalize
        global_sentiment = weighted_sentiment / total_weight
        global_volatility = total_volatility / total_weight
        
        # Calculate global confidence (average of confidence-weighted sources)
        # Adjust down if we have very few sources
        source_count = len(snapshots)
        diversity_factor = min(1.0, source_count / 5)  # Penalize < 5 sources
        global_confidence = (total_confidence_weight / sum(s.weight for s, _ in snapshots)) * diversity_factor
        
        return GlobalSentiment(
            global_sentiment=global_sentiment,
            confidence=global_confidence,
            source_count=source_count,
            volatility=global_volatility
        )
    
    async def compute_source_contribution(
        self,
        source_id
    ) -> Optional[float]:
        """
        Compute how much a specific source contributes to global sentiment.
        
        Args:
            source_id: UUID of the source
            
        Returns:
            Contribution factor (0-1) or None if not applicable
        """
        # Get global with this source
        global_with = await self.compute_global_sentiment()
        
        if not global_with:
            return None
        
        # Temporarily disable source and recalculate
        source = await self.db.get_source(source_id)
        if not source or not source.enabled:
            return None
        
        # Get snapshot to calculate individual contribution
        snapshot = await self.db.get_latest_snapshot(source_id)
        if not snapshot:
            return None
        
        # Contribution is based on weight and sentiment deviation
        contribution = abs(snapshot.sentiment) * source.weight / 10.0
        
        return min(1.0, contribution)
    
    async def get_sentiment_trend(
        self,
        source_id,
        window_size: int = 10
    ) -> Optional[float]:
        """
        Calculate sentiment trend for a source.
        
        Args:
            source_id: UUID of the source
            window_size: Number of recent snapshots to analyze
            
        Returns:
            Trend value (-1 to +1) or None if insufficient data
            Negative = declining, Positive = improving, 0 = stable
        """
        history = await self.db.get_snapshot_history(source_id, limit=window_size)
        
        if len(history) < 3:
            return None
        
        # Reverse to get chronological order
        history = list(reversed(history))
        
        # Simple linear regression on sentiment values
        sentiments = [s.sentiment for s in history]
        n = len(sentiments)
        
        # Calculate slope
        x_mean = (n - 1) / 2
        y_mean = sum(sentiments) / n
        
        numerator = sum((i - x_mean) * (sentiments[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return 0.0
        
        slope = numerator / denominator
        
        # Normalize to -1 to +1 range
        # A slope of 0.1 per snapshot is considered strong
        return max(-1.0, min(1.0, slope * 10))
