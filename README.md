# SmartAgri Guide

Flask API for user authentication and smart farm management.

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

`pytest`
