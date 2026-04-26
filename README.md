# SmartAgri Guide

Flask API for user authentication and smart farm management.

## Features Implemented (CW1)

- **User Management:** Secure signup, email verification, login, and logout flows.
- **Farm CRUD with Pagination:** Complete Create, Read, Update, and Delete operations with efficient server-side pagination.
- **Sensor Management & Readings:** Dedicated endpoints for registering agricultural sensors and retrieving real-time data.
- **Weather API Integration:** External service integration to fetch and store localized weather data for specific farm coordinates.
- **Farm & Regional Insights:** Specialized data analysis providing actionable insights at both individual farm and regional levels.
- **Emergency Alert Broadcasting:** Admin-only functionality to broadcast GeoJSON-based alerts to users in specific danger zones.
- **Full-text Search:** High-performance search indexing across the farm database.

## Setup

1. Create a virtual environment.
2. Install dependencies:
   `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and update values if needed.
4. Seed sample data:
   `python -m scripts.make_dataset`
5. Start the API:
   `python app.py`

## Project Layout

- `app.py`: app entrypoint and factory
- `config.py`: environment-driven settings and MongoDB access
- `blueprints/`: auth and farm routes
- `scripts/`: data/bootstrap scripts
- `utils/`: shared validation helpers
- `tests/`: API tests

## Running Tests

`c:/Users/ratul/SmartAgri-Guide/.venv/Scripts/python.exe -m pytest -q`

## Submission Artifacts

- `SUBMISSION_API_ENDPOINTS.md`: API endpoint summary for CW1 evidence.
- `SUBMISSION_TESTING_SUMMARY.md`: automated testing summary for CW1 evidence.

## Documentation Note (Compodoc)

For coursework evidence and self-evaluation, documentation is available in both README files and the generated Compodoc output (`documentation/` folder), which can be used in place of a separate PDF where permitted by the rubric.
