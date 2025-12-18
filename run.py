import uvicorn

from app.utils.logging import setup_logging

if __name__ == "__main__":
    setup_logging("backend.log")
    uvicorn.run("app.main:app", host="127.0.0.1", port=3011, log_config=None, log_level=None)
