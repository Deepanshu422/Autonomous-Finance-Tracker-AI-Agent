from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # These attributes automatically map to your .env file
    supabase_url: str
    supabase_key: str
    groq_api_key: str
    admin_phone_number: str
    port: int
    # This tells Pydantic exactly where to look for our secrets locally.
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

# Initialized the globally available instance
settings = Settings()