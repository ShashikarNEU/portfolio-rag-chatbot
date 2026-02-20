from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: str
    llm_model: str = ""
    embedding_model: str = ""
    embedding_dimensions: int = 0
    pinecone_api_key: str
    pinecone_index_name: str = ""
    chunk_size: int = 0
    chunk_overlap: int = 0
    top_k_retrieval: int = 0
    top_k_final: int = 0
    github_username: str = ""
    github_token: str = ""
    sendgrid_api_key: str = ""
    sender_email: str = ""
    recipient_email: str = ""
    sqlite_db_path: str = "./data/chat_history.db"
    daily_max_requests: int = 200
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
