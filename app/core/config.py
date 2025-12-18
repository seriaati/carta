from typing import Literal

from dotenv import load_dotenv
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    db_url: str
    openai_api_key: str
    env: Literal["prod", "dev"] = "prod"

    # Image CDN
    cdn_api_key: str

    # Discord
    discord_client_id: str
    discord_client_secret: str
    discord_redirect_uri: str
    discord_bot_token: str

    # JWT & token settings
    # IMPORTANT: set in environment for production
    jwt_secret: str | None = None
    jwt_algorithm: str = "HS256"
    access_token_ttl_seconds: int = 15 * 60  # 15 minutes
    refresh_token_ttl_seconds: int = 30 * 24 * 60 * 60  # 30 days

    @property
    def is_dev(self) -> bool:
        return self.env == "dev"


load_dotenv()
settings = Config()  # pyright: ignore[reportCallIssue]
