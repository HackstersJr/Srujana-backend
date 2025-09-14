"""
Settings configuration for the CareCloud AI system.
"""

import os
from typing import Any, Dict, Optional

from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""

    host: str = Field(default="localhost", env="DB_HOST")
    port: int = Field(default=5432, env="DB_PORT")
    user: str = Field(default="postgres", env="DB_USER")
    password: str = Field(default="", env="DB_PASSWORD")
    database: str = Field(default="carecloud", env="DB_NAME")
    pool_size: int = Field(default=10, env="DB_POOL_SIZE")
    max_overflow: int = Field(default=20, env="DB_MAX_OVERFLOW")
    echo: bool = Field(default=False, env="DB_ECHO")

    model_config = ConfigDict(env_prefix="DB_")


class LLMSettings(BaseSettings):
    """LLM configuration settings."""

    gemini_api_key: str = Field(default="", env="GEMINI_API_KEY")
    model_name: str = Field(default="gemini-1.5-flash", env="LLM_MODEL_NAME")
    temperature: float = Field(default=0.7, env="LLM_TEMPERATURE")
    max_tokens: int = Field(default=2048, env="LLM_MAX_TOKENS")
    max_iterations: int = Field(default=10, env="LLM_MAX_ITERATIONS")

    model_config = ConfigDict()


class EmbeddingSettings(BaseSettings):
    """Embedding configuration settings."""

    model_name: str = Field(default="all-MiniLM-L6-v2", env="EMBEDDING_MODEL_NAME")
    vector_dim: int = Field(default=384, env="EMBEDDING_VECTOR_DIM")
    batch_size: int = Field(default=32, env="EMBEDDING_BATCH_SIZE")

    model_config = ConfigDict(env_prefix="EMBEDDING_")


class NanoPQSettings(BaseSettings):
    """NanoPQ configuration settings."""

    num_subvectors: int = Field(default=16, env="NANOPQ_NUM_SUBVECTORS")
    num_clusters: int = Field(default=256, env="NANOPQ_NUM_CLUSTERS")
    index_path: str = Field(default="data/nanopq_index.pkl", env="NANOPQ_INDEX_PATH")
    docs_path: str = Field(default="data/nanopq_docs.pkl", env="NANOPQ_DOCS_PATH")

    model_config = ConfigDict(env_prefix="NANOPQ_")


class EmbedChainSettings(BaseSettings):
    """EmbedChain configuration settings."""

    db_path: str = Field(default="data/embedchain_db", env="EMBEDCHAIN_DB_PATH")
    provider: str = Field(default="chroma", env="EMBEDCHAIN_PROVIDER")
    llm_provider: str = Field(default="google", env="EMBEDCHAIN_LLM_PROVIDER")
    llm_model: str = Field(default="gemini-1.5-flash", env="EMBEDCHAIN_LLM_MODEL")

    model_config = ConfigDict(env_prefix="EMBEDCHAIN_")


class ToolboxSettings(BaseSettings):
    """Toolbox configuration settings."""

    shell_enabled: bool = Field(default=False, env="TOOLBOX_SHELL_ENABLED")
    file_management_enabled: bool = Field(
        default=True, env="TOOLBOX_FILE_MANAGEMENT_ENABLED"
    )
    calculator_enabled: bool = Field(default=True, env="TOOLBOX_CALCULATOR_ENABLED")
    web_search_enabled: bool = Field(default=False, env="TOOLBOX_WEB_SEARCH_ENABLED")
    database_enabled: bool = Field(default=True, env="TOOLBOX_DATABASE_ENABLED")

    model_config = ConfigDict(env_prefix="TOOLBOX_")


class ServerSettings(BaseSettings):
    """Server configuration settings."""

    host: str = Field(default="0.0.0.0", env="SERVER_HOST")
    port: int = Field(default=8000, env="SERVER_PORT")
    workers: int = Field(default=1, env="SERVER_WORKERS")
    reload: bool = Field(default=False, env="SERVER_RELOAD")
    log_level: str = Field(default="info", env="SERVER_LOG_LEVEL")

    model_config = ConfigDict(env_prefix="SERVER_")


class LoggingSettings(BaseSettings):
    """Logging configuration settings."""

    level: str = Field(default="INFO", env="LOG_LEVEL")
    file_path: Optional[str] = Field(default=None, env="LOG_FILE_PATH")
    max_file_size: int = Field(default=10485760, env="LOG_MAX_FILE_SIZE")  # 10MB
    backup_count: int = Field(default=5, env="LOG_BACKUP_COUNT")
    format_string: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="LOG_FORMAT_STRING",
    )

    model_config = ConfigDict(env_prefix="LOG_")


