# Phase 3: System Design - PocketSmart AI

## 1. System Architecture Pattern
PocketSmart AI is built on a modern **Client-Server Architecture**:
* **Client Layer**: Browser-based Jinja2 HTML templates (`templates/`) styled with custom CSS (`static/style.css`). Users interact via responsive forms and dropdown menus.
* **Server Layer**: FastAPI backend (`main.py`) running on an Uvicorn ASGI server. It intercepts HTTP requests, handles application routing, and processes business logic.
* **AI Intelligence Layer**: A dedicated module (`gemini_client.py`) that securely bridges the application with the Google Gemini Cloud API to fetch contextual planning responses.

## 2. Architectural Workflow Design
1. **Request Initiation**: The user selects a planning module (e.g., Home Planner or Jewelry Planner) from the dashboard dropdown and inputs text requirements.
2. **Backend Routing**: FastAPI receives the payload and routes it to the corresponding Python module function.
3. **API Communication**: The module constructs a tailored prompt and dispatches it to `gemini_client.py`.
4. **AI Generation**: Google Gemini processes the query and returns a structured response.
5. **Dynamic Rendering**: The response is returned to the frontend and rendered in the result panel seamlessly without reloading the page.

## 3. Component Interaction Diagram Flow
[Browser UI] ---> (HTTP Request) ---> [FastAPI Server (main.py)] ---> (API Call) ---> [Google Gemini API]
[Browser UI] <--- (JSON Response) <--- [FastAPI Server (main.py)] <--- (AI Output) <--- [Google Gemini API]
