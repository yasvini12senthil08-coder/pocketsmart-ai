import os
import hmac
import time

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from google import genai
from starlette.middleware.sessions import SessionMiddleware

# Load environment variables from .env file
load_dotenv()

# The names here must match the variable names in your .env file
API_KEY = os.getenv("GEMINI_API_KEY")
SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-key")

# Fixed login details (can be changed in .env)
APP_USERNAME = os.getenv("APP_USERNAME", "admin")
APP_PASSWORD = os.getenv("APP_PASSWORD", "pocketsmart123")
DISPLAY_NAME = os.getenv("APP_DISPLAY_NAME", "user")

if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY is not configured in your .env file!")

client = genai.Client(api_key=API_KEY)

# Models are tried in this order. If one is busy, the next one is used.
GEMINI_MODELS = [
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
    "gemini-3-flash-preview",
]

# Change to "₹" if you want prices in rupees
CURRENCY = "$"

app = FastAPI(title="PocketSmart Multi-Planner AI")

app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)

templates = Jinja2Templates(directory="templates")

# History is kept in memory (resets when the server restarts).
history_db = []


# ---------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------

def is_logged_in(request: Request) -> bool:
    return bool(request.session.get("logged_in"))


def check_credentials(username: str, password: str) -> bool:
    user_ok = hmac.compare_digest(
        username.strip().lower().encode("utf-8"),
        APP_USERNAME.strip().lower().encode("utf-8"),
    )
    pass_ok = hmac.compare_digest(
        password.encode("utf-8"),
        APP_PASSWORD.encode("utf-8"),
    )
    return user_ok and pass_ok


def generate_with_retry(prompt, retries=3):
    last_error = None

    for model_name in GEMINI_MODELS:
        for attempt in range(retries):
            try:
                print(f"Trying {model_name}, attempt {attempt + 1}")
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt
                )
                return response.text
            except Exception as e:
                last_error = e
                print(f"{model_name} failed: {str(e)[:120]}")
                # Retry only for temporary "high demand" errors
                if "503" in str(e) and attempt < retries - 1:
                    time.sleep(3 * (attempt + 1))
                    continue
                break  # move on to the next model

    raise last_error


def run_planner(request, template_name, history_type, budget, prompt, extra_context):
    """Common logic for all planners: call Gemini, save history, show result."""
    if not is_logged_in(request):
        return RedirectResponse(url="/login", status_code=303)

    try:
        result = generate_with_retry(prompt)

        if not result:
            result = "Gemini did not return a recommendation."

        history_db.insert(
            0,
            {
                "type": history_type,
                "budget": budget,
                "result": result
            }
        )

        context = {
            "request": request,
            "user": DISPLAY_NAME,
            "recommendations": result,
            "budget": budget
        }
        context.update(extra_context)

        return templates.TemplateResponse(template_name, context)

    except Exception as e:
        print("Gemini Error:", e)

        if "503" in str(e):
            raise HTTPException(
                status_code=503,
                detail="AI service is busy right now. Please try again in a minute."
            )

        raise HTTPException(
            status_code=500,
            detail=f"Gemini AI Error: {str(e)}"
        )


# ---------------------------------------------------------------
# Public pages
# ---------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def serve_home(request: Request):
    return templates.TemplateResponse(
        "home.html",
        {
            "request": request,
            "user": DISPLAY_NAME if is_logged_in(request) else None
        }
    )


# ---------------------------------------------------------------
# Login / Logout (fixed username and password)
# ---------------------------------------------------------------

@app.get("/login", response_class=HTMLResponse)
def serve_login(request: Request):
    if is_logged_in(request):
        return RedirectResponse(url="/dashboard", status_code=303)

    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": "", "success": ""}
    )


@app.post("/login", response_class=HTMLResponse)
def login_post(
    request: Request,
    username: str = Form(None),
    email: str = Form(None),
    password: str = Form(...)
):
    # The login form field can be named either "username" or "email"
    entered_username = username or email or ""

    if not check_credentials(entered_username, password):
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error": "Invalid username or password.",
                "success": ""
            },
            status_code=401
        )

    request.session["logged_in"] = True

    return RedirectResponse(url="/dashboard", status_code=303)


@app.get("/register")
def register_redirect():
    # No register page. Send old links to the login page.
    return RedirectResponse(url="/login", status_code=303)


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)


# ---------------------------------------------------------------
# Dashboard + History (login required)
# ---------------------------------------------------------------

@app.get("/dashboard", response_class=HTMLResponse)
def serve_dashboard(request: Request):
    if not is_logged_in(request):
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": DISPLAY_NAME,
            "history": history_db
        }
    )


