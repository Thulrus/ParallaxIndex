"""
Core schemas for Parallax Index.

These schemas define the canonical data structures for the system.
All schemas are designed to be stable across versions.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class SourceCategory(str, Enum):
    """
    Category of data source.
    
    - TEXT: Sources that produce textual content (articles, social media, etc.)
    - NUMERIC: Sources that produce numeric indices (stock prices, indicators, etc.)
    - EVENT: Sources that track discrete events (protests, policy changes, etc.)
    """
    TEXT = "TEXT"
    NUMERIC = "NUMERIC"
    EVENT = "EVENT"


class SentimentPolarity(str, Enum):
    """
    Expected sentiment polarity of a source.
    
    - POSITIVE_IS_GOOD: Higher values indicate positive sentiment
    - NEGATIVE_IS_GOOD: Lower values indicate positive sentiment (e.g., unemployment rate)
    - NEUTRAL: No inherent directional interpretation
    """
    POSITIVE_IS_GOOD = "POSITIVE_IS_GOOD"
    NEGATIVE_IS_GOOD = "NEGATIVE_IS_GOOD"
    NEUTRAL = "NEUTRAL"


class PluginDefinition(BaseModel):
    """
    Defines a plugin type that can collect and distill data.
    
    Plugins are registered at startup and define the capabilities
    and configuration schema for a type of data source.
    """
    plugin_id: str = Field(
        description="Unique identifier for this plugin type (e.g., 'numeric_index')"
    )
    plugin_version: str = Field(
        description="Version of the plugin implementation (semver recommended)"
    )
    display_name: str = Field(
        description="Human-readable name shown in the UI"
    )
    description: str = Field(
        description="Detailed description of what this plugin does"
    )
    source_category: SourceCategory = Field(
        description="Category of data this plugin handles"
    )
    config_schema: dict[str, Any] = Field(
        description="JSON Schema defining required configuration parameters"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "plugin_id": "numeric_index",
                "plugin_version": "1.0.0",
                "display_name": "Numeric Index",
                "description": "Tracks a single numeric value from a URL",
                "source_category": "NUMERIC",
                "config_schema": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "format": "uri"},
                        "baseline": {"type": "number"}
                    },
                    "required": ["url"]
                }
            }
        }


class SourceInstance(BaseModel):
    """
    A configured instance of a plugin.
    
    This represents a user-configured data source that will be
    periodically collected and distilled according to its schedule.
    """
    source_id: UUID = Field(default_factory=uuid4)
    plugin_id: str = Field(
        description="ID of the plugin this instance uses"
    )
    display_name: str = Field(
        description="User-provided name for this source"
    )
    enabled: bool = Field(
        default=True,
        description="Whether this source is actively being collected"
    )
    config: dict[str, Any] = Field(
        description="Configuration values as defined by plugin schema"
    )
    weight: float = Field(
        default=1.0,
        ge=0.0,
        le=10.0,
        description="Weight of this source in global aggregation (0-10)"
    )
    sentiment_polarity: SentimentPolarity = Field(
        default=SentimentPolarity.POSITIVE_IS_GOOD,
        description="How to interpret sentiment direction"
    )
    schedule: str = Field(
        default="0 * * * *",  # Every hour at minute 0
        description="Cron-style schedule for collection"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "source_id": "550e8400-e29b-41d4-a716-446655440000",
                "plugin_id": "numeric_index",
                "display_name": "S&P 500 Index",
                "enabled": True,
                "config": {
                    "url": "https://api.example.com/sp500",
                    "baseline": 4000.0
                },
                "weight": 2.0,
                "sentiment_polarity": "POSITIVE_IS_GOOD",
                "schedule": "0 * * * *",
                "created_at": "2026-01-14T12:00:00Z"
            }
        }


class RawSnapshot(BaseModel):
    """
    Ephemeral snapshot of raw collected data.
    
    Raw snapshots are NOT persisted long-term. They exist only
    during the collect -> distill pipeline and are then discarded.
    """
    source_id: UUID = Field(
        description="ID of the source that collected this data"
    )
    collected_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this data was collected"
    )
    payload: Any = Field(
        description="Raw data in plugin-specific format"
    )
    diagnostics: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata about collection (response time, errors, etc.)"
    )


class TermStat(BaseModel):
    """
    Statistical information about a term extracted from a snapshot.
    
    Terms are extracted entities that may persist across snapshots
    to track emergence and decline of concepts.
    """
    term: str = Field(
        description="The extracted term or phrase"
    )
    weight: float = Field(
        ge=0.0,
        le=1.0,
        description="Relative importance/frequency (0-1)"
    )
    polarity: float = Field(
        ge=-1.0,
        le=1.0,
        description="Sentiment polarity of this term (-1 to +1)"
    )
    novelty: float = Field(
        ge=0.0,
        le=1.0,
        description="How novel/unexpected this term is (0-1)"
    )


class DistilledSnapshot(BaseModel):
    """
    Canonical distilled snapshot persisted to storage.
    
    This is the fundamental unit of stored data. All analysis
    and aggregation is performed on distilled snapshots.
    
    These records are append-only and immutable.
    """
    source_id: UUID = Field(
        description="ID of the source this snapshot belongs to"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this snapshot was created"
    )
    sentiment: float = Field(
        ge=-1.0,
        le=1.0,
        description="Overall sentiment score (-1=very negative to +1=very positive)"
    )
    sentiment_confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence in the sentiment measurement (0-1)"
    )
    volatility: float = Field(
        ge=0.0,
        description="Measure of how much sentiment has changed recently"
    )
    terms: list[TermStat] = Field(
        default_factory=list,
        description="Extracted terms with statistics (may be empty for numeric sources)"
    )
    term_entropy: float = Field(
        ge=0.0,
        description="Entropy of term distribution (higher = more diverse)"
    )
    anomaly_score: float = Field(
        ge=0.0,
        le=1.0,
        description="How anomalous this snapshot is compared to history (0-1)"
    )
    coverage: float = Field(
        ge=0.0,
        le=1.0,
        description="Data quality/completeness metric (0-1)"
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Plugin-specific metadata for display purposes (e.g., current value, min/max)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "source_id": "550e8400-e29b-41d4-a716-446655440000",
                "timestamp": "2026-01-14T12:00:00Z",
                "sentiment": 0.35,
                "sentiment_confidence": 0.8,
                "volatility": 0.12,
                "terms": [
                    {
                        "term": "market growth",
                        "weight": 0.8,
                        "polarity": 0.6,
                        "novelty": 0.3
                    }
                ],
                "term_entropy": 2.4,
                "anomaly_score": 0.15,
                "coverage": 1.0
            }
        }


class GlobalSentiment(BaseModel):
    """
    Aggregated global sentiment computed from all active sources.
    
    This is computed on-demand from the latest distilled snapshots.
    """
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this aggregation was computed"
    )
    global_sentiment: float = Field(
        ge=-1.0,
        le=1.0,
        description="Weighted average sentiment across all sources"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Overall confidence in the global metric"
    )
    source_count: int = Field(
        description="Number of sources included in aggregation"
    )
    volatility: float = Field(
        ge=0.0,
        description="Overall volatility across all sources"
    )
