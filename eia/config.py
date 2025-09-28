import yaml
from pydantic import BaseModel, Field, EmailStr, HttpUrl
from typing import List, Optional

# --- Pydantic Models for Configuration Validation ---

class EmailAccount(BaseModel):
    email: EmailStr
    password: str
    imap_server: str
    imap_port: int = 993
    use_ssl: bool = True
    folders_to_scan: List[str] = Field(default_factory=lambda: ["INBOX"])

class ImapSettings(BaseModel):
    scan_interval_minutes: int = 10
    mark_as_seen: bool = True

class DatabaseSettings(BaseModel):
    url: str = "postgresql://user:password@localhost/eia_db"

class RedisSettings(BaseModel):
    url: str = "redis://localhost:6379/0"

class NlpSettings(BaseModel):
    classification_model: str = "mrm8488/distilbert-base-spanish-uncased-finetuned-spa-squad2-es"
    ner_model: str = "es_core_news_lg"
    summarization_model: str = "Josue-DL/t5-base-spanish-summarization"
    similarity_threshold: float = Field(default=0.75, ge=0, le=1)

class TelegramSettings(BaseModel):
    enabled: bool = False
    bot_token: Optional[str] = None
    chat_id: Optional[str] = None

class AlertSettings(BaseModel):
    send_email_notifications: bool = True
    notification_email_recipient: Optional[EmailStr] = None
    telegram: TelegramSettings = Field(default_factory=TelegramSettings)

class ServerSettings(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8000

class AppConfig(BaseModel):
    email_accounts: List[EmailAccount]
    imap: ImapSettings = Field(default_factory=ImapSettings)
    database: DatabaseSettings
    redis: RedisSettings
    nlp: NlpSettings = Field(default_factory=NlpSettings)
    product_catalog_path: str = "catalog.yml"
    alerts: AlertSettings = Field(default_factory=AlertSettings)
    server: ServerSettings = Field(default_factory=ServerSettings)


# --- Configuration Loading Function ---

def load_config(config_path: str = "config.yml") -> AppConfig:
    """
    Loads the application configuration from a YAML file and validates it.

    Args:
        config_path: The path to the configuration file.

    Returns:
        An AppConfig object with the loaded and validated settings.

    Raises:
        FileNotFoundError: If the config file is not found.
        ValueError: If the config file is invalid.
    """
    try:
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Configuration file not found at '{config_path}'. "
            "Please copy 'config.yml.example' to 'config.yml' and fill it out."
        )
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing YAML file: {e}")

    if not config_data:
        raise ValueError("Configuration file is empty.")

    try:
        return AppConfig(**config_data)
    except Exception as e:
        # Pydantic's ValidationError can be complex, so we wrap it.
        raise ValueError(f"Configuration validation error: {e}")

# --- Global Config Object ---

# Load the configuration once when the module is imported.
# The application will use this `settings` object to access configuration.
try:
    settings = load_config()
except (FileNotFoundError, ValueError) as e:
    # This will print an error message and exit if the config is not valid.
    # This is useful for preventing the app from starting with a bad config.
    print(f"Error: Could not load configuration. {e}")
    # In a real application, you might want to handle this more gracefully.
    # For now, we'll allow the import to succeed but `settings` will be None.
    settings = None

if __name__ == "__main__":
    # Example of how to use the configuration loader
    # This part will only run when the script is executed directly
    if settings:
        print("Configuration loaded successfully!")
        print("\n--- Database URL ---")
        print(settings.database.url)
        print("\n--- First Email Account ---")
        if settings.email_accounts:
            print(settings.email_accounts[0].email)
        print("\n--- NLP Model ---")
        print(settings.nlp.classification_model)
    else:
        print("Failed to load configuration.")