@app.get("/history", response_class=HTMLResponse)
def serve_history(request: Request):
    if not is_logged_in(request):
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse(
        "history.html",
        {
            "request": request,
            "user": DISPLAY_NAME,
            "history": history_db
        }
    )


# ---------------------------------------------------------------
# Planner pages (forms, login required)
# ---------------------------------------------------------------

@app.get("/home-planner", response_class=HTMLResponse)
def serve_home_planner(request: Request):
    if not is_logged_in(request):
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse(
        "home_planner.html",
        {"request": request, "user": DISPLAY_NAME}
    )


@app.get("/jewelry-planner", response_class=HTMLResponse)
def serve_jewelry_planner(request: Request):
    if not is_logged_in(request):
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse(
        "jewelry_planner.html",
        {"request": request, "user": DISPLAY_NAME}
    )


@app.get("/party-planner", response_class=HTMLResponse)
def serve_party_planner(request: Request):
    if not is_logged_in(request):
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse(
        "party_planner.html",
        {"request": request, "user": DISPLAY_NAME}
    )


# ---------------------------------------------------------------
# Home planner
# ---------------------------------------------------------------

@app.post("/generate-home", response_class=HTMLResponse)
def generate_home(
    request: Request,
    budget: float = Form(...),
    rooms: str = Form(...),
    items_description: str = Form(...)
):
    prompt = f"""
You are PocketSmart AI, an expert interior planning assistant.

Create a practical and realistic home interior recommendation.

Budget: {CURRENCY}{budget}

Rooms:
{rooms}

Requirements:
{items_description}

Include:
1. Interior concept
2. Recommended furniture/items
3. Estimated cost for each item
4. Room arrangement
5. Budget breakdown
6. Money-saving suggestions
7. Final estimated total

Keep the total close to the user's budget.
Use clear headings and easy-to-read formatting.
"""

    return run_planner(
        request=request,
        template_name="home_recommendation.html",
        history_type=f"Home ({rooms})",
        budget=budget,
        prompt=prompt,
        extra_context={"rooms": rooms}
    )


# ---------------------------------------------------------------
# Jewelry planner
# ---------------------------------------------------------------

@app.post("/generate-jewelry", response_class=HTMLResponse)
def generate_jewelry(
    request: Request,
    budget: float = Form(...),
    occasion: str = Form(...),
    jewelry_type: str = Form("Any"),
    items_description: str = Form("")
):
    prompt = f"""
You are PocketSmart AI, an expert jewelry shopping and styling assistant.

Create a practical and realistic jewelry recommendation.

Budget: {CURRENCY}{budget}

Occasion:
{occasion}

Jewelry type / metal preference:
{jewelry_type}

Extra requirements:
{items_description}

Include:
1. Style concept for the occasion
2. Recommended jewelry pieces (necklace, earrings, bangles, rings, etc.)
3. Estimated cost for each piece
4. Metal, stone and design suggestions (gold, silver, artificial, etc.)
5. Budget breakdown
6. Money-saving suggestions (making charges, purity, rentals, alternatives)
7. Final estimated total

Keep the total close to the user's budget.
Use clear headings and easy-to-read formatting.
"""

    return run_planner(
        request=request,
        template_name="jewelry_recommendation.html",
        history_type=f"Jewelry ({occasion})",
        budget=budget,
        prompt=prompt,
        extra_context={
            "occasion": occasion,
            "jewelry_type": jewelry_type
        }
    )


# ---------------------------------------------------------------
# Party planner
# ---------------------------------------------------------------

@app.post("/generate-party", response_class=HTMLResponse)
def generate_party(
    request: Request,
    budget: float = Form(...),
    party_type: str = Form(...),
    guests: int = Form(10),
    items_description: str = Form("")
):
    prompt = f"""
You are PocketSmart AI, an expert party planning assistant.

Create a practical and realistic party plan.

Budget: {CURRENCY}{budget}

Party type:
{party_type}

Number of guests:
{guests}

Extra requirements:
{items_description}

Include:
1. Party theme concept
2. Venue and decoration ideas with estimated cost
3. Food and drinks menu with estimated cost (per guest and total)
4. Entertainment and activities
5. Budget breakdown
6. Simple timeline / checklist
7. Money-saving suggestions
8. Final estimated total

Keep the total close to the user's budget.
Use clear headings and easy-to-read formatting.
"""

    return run_planner(
        request=request,
        template_name="party_recommendation.html",
        history_type=f"Party ({party_type})",
        budget=budget,
        prompt=prompt,
        extra_context={
            "party_type": party_type,
            "guests": guests
        }
    )