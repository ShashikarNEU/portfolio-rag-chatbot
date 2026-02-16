from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: str
    llm_model: str = "gpt-5-mini"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    pinecone_api_key: str
    pinecone_index_name: str = "portfolio"
    chunk_size: int = 512
    chunk_overlap: int = 50
    top_k_retrieval: int = 12
    top_k_final: int = 5
    sendgrid_api_key: str = ""
    sender_email: str = "shashiantonydbz@gmail.com"
    recipient_email: str = ""
    sqlite_db_path: str = "./data/chat_history.db"
    daily_max_requests: int = 200
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
