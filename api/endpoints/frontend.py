import os
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()

# Configure templates directory
templates = Jinja2Templates(
    directory=Path(__file__).parent.parent / "templates",
)


# Build your local UI available on http://localhost:{SYFTBOX_ASSIGNED_PORT}/
@router.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    # Get environment variables or use default values
    port = os.environ.get("SYFTBOX_ASSIGNED_PORT", "8080")
    app_name = os.environ.get("SYFTBOX_APP_NAME", "syft_agent")

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "port": port,
            "app_name": app_name,
        },
    )


@router.get("/config", response_class=HTMLResponse)
def get_config(request: Request):
    return templates.TemplateResponse(
        "configuration.html",
        {
            "request": request,
        },
    )


@router.get("/chat", response_class=HTMLResponse)
def get_chat(request: Request):
    return templates.TemplateResponse(
        "chat.html",
        {
            "request": request,
        },
    )


@router.get("/documents", response_class=HTMLResponse)
def get_documents(request: Request):
    return templates.TemplateResponse(
        "documents.html",
        {
            "request": request,
        },
    )
