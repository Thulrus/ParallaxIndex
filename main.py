"""
Parallax Index - Global Sentiment & Cultural Drift Tracker

Main application entry point.
"""

import asyncio
import sys

import uvicorn

from core.aggregation import AggregationEngine
from core.scheduler import CollectionScheduler
from plugins.registry import get_registry
from storage.database import Database
from web.routes import app, init_web


async def initialize_app():
    """
    Initialize all application components.
    
    Order of initialization:
    1. Database
    2. Plugin registry
    3. Aggregation engine
    4. Scheduler
    5. Web interface
    """
    print("=" * 60)
    print("Parallax Index - Global Sentiment Tracker")
    print("=" * 60)
    
    # Initialize database
    print("\n[1/5] Initializing database...")
    db = Database("parallax_index.db")
    await db.initialize()
    
    # Discover and register plugins
    print("\n[2/5] Loading plugins...")
    registry = get_registry()
    registry.discover_plugins()
    
    plugins = registry.list_plugins()
    print(f"Loaded {len(plugins)} plugin(s):")
    for plugin in plugins:
        print(f"  • {plugin.display_name} ({plugin.plugin_id}) v{plugin.plugin_version}")
    
    # Initialize aggregation engine
    print("\n[3/5] Initializing aggregation engine...")
    aggregator = AggregationEngine(db)
    
    # Initialize scheduler
    print("\n[4/5] Initializing scheduler...")
    scheduler = CollectionScheduler(db)
    await scheduler.start()
    
    # Initialize web interface
    print("\n[5/5] Initializing web interface...")
    init_web(db, scheduler, aggregator)
    
    # Display source summary
    sources = await db.list_sources()
    enabled_count = sum(1 for s in sources if s.enabled)
    print(f"\nConfigured sources: {len(sources)} ({enabled_count} enabled)")
    
    print("\n" + "=" * 60)
    print("✓ Application initialized successfully")
    print("=" * 60)
    print("\nAccess the dashboard at: http://localhost:8000")
    print("API documentation at: http://localhost:8000/docs")
    print("\nPress Ctrl+C to stop\n")
    
    return scheduler


def main():
    """
    Main entry point.
    """
    # Check Python version
    if sys.version_info < (3, 12):
        print("ERROR: Python 3.12 or higher is required")
        sys.exit(1)
    
    # Initialize application
    scheduler = None
    
    try:
        # Run initialization in event loop
        loop = asyncio.get_event_loop()
        scheduler = loop.run_until_complete(initialize_app())
        
        # Start web server
        config = uvicorn.Config(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info",
            access_log=True
        )
        server = uvicorn.Server(config)
        
        # Run server
        loop.run_until_complete(server.serve())
    
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        if scheduler:
            scheduler.stop()
        print("✓ Shutdown complete")
    
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        if scheduler:
            scheduler.stop()
        sys.exit(1)


if __name__ == "__main__":
    main()
