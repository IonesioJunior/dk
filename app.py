import asyncio
import logging
import threading
from pathlib import Path

from fastapi import FastAPI
from fastsyftbox import Syftbox

from agent.agent import Agent
from api.endpoints.config import set_agent
from api.routes import api_router
from rpc.rpc_handler import ping_handler
from syftbox.client import syft_client
from syftbox.jobs import register_jobs
from syftbox.scheduler import scheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

# Initialize the agent at startup
agent = Agent()

# Set the agent in the config module to avoid circular imports
set_agent(agent)

# Initialize the singleton client
syft_client.initialize()

# Register periodic jobs with the scheduler
register_jobs()

app = FastAPI()

# Include the main API router
app.include_router(api_router)

syftbox = Syftbox(
    app=app,
    name=Path(__file__).resolve().parent.name,
)


# Register RPC handler
syftbox.on_request("/ping")(ping_handler)


# Start scheduler in background thread to work with Syftbox
def run_scheduler_in_thread() -> None:
    """Run the scheduler in a separate thread with its own event loop."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def start_scheduler() -> None:
        await scheduler.start()

    loop.run_until_complete(start_scheduler())
    loop.run_forever()


scheduler_thread = threading.Thread(target=run_scheduler_in_thread, daemon=True)
scheduler_thread.start()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
