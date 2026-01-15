# Contributing to Parallax Index

Thank you for your interest in contributing to Parallax Index! This document provides guidelines for contributing to the project.

## Ways to Contribute

### 1. Create New Plugins
The most impactful contribution! Add support for new data sources:
- TEXT category: RSS feeds, news APIs, social media
- EVENT category: Event trackers, policy changes, protests
- NUMERIC category: Additional economic indicators, metrics

See [Creating a New Plugin](#creating-a-new-plugin) below.

### 2. Enhance Core Features
- Improve aggregation algorithms
- Add visualization capabilities
- Enhance anomaly detection
- Optimize performance

### 3. Documentation
- Improve existing docs
- Add tutorials and examples
- Create video guides
- Translate documentation

### 4. Bug Fixes
- Report bugs via Issues
- Submit fixes via Pull Requests
- Add test cases

### 5. Testing
- Write unit tests
- Add integration tests
- Improve test coverage

## Development Setup

### Prerequisites
- Python 3.12 or higher
- Git
- Virtual environment tool (venv, conda, etc.)

### Setup Steps

1. **Fork the repository**
   ```bash
   # On GitHub, click "Fork" button
   ```

2. **Clone your fork**
   ```bash
   git clone https://github.com/YOUR_USERNAME/parallax-index.git
   cd parallax-index
   ```

3. **Create virtual environment**
   ```bash
   python3.12 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Verify setup**
   ```bash
   python setup_check.py
   python main.py  # Should start without errors
   ```

6. **Create feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Code Style

### Python Style Guide
- Follow **PEP 8** style guidelines
- Use **type hints** for all function parameters and returns
- Maximum line length: **100 characters** (flexible for readability)
- Use **4 spaces** for indentation (no tabs)

### Documentation Style
- Add **docstrings** to all public classes and methods
- Use **Google-style docstrings**:
  ```python
  def example_function(param1: str, param2: int) -> bool:
      """
      Brief description of function.
      
      Longer description if needed.
      
      Args:
          param1: Description of param1
          param2: Description of param2
          
      Returns:
          Description of return value
          
      Raises:
          ValueError: When param1 is empty
      """
      pass
  ```

### Naming Conventions
- **Classes**: PascalCase (e.g., `PluginBase`, `SourceInstance`)
- **Functions/Methods**: snake_case (e.g., `collect_data`, `get_snapshot`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `MAX_RETRIES`, `DEFAULT_TIMEOUT`)
- **Private methods**: Prefix with underscore (e.g., `_internal_helper`)

## Creating a New Plugin

### Step-by-Step Guide

1. **Create plugin file** in `plugins/` directory
   ```bash
   touch plugins/my_plugin.py
   ```

2. **Import base classes**
   ```python
   from plugins.base import PluginBase
   from core.schemas import (
       PluginDefinition,
       RawSnapshot,
       DistilledSnapshot,
       SourceInstance,
       SourceCategory,
       TermStat
   )
   ```

3. **Implement the plugin class**
   ```python
   class MyPlugin(PluginBase):
       """Brief description of what this plugin does."""
       
       def get_definition(self) -> PluginDefinition:
           """Return plugin metadata and config schema."""
           return PluginDefinition(
               plugin_id="my_plugin",
               plugin_version="1.0.0",
               display_name="My Data Source",
               description="Detailed description",
               source_category=SourceCategory.TEXT,  # or NUMERIC, EVENT
               config_schema={
                   "type": "object",
                   "properties": {
                       "url": {"type": "string", "format": "uri"},
                       "api_key": {"type": "string"}
                   },
                   "required": ["url"]
               }
           )
       
       async def collect(self, instance: SourceInstance) -> RawSnapshot:
           """Fetch data from the source."""
           # TODO: Implement data collection
           pass
       
       async def distill(
           self,
           raw: RawSnapshot,
           history: list[DistilledSnapshot]
       ) -> DistilledSnapshot:
           """Convert raw data to normalized snapshot."""
           # TODO: Implement distillation logic
           pass
   ```

4. **Restart application** - Plugin auto-discovered!

### Plugin Best Practices

#### Collection (`collect` method)
- Keep fast (< 5 seconds if possible)
- Handle timeouts gracefully
- Include diagnostic info (response time, status codes)
- Raise exceptions on fatal errors (scheduler will catch)
- Don't persist raw data

#### Distillation (`distill` method)
- Use `history` to calculate volatility and trends
- Set `sentiment` between -1.0 and +1.0
- Set `sentiment_confidence` based on data quality
- Extract meaningful terms only (empty list is valid)
- Calculate `anomaly_score` relative to history
- Set `coverage` based on data completeness

#### Configuration Schema
- Use JSON Schema format
- Provide clear descriptions for each field
- Mark required fields in `required` array
- Consider default values

#### Error Handling
- Validate config in `validate_config()` if custom validation needed
- Raise clear, descriptive exceptions
- Log important events

### Example: RSS Feed Plugin

```python
class RSSPlugin(PluginBase):
    """Collects articles from RSS feeds."""
    
    def get_definition(self) -> PluginDefinition:
        return PluginDefinition(
            plugin_id="rss_feed",
            plugin_version="1.0.0",
            display_name="RSS Feed",
            description="Tracks sentiment from RSS feeds",
            source_category=SourceCategory.TEXT,
            config_schema={
                "type": "object",
                "properties": {
                    "feed_url": {
                        "type": "string",
                        "format": "uri",
                        "description": "RSS feed URL"
                    },
                    "max_items": {
                        "type": "integer",
                        "default": 10,
                        "description": "Maximum articles to fetch"
                    }
                },
                "required": ["feed_url"]
            }
        )
    
    async def collect(self, instance: SourceInstance) -> RawSnapshot:
        import feedparser
        import httpx
        from datetime import datetime
        
        feed_url = instance.config["feed_url"]
        max_items = instance.config.get("max_items", 10)
        
        start = datetime.utcnow()
        
        # Fetch RSS feed
        async with httpx.AsyncClient() as client:
            response = await client.get(feed_url, timeout=10)
            response.raise_for_status()
        
        # Parse feed
        feed = feedparser.parse(response.text)
        articles = feed.entries[:max_items]
        
        end = datetime.utcnow()
        
        return RawSnapshot(
            source_id=instance.source_id,
            collected_at=datetime.utcnow(),
            payload={
                "articles": [
                    {
                        "title": entry.title,
                        "summary": entry.get("summary", ""),
                        "published": entry.get("published", "")
                    }
                    for entry in articles
                ]
            },
            diagnostics={
                "fetch_time_ms": (end - start).total_seconds() * 1000,
                "article_count": len(articles)
            }
        )
    
    async def distill(
        self,
        raw: RawSnapshot,
        history: list[DistilledSnapshot]
    ) -> DistilledSnapshot:
        articles = raw.payload["articles"]
        
        # Simple sentiment analysis (enhance with NLP library)
        positive_words = {"good", "great", "excellent", "positive", "growth"}
        negative_words = {"bad", "poor", "negative", "decline", "crisis"}
        
        total_sentiment = 0.0
        term_counts = {}
        
        for article in articles:
            text = (article["title"] + " " + article["summary"]).lower()
            
            # Count sentiment words
            pos_count = sum(1 for word in positive_words if word in text)
            neg_count = sum(1 for word in negative_words if word in text)
            
            # Simple sentiment
            if pos_count + neg_count > 0:
                article_sentiment = (pos_count - neg_count) / (pos_count + neg_count)
                total_sentiment += article_sentiment
            
            # Extract terms (simple word frequency)
            words = text.split()
            for word in words:
                if len(word) > 5:  # Only longer words
                    term_counts[word] = term_counts.get(word, 0) + 1
        
        # Average sentiment
        sentiment = total_sentiment / len(articles) if articles else 0.0
        sentiment = max(-1.0, min(1.0, sentiment))
        
        # Calculate volatility from history
        volatility = 0.0
        if len(history) >= 2:
            recent_sentiments = [s.sentiment for s in history[-5:]]
            mean = sum(recent_sentiments) / len(recent_sentiments)
            variance = sum((s - mean) ** 2 for s in recent_sentiments) / len(recent_sentiments)
            volatility = min(1.0, variance ** 0.5 * 2)
        
        # Extract top terms
        top_terms = sorted(term_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        total_term_count = sum(term_counts.values())
        
        terms = [
            TermStat(
                term=term,
                weight=count / total_term_count if total_term_count > 0 else 0,
                polarity=0.0,  # Would need sentiment analysis per term
                novelty=0.5  # Placeholder
            )
            for term, count in top_terms
        ]
        
        # Calculate term entropy
        import math
        term_entropy = 0.0
        if total_term_count > 0:
            for count in term_counts.values():
                p = count / total_term_count
                term_entropy -= p * math.log2(p) if p > 0 else 0
        
        return DistilledSnapshot(
            source_id=raw.source_id,
            timestamp=raw.collected_at,
            sentiment=sentiment,
            sentiment_confidence=0.7,  # Medium confidence for simple analysis
            volatility=volatility,
            terms=terms,
            term_entropy=term_entropy,
            anomaly_score=0.0,  # Would calculate from history
            coverage=len(articles) / 10  # Fraction of max_items collected
        )
```

## Pull Request Process

### Before Submitting

1. **Test your changes**
   ```bash
   python main.py  # Should start without errors
   # Test your specific feature manually
   ```

2. **Update documentation**
   - Add/update docstrings
   - Update README.md if needed
   - Add example to examples.json if applicable

3. **Check code style**
   ```bash
   # If you have installed linting tools:
   # flake8 .
   # mypy .
   ```

4. **Commit with clear message**
   ```bash
   git add .
   git commit -m "Add RSS feed plugin for TEXT sources

   - Implements PluginBase interface
   - Supports RSS 2.0 and Atom feeds
   - Basic sentiment analysis on article content
   - Extracts top terms from articles"
   ```

### Submitting PR

1. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create Pull Request on GitHub**
   - Click "New Pull Request"
   - Select your branch
   - Fill in PR template (see below)

3. **PR Title Format**
   - `[Feature] Add RSS feed plugin`
   - `[Fix] Correct sentiment calculation in aggregation`
   - `[Docs] Improve plugin development guide`
   - `[Test] Add unit tests for scheduler`

### PR Template

```markdown
## Description
Brief description of what this PR does.

## Type of Change
- [ ] New plugin
- [ ] Bug fix
- [ ] Feature enhancement
- [ ] Documentation
- [ ] Test coverage

## Testing
- [ ] Tested manually
- [ ] Added/updated tests
- [ ] Verified no regressions

## Related Issues
Closes #123

## Screenshots (if applicable)
[Add screenshots for UI changes]

## Checklist
- [ ] Code follows project style guidelines
- [ ] Documentation updated
- [ ] No breaking changes (or clearly documented)
```

## Reporting Bugs

### Before Reporting
1. Check existing issues
2. Verify it's reproducible
3. Test with latest version

### Bug Report Template

```markdown
**Description**
Clear description of the bug

**To Reproduce**
Steps to reproduce:
1. Go to '...'
2. Click on '...'
3. See error

**Expected Behavior**
What you expected to happen

**Actual Behavior**
What actually happened

**Environment**
- OS: [e.g., Ubuntu 22.04]
- Python version: [e.g., 3.12.1]
- Parallax Index version: [e.g., 1.0.0]

**Logs**
```
Relevant log output
```

**Additional Context**
Any other relevant information
```

## Feature Requests

Use GitHub Issues with label `enhancement`:

```markdown
**Feature Description**
Clear description of proposed feature

**Use Case**
Why is this needed? What problem does it solve?

**Proposed Solution**
How you think it should work

**Alternatives Considered**
Other approaches you've thought about

**Additional Context**
Mockups, examples, references
```

## Code Review Process

### What We Look For
- **Correctness**: Does it work as intended?
- **Design**: Does it fit the architecture?
- **Testing**: Is it adequately tested?
- **Documentation**: Is it well documented?
- **Style**: Does it follow code style?
- **Performance**: Are there obvious optimizations?

### Review Timeline
- Initial response: Within 48 hours
- Full review: Within 1 week
- Merge decision: After approval from maintainer

## Community Guidelines

### Be Respectful
- Use welcoming and inclusive language
- Respect differing viewpoints
- Accept constructive criticism gracefully
- Focus on what's best for the community

### Be Collaborative
- Help others when you can
- Share knowledge and resources
- Give credit where due
- Build on others' work

### Be Professional
- Keep discussions technical and objective
- Assume good intentions
- Admit mistakes and learn from them

## Questions?

- **General questions**: Open a GitHub Discussion
- **Bug reports**: Open an Issue
- **Security concerns**: Email [security contact]
- **Feature ideas**: Open an Issue with `enhancement` label

## License

By contributing, you agree that your contributions will be licensed under the same MIT License that covers the project.

---

Thank you for contributing to Parallax Index! 🎉
