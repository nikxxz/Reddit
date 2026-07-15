from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    app: str


class AppConfigResponse(BaseModel):
    app_name: str
    reddit_username: str | None = None
