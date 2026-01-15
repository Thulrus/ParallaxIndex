"""
Numeric Index Plugin for Parallax Index.

Tracks a single numeric value from a URL and determines sentiment
based on whether the value increased or decreased from a baseline.
"""

import math
from datetime import datetime, timedelta
from typing import Any

import httpx

from core.schemas import (
    DistilledSnapshot,
    PluginDefinition,
    RawSnapshot,
    SourceCategory,
    SourceInstance,
    TermStat,
)
from plugins.base import PluginBase


class NumericIndexPlugin(PluginBase):
    """
    Plugin for tracking numeric indices (stock prices, economic indicators, etc.).
    
    Configuration parameters:
    - url: URL that returns a numeric value (JSON or plaintext)
    - baseline: Optional baseline value for comparison (defaults to first reading)
    - json_path: Optional JSON path if response is JSON (e.g., "data.value")
    """
    
    def get_definition(self) -> PluginDefinition:
        """Return plugin definition."""
        return PluginDefinition(
            plugin_id="numeric_index",
            plugin_version="2.0.0",
            display_name="Numeric Index",
            description=(
                "Tracks a single numeric value from a URL. "
                "Calculates sentiment based on configurable range and polarity modes."
            ),
            source_category=SourceCategory.NUMERIC,
            config_schema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "format": "uri",
                        "description": "URL that returns a numeric value"
                    },
                    "json_path": {
                        "type": "string",
                        "description": "JSON path to extract value (e.g., 'data.value', 'data[0]')"
                    },
                    "timeout": {
                        "type": "integer",
                        "default": 10,
                        "description": "Request timeout in seconds"
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["higher_is_better", "lower_is_better", "target_is_best", "change_tracking"],
                        "default": "change_tracking",
                        "description": "Sentiment calculation mode"
                    },
                    "min_value": {
                        "type": "number",
                        "description": "Minimum value of expected range (required for range-based modes)"
                    },
                    "max_value": {
                        "type": "number",
                        "description": "Maximum value of expected range (required for range-based modes)"
                    },
                    "midpoint": {
                        "type": "number",
                        "description": "Neutral/target value (defaults to middle of range if not specified)"
                    }
                },
                "required": ["url"]
            }
        )
    
    async def collect(self, instance: SourceInstance) -> RawSnapshot:
        """
        Fetch numeric value from the configured URL.
        
        Supports both plaintext numeric responses and JSON responses.
        """
        url = instance.config["url"]
        timeout = instance.config.get("timeout", 10)
        json_path = instance.config.get("json_path")
        
        start_time = datetime.utcnow()
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=timeout)
                response.raise_for_status()
                
                # Try to parse as JSON first
                try:
                    data = response.json()
                    
                    # Extract value from JSON path if specified
                    if json_path:
                        value = self._extract_json_path(data, json_path)
                    else:
                        # If no path, assume the response is a single number or has a 'value' field
                        if isinstance(data, (int, float)):
                            value = float(data)
                        elif isinstance(data, dict) and 'value' in data:
                            value = float(data['value'])
                        else:
                            raise ValueError("Cannot determine numeric value from JSON response")
                    
                except (ValueError, KeyError) as e:
                    # Not JSON, try to parse as plaintext number
                    text = response.text.strip()
                    try:
                        value = float(text)
                    except ValueError:
                        raise ValueError(f"Cannot parse response as number: {text[:100]}")
                
                end_time = datetime.utcnow()
                
                return RawSnapshot(
                    source_id=instance.source_id,
                    collected_at=datetime.utcnow(),
                    payload={"value": value},
                    diagnostics={
                        "response_time_ms": (end_time - start_time).total_seconds() * 1000,
                        "status_code": response.status_code,
                        "content_type": response.headers.get("content-type", "unknown")
                    }
                )
        
        except httpx.TimeoutException:
            raise Exception(f"Request to {url} timed out after {timeout}s")
        except httpx.HTTPError as e:
            raise Exception(f"HTTP error fetching {url}: {e}")
        except Exception as e:
            raise Exception(f"Failed to collect data: {e}")
    
    def _extract_json_path(self, data: Any, path: str) -> float:
        """
        Extract value from nested JSON using dot notation and array indices.
        
        Examples:
            "data.value" -> data["value"]
            "results[0].score" -> results[0]["score"]
            "daily.temperature_2m_max[0]" -> daily["temperature_2m_max"][0]
        
        Args:
            data: JSON data structure
            path: Dot-notation path with optional array indices
            
        Returns:
            Extracted numeric value
        """
        import re

        # Split path by dots, but handle array indices
        parts = path.split(".")
        current = data
        
        for part in parts:
            # Check if this part has array index notation: name[index]
            match = re.match(r'([^\[]+)(\[\d+\])+$', part)
            
            if match:
                # Extract name and all indices
                name = match.group(1)
                indices_str = match.group(2)
                
                # Navigate to the named field first
                if isinstance(current, dict) and name:
                    current = current[name]
                elif not name:  # Just indices, no name
                    pass
                else:
                    raise KeyError(f"Cannot navigate path '{path}' - not a dict at '{part}'")
                
                # Process all array indices [0][1][2] etc.
                for index_match in re.finditer(r'\[(\d+)\]', indices_str):
                    index = int(index_match.group(1))
                    if isinstance(current, list):
                        current = current[index]
                    else:
                        raise KeyError(f"Cannot navigate path '{path}' - not a list at index {index}")
            else:
                # Simple dict navigation
                if isinstance(current, dict):
                    current = current[part]
                else:
                    raise KeyError(f"Cannot navigate path '{path}' - not a dict at '{part}'")
        
        return float(current)
    
    async def distill(
        self,
        raw: RawSnapshot,
        history: list[DistilledSnapshot],
        instance: SourceInstance
    ) -> DistilledSnapshot:
        """
        Distill a raw numeric reading into a sentiment snapshot.
        
        Sentiment calculation depends on configured mode:
        - higher_is_better: Higher values = positive sentiment
        - lower_is_better: Lower values = positive sentiment
        - target_is_best: Closer to midpoint = positive sentiment
        - change_tracking: Based on percent change from previous value
        """
        current_value = raw.payload["value"]
        config = instance.config
        mode = config.get("mode", "change_tracking")
        
        # Get previous value for reference
        previous_value = None
        baseline = None
        if history:
            previous_value = self._extract_value_from_history(history[-1])
            if len(history) >= 1:
                baseline = self._extract_value_from_history(history[0])
        
        # Calculate sentiment based on mode
        if mode == "change_tracking":
            sentiment, confidence = self._calculate_change_sentiment(current_value, previous_value)
        else:
            # Range-based modes
            min_value = config.get("min_value")
            max_value = config.get("max_value")
            midpoint = config.get("midpoint")
            
            if min_value is None or max_value is None:
                # Fallback to change tracking if range not configured
                sentiment, confidence = self._calculate_change_sentiment(current_value, previous_value)
            else:
                # Calculate midpoint if not specified
                if midpoint is None:
                    midpoint = (min_value + max_value) / 2
                
                sentiment, confidence = self._calculate_range_sentiment(
                    current_value, min_value, max_value, midpoint, mode
                )
        
        # Calculate volatility from recent history
        volatility = self._calculate_volatility(history, current_value)
        
        # Calculate anomaly score
        anomaly_score = self._calculate_anomaly(history, current_value)
        
        # Store the numeric value in terms array for future reference
        # Encode as string in the term field
        terms = [
            TermStat(
                term=f"value:{current_value}",  # Store value in the term name
                weight=1.0,
                polarity=0.0,  # Neutral polarity for numeric values
                novelty=0.0
            )
        ]
        
        # Calculate min/max from history
        all_values = [current_value]
        if history:
            all_values.extend([
                self._extract_value_from_history(s) for s in history
            ])
        
        observed_min = min(all_values)
        observed_max = max(all_values)
        
        # Build metadata for display
        metadata = {
            "current_value": current_value,
            "observed_min": observed_min,
            "observed_max": observed_max,
            "sample_count": len(history) + 1,
            "previous_value": previous_value,
            "baseline": baseline,
            "mode": mode
        }
        
        # Add range configuration if using range-based mode
        if mode != "change_tracking":
            metadata["configured_min"] = config.get("min_value")
            metadata["configured_max"] = config.get("max_value")
            metadata["configured_midpoint"] = config.get("midpoint")
        
        return DistilledSnapshot(
            source_id=raw.source_id,
            timestamp=raw.collected_at,
            sentiment=sentiment,
            sentiment_confidence=confidence,
            volatility=volatility,
            terms=terms,
            term_entropy=0.0,
            anomaly_score=anomaly_score,
            coverage=1.0,
            metadata=metadata
        )
    
    def _calculate_change_sentiment(self, current_value: float, previous_value: float | None) -> tuple[float, float]:
        """
        Calculate sentiment based on percent change from previous value.
        
        Returns:
            Tuple of (sentiment, confidence)
        """
        if previous_value is not None and previous_value != 0:
            change = current_value - previous_value
            percent_change = change / previous_value
            
            # ±5% = ±0.5 sentiment, ±10% = ±1.0 sentiment
            sentiment = max(-1.0, min(1.0, percent_change * 10))
            
            # Confidence based on magnitude of change
            confidence = min(1.0, abs(percent_change) * 5)
            if confidence < 0.1:
                confidence = 0.5
        else:
            # First reading - neutral sentiment
            sentiment = 0.0
            confidence = 0.5
        
        return sentiment, confidence
    
    def _calculate_range_sentiment(
        self,
        value: float,
        min_value: float,
        max_value: float,
        midpoint: float,
        mode: str
    ) -> tuple[float, float]:
        """
        Calculate sentiment based on position within a range.
        
        Args:
            value: Current value
            min_value: Minimum of range
            max_value: Maximum of range
            midpoint: Neutral/target value
            mode: 'higher_is_better', 'lower_is_better', or 'target_is_best'
        
        Returns:
            Tuple of (sentiment, confidence)
        """
        if mode == "higher_is_better":
            # At or above max: sentiment = 1
            # At midpoint: sentiment = 0
            # At or below min: sentiment = -1
            if value >= max_value:
                sentiment = 1.0
            elif value <= min_value:
                sentiment = -1.0
            elif value >= midpoint:
                # Scale from 0 to 1
                sentiment = (value - midpoint) / (max_value - midpoint)
            else:
                # Scale from -1 to 0
                sentiment = (value - midpoint) / (midpoint - min_value)
            
            # High confidence when near extremes
            distance_from_mid = abs(value - midpoint)
            max_distance = max(abs(max_value - midpoint), abs(min_value - midpoint))
            confidence = min(1.0, 0.5 + (distance_from_mid / max_distance) * 0.5)
        
        elif mode == "lower_is_better":
            # Inverse of higher_is_better
            # At or below min: sentiment = 1
            # At midpoint: sentiment = 0
            # At or above max: sentiment = -1
            if value <= min_value:
                sentiment = 1.0
            elif value >= max_value:
                sentiment = -1.0
            elif value <= midpoint:
                # Scale from 1 to 0
                sentiment = (midpoint - value) / (midpoint - min_value)
            else:
                # Scale from 0 to -1
                sentiment = -(value - midpoint) / (max_value - midpoint)
            
            distance_from_mid = abs(value - midpoint)
            max_distance = max(abs(max_value - midpoint), abs(min_value - midpoint))
            confidence = min(1.0, 0.5 + (distance_from_mid / max_distance) * 0.5)
        
        elif mode == "target_is_best":
            # Being at midpoint is ideal (sentiment = 1)
            # Being at either extreme is bad (sentiment = -1)
            distance_from_target = abs(value - midpoint)
            
            if value >= midpoint:
                max_distance = max_value - midpoint
            else:
                max_distance = midpoint - min_value
            
            # Clamp value to range
            if value > max_value:
                distance_from_target = abs(max_value - midpoint)
                max_distance = max_value - midpoint
            elif value < min_value:
                distance_from_target = abs(min_value - midpoint)
                max_distance = midpoint - min_value
            
            # Sentiment decreases as we move away from target
            if max_distance > 0:
                sentiment = 1.0 - (distance_from_target / max_distance)
                # Convert to -1 to +1 range (instead of 0 to 1)
                sentiment = (sentiment * 2) - 1
            else:
                sentiment = 1.0
            
            # High confidence near extremes or target
            if distance_from_target < max_distance * 0.1:
                confidence = 0.9  # High confidence at target
            elif distance_from_target > max_distance * 0.8:
                confidence = 0.9  # High confidence at extremes
            else:
                confidence = 0.6
        else:
            # Unknown mode, return neutral
            sentiment = 0.0
            confidence = 0.5
        
        return sentiment, confidence
    
    def _extract_value_from_history(self, snapshot: DistilledSnapshot) -> float:
        """
        Extract numeric value from a historical snapshot.
        
        The value is stored in the terms array with format "value:123.45"
        
        Args:
            snapshot: Historical distilled snapshot
            
        Returns:
            The numeric value from that snapshot
        """
        # Look for the value: term
        for term in snapshot.terms:
            if term.term.startswith("value:"):
                try:
                    return float(term.term.split(":", 1)[1])
                except (ValueError, IndexError):
                    pass
        
        # Fallback if not found (for old snapshots)
        return 0.0
    
    def _calculate_volatility(
        self,
        history: list[DistilledSnapshot],
        current_value: float
    ) -> float:
        """
        Calculate volatility based on recent fluctuations.
        
        Uses standard deviation of recent sentiment changes.
        """
        if len(history) < 2:
            return 0.0
        
        # Use sentiment changes as proxy for value changes
        recent = history[-10:]  # Last 10 snapshots
        sentiments = [s.sentiment for s in recent]
        
        # Calculate standard deviation
        mean = sum(sentiments) / len(sentiments)
        variance = sum((s - mean) ** 2 for s in sentiments) / len(sentiments)
        std_dev = math.sqrt(variance)
        
        return min(1.0, std_dev * 2)  # Scale to 0-1 range
    
    def _calculate_anomaly(
        self,
        history: list[DistilledSnapshot],
        current_value: float
    ) -> float:
        """
        Calculate how anomalous the current value is.
        
        Based on z-score from recent history.
        """
        if len(history) < 3:
            return 0.0
        
        recent = history[-20:]  # Last 20 snapshots
        sentiments = [s.sentiment for s in recent]
        
        mean = sum(sentiments) / len(sentiments)
        variance = sum((s - mean) ** 2 for s in sentiments) / len(sentiments)
        std_dev = math.sqrt(variance)
        
        if std_dev == 0:
            return 0.0
        
        # Current sentiment vs historical
        current_sentiment = sentiments[-1] if sentiments else 0
        z_score = abs(current_sentiment - mean) / std_dev
        
        # Convert z-score to 0-1 range (z > 3 is very anomalous)
        return min(1.0, z_score / 3)
