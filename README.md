# Phase 6: Automated Testing & Quality Assurance - PocketSmart AI
# Run tests using pytest framework: pytest -v

from fastapi.testclient import TestClient
from main import app, GEMINI_MODELS, CURRENCY

# Initialize FastAPI Test Client
client = TestClient(app)

def test_root_endpoint():
    """
    Test the root endpoint (home page) to ensure the FastAPI server 
    is active and responds with a successful HTTP status code.
    """
    response = client.get("/")
    assert response.status_code in [200, 301, 302]

def test_login_redirect_and_unauthorized_access():
    """
    Verify that protected endpoints like dashboard or planners 
    redirect unauthenticated users to the login page.
    """
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code in [302, 303]
    assert "/login" in response.headers.get("location", "")

def test_gemini_models_and_currency_configuration():
    """
    Validate that critical configuration variables and Gemini models 
    are properly loaded in the main application instance.
    """
    assert len(GEMINI_MODELS) > 0
    assert CURRENCY in ["$", "₹"]

def test_planner_get_routes_exist():
    """
    Ensure all three multi-planner GET endpoints are registered and 
    respond correctly (with authentication redirection or forms).
    """
    for route in ["/home-planner", "/jewelry-planner", "/party-planner"]:
        response = client.get(route, follow_redirects=False)
        # Should redirect to login when session is empty
        assert response.status_code in [200, 302, 303]
