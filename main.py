from backend.app.main import app


if __name__ == "__main__":
    try:
        import uvicorn
    except ImportError as exc:
        raise SystemExit(
            "uvicorn is not installed. Run `pip install -r requirements.txt` first."
        ) from exc

    uvicorn.run(app, host="127.0.0.1", port=8000)
