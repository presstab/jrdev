from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from jrdev.core.application import Application
    from jrdev.models.api_provider import ApiProvider

_app: Optional['Application'] = None


def initialize_provider_factory(app: 'Application'):
    """Initializes the provider factory with the application instance."""
    global _app
    _app = app


def _get_app() -> 'Application':
    """Returns the application instance, raising an error if not initialized."""
    if _app is None:
        raise RuntimeError("Provider factory has not been initialized. Call initialize_provider_factory() first.")
    return _app


def get_client(provider_name: str) -> Optional[Any]:
    """
    Gets the API client for a given provider name.

    Args:
        provider_name: The name of the provider.

    Returns:
        The initialized client instance, or None if not found or not initialized.
    """
    app = _get_app()
    return app.state.clients.get_client(provider_name)


def list_providers() -> List['ApiProvider']:
    """
    Lists all available API providers.

    Returns:
        A list of ApiProvider objects.
    """
    app = _get_app()
    return app.state.clients.provider_list()


def get_provider_for_model(model_name: str) -> Optional[str]:
    """
    Finds the provider name for a given model name.

    Args:
        model_name: The name of the model.

    Returns:
        The name of the provider, or None if the model is not found.
    """
    app = _get_app()
    for model_info in app.get_models():
        if model_info["name"] == model_name:
            return model_info["provider"]
    return None


def add_provider(provider_data: Dict[str, Any]) -> None:
    """Adds a new API provider."""
    app = _get_app()
    app.state.clients.add_provider(provider_data)


def edit_provider(name: str, updated_fields: Dict[str, Any]) -> None:
    """Edits an existing API provider."""
    app = _get_app()
    app.state.clients.edit_provider(name, updated_fields)


def remove_provider(name: str) -> None:
    """Removes an API provider."""
    app = _get_app()
    app.state.clients.remove_provider(name)
