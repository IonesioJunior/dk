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
def read_root(request: Request) -> HTMLResponse:
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
def get_config(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "configuration.html",
        {
            "request": request,
        },
    )


@router.get("/chat", response_class=HTMLResponse)
def get_chat(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "chat.html",
        {
            "request": request,
        },
    )


@router.get("/documents", response_class=HTMLResponse)
def get_documents(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "documents.html",
        {
            "request": request,
        },
    )


@router.get("/api_configs", response_class=HTMLResponse)
def get_api_configs(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "api_configs.html",
        {
            "request": request,
        },
    )


@router.get("/component/{component_name}", response_class=HTMLResponse)
def get_component(request: Request, component_name: str) -> HTMLResponse:
    """Serve UI components as standalone modules"""

    # Security: Only allow specific component names
    allowed_components = ['document_upload', 'user_avatar']
    if component_name not in allowed_components:
        return HTMLResponse(content="Component not found", status_code=404)

    try:
        component_path = f"components/{component_name}.html"
        return templates.TemplateResponse(
            component_path,
            {
                "request": request,
            },
        )
    except Exception as e:
        return HTMLResponse(content=f"Error loading component: {e!s}", status_code=500)
