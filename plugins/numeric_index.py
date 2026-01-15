"""
Numeric Index Plugin for Parallax Index.

Tracks a single numeric value from a URL and determines sentiment
based on whether the value increased or decreased from a baseline.
"""

import math
from datetime import datetime, timedelta
from typing import Any

import httpx

from core.schemas import (DistilledSnapshot, PluginDefinition, RawSnapshot,
                          SourceCategory, SourceInstance, TermStat)
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
            plugin_version="1.0.0",
            display_name="Numeric Index",
            description=(
                "Tracks a single numeric value from a URL. "
                "Determines sentiment based on whether the value increases "
                "or decreases compared to baseline or previous readings."
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
                    "baseline": {
                        "type": "number",
                        "description": "Baseline value for comparison (optional)"
                    },
                    "json_path": {
                        "type": "string",
                        "description": "JSON path to extract value (e.g., 'data.value')"
                    },
                    "timeout": {
                        "type": "integer",
                        "default": 10,
                        "description": "Request timeout in seconds"
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
        history: list[DistilledSnapshot]
    ) -> DistilledSnapshot:
        """
        Distill numeric value into sentiment snapshot.
        
        Sentiment is determined by:
        - Change from baseline (if configured) or previous value
        - Magnitude of change determines confidence
        - Volatility tracks recent fluctuations
        """
        current_value = raw.payload["value"]
        
        # Get instance config to check for baseline
        # (In practice, we'd pass this in or store it, but for MVP we calculate from history)
        
        # Determine baseline and previous value
        baseline = None
        previous_value = None
        
        if history:
            # Use most recent snapshot as previous
            previous_value = self._extract_value_from_history(history[-1])
            
            # Use oldest value as baseline if no explicit baseline
            if len(history) >= 1:
                baseline = self._extract_value_from_history(history[0])
        
        # Calculate sentiment
        if previous_value is not None:
            change = current_value - previous_value
            percent_change = (change / previous_value) if previous_value != 0 else 0
            
            # Sentiment based on percent change
            # ±5% = ±0.5 sentiment, ±10% = ±1.0 sentiment
            sentiment = max(-1.0, min(1.0, percent_change * 10))
            
            # Confidence based on magnitude of change
            confidence = min(1.0, abs(percent_change) * 5)
            if confidence < 0.1:
                confidence = 0.5  # Moderate confidence for small changes
        else:
            # First reading - neutral sentiment
            sentiment = 0.0
            confidence = 0.5
        
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
        
        min_value = min(all_values)
        max_value = max(all_values)
        
        # Build metadata for display
        metadata = {
            "current_value": current_value,
            "min_value": min_value,
            "max_value": max_value,
            "sample_count": len(history) + 1,
            "previous_value": previous_value,
            "baseline": baseline
        }
        
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
