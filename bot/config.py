import toml
from pydantic import BaseModel

class BotConfig(BaseModel):
    token: str

class ConfigModel(BaseModel):
    bot: BotConfig

class Config:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.config: ConfigModel = self.load_config()

    def load_config(self) -> ConfigModel:
        with open(self.file_path, 'r') as f:
            data = toml.load(f)
            return ConfigModel.model_validate_json(toml.dumps(data))
        raise FileNotFoundError(f"Config file {self.file_path} not found.")