class Settings(BaseSettings):
    """Main application settings."""

    # Environment
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=True, env="DEBUG")

    # Application info
    app_name: str = Field(default="CareCloud AI Agent", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")

    # Data paths
    data_dir: str = Field(default="data", env="DATA_DIR")
    input_dir: str = Field(default="data/input", env="INPUT_DIR")
    output_dir: str = Field(default="data/output", env="OUTPUT_DIR")

    # Sub-settings
    database: DatabaseSettings = DatabaseSettings()
    llm: LLMSettings = LLMSettings()
    embedding: EmbeddingSettings = EmbeddingSettings()
    nanopq: NanoPQSettings = NanoPQSettings()
    embedchain: EmbedChainSettings = EmbedChainSettings()
    toolbox: ToolboxSettings = ToolboxSettings()
    server: ServerSettings = ServerSettings()
    logging: LoggingSettings = LoggingSettings()

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow"
    )

    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration as dictionary."""
        return {
            "host": self.database.host,
            "port": self.database.port,
            "user": self.database.user,
            "password": self.database.password,
            "database": self.database.database,
            "pool_size": self.database.pool_size,
            "max_overflow": self.database.max_overflow,
            "echo": self.database.echo,
        }

    def get_llm_config(self) -> Dict[str, Any]:
        """Get LLM configuration as dictionary."""
        return {
            "gemini_api_key": self.llm.gemini_api_key,
            "model_name": self.llm.model_name,
            "temperature": self.llm.temperature,
            "max_tokens": self.llm.max_tokens,
            "max_iterations": self.llm.max_iterations,
        }

    def get_llm_configs(self) -> Dict[str, Dict[str, Any]]:
        """Return a map of LLM configurations (primary and secondary).

        Secondary values may be provided by environment variables prefixed with
        LLM_SECONDARY_. This allows running two LLMs and selecting at runtime.
        """
        primary = self.get_llm_config()

        # Secondary LLM configuration (falls back to primary values)
        secondary = {
            "gemini_api_key": os.environ.get("GEMINI_API_KEY_SECONDARY", self.llm.gemini_api_key),
            "model_name": os.environ.get("LLM_MODEL_NAME_SECONDARY", self.llm.model_name),
            "temperature": float(os.environ.get("LLM_TEMPERATURE_SECONDARY", self.llm.temperature)),
            "max_tokens": int(os.environ.get("LLM_MAX_TOKENS_SECONDARY", self.llm.max_tokens)),
            "max_iterations": int(os.environ.get("LLM_MAX_ITERATIONS_SECONDARY", self.llm.max_iterations)),
        }

        return {"primary": primary, "secondary": secondary}

    def get_nanopq_config(self) -> Dict[str, Any]:
        """Get NanoPQ configuration as dictionary."""
        return {
            "num_subvectors": self.nanopq.num_subvectors,
            "num_clusters": self.nanopq.num_clusters,
            "vector_dim": self.embedding.vector_dim,
            "index_path": self.nanopq.index_path,
            "docs_path": self.nanopq.docs_path,
        }

    def get_embedchain_config(self) -> Dict[str, Any]:
        """Get EmbedChain configuration as dictionary."""
        return {
            "db_path": self.embedchain.db_path,
            "provider": self.embedchain.provider,
            "gemini_api_key": self.llm.gemini_api_key,
            "llm": {
                "provider": self.embedchain.llm_provider,
                "config": {
                    "model": self.embedchain.llm_model,
                }
            },
            "embedder": {
                "provider": "google",
                "config": {
                    "model": "models/embedding-001",
                }
            }
        }

    def get_toolbox_config(self) -> Dict[str, Any]:
        """Get Toolbox configuration as dictionary."""
        return {
            "builtin_tools": {
                "shell": self.toolbox.shell_enabled,
                "file_management": self.toolbox.file_management_enabled,
                "calculator": self.toolbox.calculator_enabled,
                "web_search": self.toolbox.web_search_enabled,
                "database": self.toolbox.database_enabled,
            }
        }

    def ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        directories = [
            self.data_dir,
            self.input_dir,
            self.output_dir,
            os.path.dirname(self.nanopq.index_path),
            self.embedchain.db_path,
        ]

        for directory in directories:
            if directory:
                os.makedirs(directory, exist_ok=True)


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings


def load_settings_from_file(config_file: str) -> Settings:
    """
    Load settings from a configuration file.

    Args:
        config_file: Path to configuration file

    Returns:
        Settings instance
    """
    # Set the environment file
    os.environ["ENV_FILE"] = config_file
    return Settings(_env_file=config_file)
