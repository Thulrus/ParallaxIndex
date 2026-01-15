"""
Web interface for Parallax Index.

FastAPI routes for the dashboard and source management.
"""

from uuid import UUID

from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from core.aggregation import AggregationEngine
from core.schemas import SourceInstance, SentimentPolarity
from core.scheduler import CollectionScheduler
from plugins.registry import get_registry
from storage.database import Database


# Initialize FastAPI app
app = FastAPI(
    title="Parallax Index",
    description="Global Sentiment & Cultural Drift Tracker",
    version="1.0.0"
)

# Templates
templates = Jinja2Templates(directory="web/templates")

# Global instances (initialized in main.py)
db: Database = None
scheduler: CollectionScheduler = None
aggregator: AggregationEngine = None


def init_web(database: Database, sched: CollectionScheduler, agg: AggregationEngine):
    """Initialize web module with dependencies."""
    global db, scheduler, aggregator
    db = database
    scheduler = sched
    aggregator = agg


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """
    Main dashboard showing global sentiment and source overview.
    """
    # Get global sentiment
    global_sentiment = await aggregator.compute_global_sentiment()
    
    # Get all sources with their latest snapshots
    sources = await db.list_sources()
    source_data = []
    
    for source in sources:
        latest = await db.get_latest_snapshot(source.source_id)
        trend = await aggregator.get_sentiment_trend(source.source_id)
        
        source_data.append({
            "source": source,
            "latest": latest,
            "trend": trend
        })
    
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "global_sentiment": global_sentiment,
            "sources": source_data
        }
    )


@app.get("/sources", response_class=HTMLResponse)
async def list_sources(request: Request):
    """
    List all configured sources.
    """
    sources = await db.list_sources()
    
    return templates.TemplateResponse(
        "sources.html",
        {
            "request": request,
            "sources": sources
        }
    )


@app.get("/sources/new", response_class=HTMLResponse)
async def new_source_form(request: Request):
    """
    Form to create a new source.
    """
    registry = get_registry()
    plugins = registry.list_plugins()
    
    return templates.TemplateResponse(
        "source_form.html",
        {
            "request": request,
            "plugins": plugins,
            "polarities": list(SentimentPolarity),
            "source": None
        }
    )


@app.post("/sources/create")
async def create_source(
    plugin_id: str = Form(...),
    display_name: str = Form(...),
    enabled: bool = Form(False),
    weight: float = Form(1.0),
    sentiment_polarity: str = Form("POSITIVE_IS_GOOD"),
    schedule: str = Form("0 * * * *"),
    config_json: str = Form("{}")
):
    """
    Create a new source instance.
    """
    import json
    
    try:
        config = json.loads(config_json)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON configuration")
    
    # Validate plugin exists
    registry = get_registry()
    plugin = registry.get_plugin(plugin_id)
    if not plugin:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found")
    
    # Validate config
    is_valid, error = plugin.validate_config(config)
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"Invalid configuration: {error}")
    
    # Create source
    source = SourceInstance(
        plugin_id=plugin_id,
        display_name=display_name,
        enabled=enabled,
        config=config,
        weight=weight,
        sentiment_polarity=SentimentPolarity(sentiment_polarity),
        schedule=schedule
    )
    
    await db.create_source(source)
    
    # Schedule if enabled
    if enabled:
        await scheduler.schedule_source(str(source.source_id))
    
    return RedirectResponse(url="/sources", status_code=303)


@app.get("/sources/{source_id}", response_class=HTMLResponse)
async def view_source(request: Request, source_id: str):
    """
    View details of a specific source.
    """
    try:
        source = await db.get_source(UUID(source_id))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID")
    
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    
    # Get recent snapshots
    history = await db.get_snapshot_history(source.source_id, limit=20)
    
    # Get plugin info
    registry = get_registry()
    plugin_def = registry.get_definition(source.plugin_id)
    
    return templates.TemplateResponse(
        "source_detail.html",
        {
            "request": request,
            "source": source,
            "plugin": plugin_def,
            "history": history
        }
    )


@app.post("/sources/{source_id}/collect")
async def trigger_collection(source_id: str):
    """
    Trigger immediate collection for a source.
    """
    result = await scheduler.collect_now(source_id)
    return {"message": result}


@app.post("/sources/{source_id}/toggle")
async def toggle_source(source_id: str):
    """
    Enable or disable a source.
    """
    try:
        source = await db.get_source(UUID(source_id))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID")
    
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    
    # Toggle enabled state
    source.enabled = not source.enabled
    await db.update_source(source)
    
    # Update scheduler
    if source.enabled:
        await scheduler.schedule_source(source_id)
    else:
        await scheduler.unschedule_source(source_id)
    
    return RedirectResponse(url=f"/sources/{source_id}", status_code=303)


@app.delete("/sources/{source_id}")
async def delete_source(source_id: str):
    """
    Delete a source.
    """
    try:
        # Unschedule first
        await scheduler.unschedule_source(source_id)
        
        # Delete from database
        await db.delete_source(UUID(source_id))
        
        return {"message": "Source deleted"}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID")


@app.get("/api/plugins")
async def list_plugins():
    """
    API endpoint to list available plugins.
    """
    registry = get_registry()
    plugins = registry.list_plugins()
    return {"plugins": [p.model_dump() for p in plugins]}


@app.get("/api/sources")
async def api_list_sources():
    """
    API endpoint to list all sources.
    """
    sources = await db.list_sources()
    return {"sources": [s.model_dump() for s in sources]}


@app.get("/api/sentiment/global")
async def api_global_sentiment():
    """
    API endpoint for global sentiment.
    """
    sentiment = await aggregator.compute_global_sentiment()
    if sentiment:
        return sentiment.model_dump()
    return {"error": "No data available"}


@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    """
    return {
        "status": "healthy",
        "scheduler_running": scheduler.scheduler.running,
        "source_count": len(await db.list_sources())
    }
