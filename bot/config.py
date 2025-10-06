from pathlib import Path

import toml
from pydantic import BaseModel


class BotConfig(BaseModel):
    token: str


class ConfigModel(BaseModel):
    bot: BotConfig


class Config:
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.config_model: ConfigModel = self.load_config()

    def load_config(self) -> ConfigModel:
        try:
            return ConfigModel.model_validate(toml.load(self.file_path))
        except FileNotFoundError:
            raise FileNotFoundError(f"Config file {self.file_path} not found.")
        except toml.TomlDecodeError:
            raise ValueError(f"Error decoding TOML from {self.file_path}.")
        except Exception as e:
            raise RuntimeError(f"An unexpected error occurred: {e}")
