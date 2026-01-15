# 1. Architectural Clarification (Non-Negotiable Principles)

Before schemas, lock these rules:

1. **Plugins define capability; instances define intent**

   * *Plugin* = code + schema + heuristics
   * *Source instance* = configuration + identity + weight

2. **Raw data is ephemeral**

   * Raw payloads exist only during a collection run
   * They may be cached briefly for debugging, never persisted long-term

3. **Distilled data is canonical**

   * All storage, aggregation, and UI reads operate on distilled artifacts

4. **Term data is not “raw”**

   * Extracted terms, frequencies, and embeddings are *distillates*
   * They are safe to store and necessary for trend analysis

If you violate #4, your word-cloud and drift logic will collapse later.

---

# 2. High-Level Data Model

You need **four primary entities**:

```
Plugin
SourceInstance
Snapshot
Aggregation
```

Everything else hangs off these.

---

# 3. Plugin Definition Schema (Code-Level Contract)

A plugin is a **versioned capability provider**.

```python
class PluginDefinition(BaseModel):
    plugin_id: str                  # "reddit_feed"
    plugin_version: str             # semver
    display_name: str               # "Reddit Feed"
    description: str
    source_category: Enum           # TEXT | NUMERIC | EVENT
    config_schema: JSONSchema       # validated at instance creation
    output_schema_version: str
```

**Key point**
`config_schema` is what allows the UI to dynamically render “Add Source” forms.

Example (Reddit Feed):

```json
{
  "type": "object",
  "properties": {
    "subreddit": {"type": "string"},
    "sort": {"enum": ["hot", "new", "top"]},
    "limit": {"type": "integer", "minimum": 5, "maximum": 100}
  },
  "required": ["subreddit"]
}
```

No hardcoded UI logic. Ever.

---

# 4. Source Instance Schema (User-Created Objects)

This is what the central tracker actually runs.

```python
class SourceInstance(BaseModel):
    source_id: UUID
    plugin_id: str
    display_name: str
    enabled: bool

    config: dict                    # validated against plugin schema

    weight: float                   # contribution to global index
    sentiment_polarity: Enum        # POSITIVE | NEGATIVE | NEUTRAL | BIDIRECTIONAL

    schedule: CronSpec
    created_at: datetime
```

**Why polarity matters**

* Some numeric sources worsen when they rise (VIX)
* Some improve when they rise (market breadth)

Do NOT infer this later.

---

# 5. Collection Lifecycle (Important Separation)

Each run produces:

```
RawSnapshot → DistilledSnapshot
```

RawSnapshot is in-memory or short-lived cache only.

---

# 6. Raw Snapshot (Ephemeral, Plugin-Specific)

Plugins may define arbitrary raw formats.

```python
class RawSnapshot(BaseModel):
    source_id: UUID
    collected_at: datetime
    payload: Any                    # plugin-private
    diagnostics: dict               # fetch time, errors, completeness
```

This allows:

* Debugging
* Health checks
* No schema lock-in

Raw snapshots are **never queried by the UI**.

---

# 7. Distilled Snapshot (Canonical, Stored)

This is the most important schema.

```python
class DistilledSnapshot(BaseModel):
    source_id: UUID
    timestamp: datetime

    sentiment: float                # -1.0 → +1.0
    sentiment_confidence: float     # 0.0 → 1.0
    volatility: float               # normalized 0.0 → 1.0

    terms: list["TermStat"]
    term_entropy: float

    anomaly_score: float            # deviation vs rolling baseline

    coverage: float                 # % of expected data retrieved
```

### TermStat schema

```python
class TermStat(BaseModel):
    term: str
    weight: float                   # tf-idf or similar
    polarity: float                 # -1 → +1
    novelty: float                  # new vs baseline
```

**This is not raw text.**
It is already interpreted, normalized, and safe to persist.

---

# 8. Why This Term Model Will Survive

This structure supports:

* Word clouds (weight)
* Sentiment coloring (polarity)
* Trend detection (novelty)
* Cross-source correlation (shared terms)

If you store “just words”, you will regret it.

---

# 9. Aggregation Schema (Derived, Recomputable)

Aggregations should be reproducible from snapshots.

```python
class GlobalAggregation(BaseModel):
    timestamp: datetime

    global_sentiment: float
    global_volatility: float
    confidence: float

    contributing_sources: list["SourceContribution"]
    dominant_terms: list[TermStat]
```

```python
class SourceContribution(BaseModel):
    source_id: UUID
    weighted_sentiment: float
    influence: float
```

You may persist this for performance, but you should be able to rebuild it.

---

# 10. Trend & Drift Tables (Optional but Smart)

If you want speed later:

```python
class TermTrend(BaseModel):
    term: str
    first_seen: datetime
    peak_weight: float
    decay_rate: float
    cross_source_count: int
```

These are derived artifacts. Treat them as caches.

---

# 11. Plugin Interface (Concrete)

```python
class Plugin:
    definition: PluginDefinition

    def collect(self, instance: SourceInstance) -> RawSnapshot:
        ...

    def distill(
        self,
        raw: RawSnapshot,
        history: list[DistilledSnapshot]
    ) -> DistilledSnapshot:
        ...

    def healthcheck(self, instance: SourceInstance) -> PluginHealth:
        ...
```

**History is passed in** so plugins can compute:

* Novelty
* Baselines
* Entropy shifts

Do not centralize that logic; it belongs in the plugin.

---

# 12. Storage Strategy (Opinionated)

* SQLite or Postgres
* Append-only snapshots
* Indexed by `(source_id, timestamp)`
* No updates, no deletes (except retention policies)

Time-series systems are optional, not required.

---

# 13. Why This Will Not Need Redesign

* UI driven by schemas, not hardcoded forms
* Plugins encapsulate meaning
* Terms are first-class distillates
* Aggregations are cleanly separated
* Opinionated logic is localized

If you ever add:

* Podcasts
* Video captions
* Transcripts
* Sensor data

They will still fit.
