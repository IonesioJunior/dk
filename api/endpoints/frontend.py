import os
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
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

    # Get user ID from settings
    from dependencies import get_settings

    settings = get_settings()

    # Check if in onboarding mode
    if settings.onboarding:
        return templates.TemplateResponse(
            "onboarding.html",
            {
                "request": request,
                "title": "Syft Agent - Onboarding",
            },
        )

    user_id = settings.syftbox_username

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "title": "Syft Agent",
            "message": "Welcome to the Syft Agent platform",
            "port": port,
            "app_name": app_name,
            "user_id": user_id,
        },
    )


@router.get("/config", response_class=HTMLResponse)
def get_config(request: Request) -> HTMLResponse:
    # Check if in onboarding mode
    from dependencies import get_settings

    settings = get_settings()

    if settings.onboarding:
        # Redirect to home page which will show onboarding
        from fastapi.responses import RedirectResponse

        return RedirectResponse(url="/")

    return templates.TemplateResponse(
        "configuration.html",
        {
            "request": request,
        },
    )


@router.get("/chat", response_class=HTMLResponse)
def get_chat(request: Request) -> HTMLResponse:
    # Get settings first to check onboarding
    from dependencies import get_settings

    settings = get_settings()

    # Check if in onboarding mode
    if settings.onboarding:
        # Redirect to home page which will show onboarding
        from fastapi.responses import RedirectResponse

        return RedirectResponse(url="/")

    # Import the agent to get current provider and model information
    from api.endpoints.config import get_agent

    # Get agent instance
    agent = get_agent()

    # Default values in case agent is not available
    provider_name = "anthropic"
    model_name = "claude-3-opus"
    providers_config = {
        "providers": {
            "anthropic": ["claude-3-opus-20240229", "claude-3-sonnet-20240229"],
            "openai": ["gpt-4o", "gpt-4"],
            "ollama": ["llama2", "mistral"],
            "openrouter": ["anthropic/claude-3-opus", "openai/gpt-4"],
        }
    }

    if agent:
        provider_name = agent.provider_name
        model_name = agent.model
        # Get the full configuration including available providers and models
        providers_config = agent.get_config()

    user_id = settings.syftbox_username

    return templates.TemplateResponse(
        "chat.html",
        {
            "request": request,
            "provider": provider_name,
            "model": model_name,
            "providers_config": providers_config,
            "user_id": user_id,  # Pass user ID to template
        },
    )


@router.get("/documents", response_class=HTMLResponse)
async def get_documents(request: Request) -> HTMLResponse:
    # Check if in onboarding mode
    from dependencies import get_settings

    settings = get_settings()

    if settings.onboarding:
        # Redirect to home page which will show onboarding
        from fastapi.responses import RedirectResponse

        return RedirectResponse(url="/")

    # Import here to avoid circular imports
    from api.endpoints.documents_collection import document_insights

    # Get document insights for the dashboard
    insights = await document_insights()

    return templates.TemplateResponse(
        "documents.html",
        {
            "request": request,
            "insights": insights,
        },
    )


@router.get("/api_configs", response_class=HTMLResponse)
def get_api_configs(request: Request) -> HTMLResponse:
    # Check if in onboarding mode
    from dependencies import get_settings

    settings = get_settings()

    if settings.onboarding:
        # Redirect to home page which will show onboarding
        from fastapi.responses import RedirectResponse

        return RedirectResponse(url="/")

    return templates.TemplateResponse(
        "api_configs.html",
        {
            "request": request,
        },
    )


@router.get("/map", response_class=HTMLResponse)
def get_map(request: Request) -> HTMLResponse:
    # Check if in onboarding mode
    from dependencies import get_settings

    settings = get_settings()

    if settings.onboarding:
        # Redirect to home page which will show onboarding
        from fastapi.responses import RedirectResponse

        return RedirectResponse(url="/")

    return templates.TemplateResponse(
        "map.html",
        {
            "request": request,
        },
    )


@router.get("/active-users", response_class=HTMLResponse)
async def get_active_users(_request: Request) -> JSONResponse:
    """Return a list of active users for mention feature"""
    from fastapi.responses import JSONResponse

    from dependencies import get_settings

    # Get the current user ID from settings
    settings = get_settings()
    user_id = settings.syftbox_username

    # In a real implementation, this would query a database or service
    # For now, we'll return static sample data with the actual user ID
    sample_data = {
        "current_user_id": user_id,
        "online": ["alice", "bob", "david", "frank"],
        "offline": ["charlie", "emma", "george", "hannah"],
    }

    return JSONResponse(content=sample_data)


@router.get("/component/{component_name}", response_class=HTMLResponse)
def get_component(request: Request, component_name: str) -> HTMLResponse:
    """Serve UI components as standalone modules"""

    # Security: Only allow specific component names
    allowed_components = [
        "document_upload",
        "user_avatar",
        "header_controls",
        "input_area",
        "message_area",
        "modals",
        "dropdown",
        "theme_toggle",
        "avatar",
        "mention_popup",
    ]
    if component_name not in allowed_components:
        return HTMLResponse(content="Component not found", status_code=404)

    try:
        # Get user ID from settings for components that need it
        from dependencies import get_settings

        settings = get_settings()
        user_id = settings.syftbox_username

        component_path = f"components/{component_name}.html"
        return templates.TemplateResponse(
            component_path,
            {
                "request": request,
                "user_id": user_id,
            },
        )
    except Exception as e:
        return HTMLResponse(content=f"Error loading component: {e!s}", status_code=500)


@router.get("/templates/{template_name}", response_class=HTMLResponse)
def get_template(request: Request, template_name: str) -> HTMLResponse:
    """Serve templates for SPA content loading"""

    # Security: Only allow specific template names
    allowed_templates = ["chat", "documents"]
    if template_name not in allowed_templates:
        return HTMLResponse(content="Template not found", status_code=404)

    try:
        # Get user ID from settings for templates that need it
        from dependencies import get_settings

        settings = get_settings()
        user_id = settings.syftbox_username

        return templates.TemplateResponse(
            f"{template_name}.html",
            {
                "request": request,
                "user_id": user_id,
            },
        )
    except Exception as e:
        return HTMLResponse(content=f"Error loading template: {e!s}", status_code=500)
