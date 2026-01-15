"""
Plugin base interface for Parallax Index.

All data source plugins must implement this interface to be compatible
with the core tracking system.
"""

from abc import ABC, abstractmethod
from typing import Optional

from core.schemas import (
    DistilledSnapshot,
    PluginDefinition,
    RawSnapshot,
    SourceInstance,
)


class PluginBase(ABC):
    """
    Base class for all data source plugins.
    
    Plugins define how to:
    1. Collect raw data from a source
    2. Distill raw data into normalized sentiment snapshots
    3. Validate source health
    
    Each plugin class represents a TYPE of data source (e.g., "numeric_index").
    Individual SourceInstances provide the configuration for specific instances.
    """
    
    @abstractmethod
    def get_definition(self) -> PluginDefinition:
        """
        Return the plugin definition metadata.
        
        This defines the plugin's identity, capabilities, and configuration schema.
        Called once at plugin registration.
        
        Returns:
            PluginDefinition with complete metadata
        """
        pass
    
    @abstractmethod
    async def collect(self, instance: SourceInstance) -> RawSnapshot:
        """
        Collect raw data from the configured source.
        
        This method should:
        - Fetch data from the external source using instance.config
        - Package it into a RawSnapshot
        - Include diagnostic information (timing, errors, etc.)
        - NOT persist the raw data
        
        Args:
            instance: The configured source instance to collect from
            
        Returns:
            RawSnapshot containing ephemeral raw data
            
        Raises:
            Exception: If collection fails (will be caught and logged by scheduler)
        """
        pass
    
    @abstractmethod
    async def distill(
        self,
        raw: RawSnapshot,
        history: list[DistilledSnapshot]
    ) -> DistilledSnapshot:
        """
        Distill raw data into a normalized sentiment snapshot.
        
        This method should:
        - Extract sentiment from raw.payload
        - Calculate volatility using history
        - Extract terms if applicable (may be empty list)
        - Calculate anomaly score relative to history
        - Set coverage based on data quality
        
        The distillation process can use historical context to detect
        changes, anomalies, and trends.
        
        Args:
            raw: The raw snapshot to distill
            history: Recent distilled snapshots for this source (may be empty)
            
        Returns:
            DistilledSnapshot ready for persistence
        """
        pass
    
    async def healthcheck(self, instance: SourceInstance) -> tuple[bool, str]:
        """
        Check if the source is healthy and accessible.
        
        Default implementation attempts a collection and checks for success.
        Plugins may override for more sophisticated health checks.
        
        Args:
            instance: The source instance to check
            
        Returns:
            Tuple of (is_healthy, message)
        """
        try:
            raw = await self.collect(instance)
            if raw.payload is None:
                return False, "Collection returned no data"
            return True, "Source is healthy"
        except Exception as e:
            return False, f"Health check failed: {str(e)}"
    
    def validate_config(self, config: dict) -> tuple[bool, str]:
        """
        Validate that a configuration dict matches the plugin's schema.
        
        Default implementation does basic type checking against config_schema.
        Plugins may override for custom validation logic.
        
        Args:
            config: Configuration dict to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        definition = self.get_definition()
        schema = definition.config_schema
        
        # Basic validation: check required fields
        if "required" in schema:
            for field in schema["required"]:
                if field not in config:
                    return False, f"Missing required field: {field}"
        
        return True, "Configuration is valid"
