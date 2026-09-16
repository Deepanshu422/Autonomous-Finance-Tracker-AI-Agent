from fastapi import FastAPI
from app.api.webhooks import router as webhook_router
from contextlib import asynccontextmanager
from app.services.agent_tasks import start_agent_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # to start autonomous background agent
    start_agent_scheduler()
    yield

# Initializing FastAPI application
app = FastAPI(
    title="AI-Powered Money Tracker Agent",
    description="An autonomous agent for WhatsApp expense tracking.",
    version="1.0.0",
    lifespan=lifespan
)

# webhook router with clean URL prefix
app.include_router(webhook_router, prefix="/api/v1")

# A health check endpoint for cloud host
@app.get("/")
def health_check():
    return {"status": "success", "message": "Money Tracker Agent is live!"}
