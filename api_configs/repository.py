import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from api_configs.models import APIConfig, APIConfigUpdate


class APIConfigRepository:
    def __init__(self, database_path: str = "./cache/apis") -> None:
        self.database_path = database_path
        Path(self.database_path).mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, api_config_id: str) -> Path:
        return Path(self.database_path) / f"{api_config_id}.json"

    def _get_all_api_configs_index_path(self) -> Path:
        return Path(self.database_path) / "_index.json"

    def _update_index(self, api_config_id: str, action: str = "add") -> None:
        index_path = self._get_all_api_configs_index_path()
        index = []

        if index_path.exists():
            with index_path.open() as f:
                index = json.load(f)

        if action == "add":
            if api_config_id not in index:
                index.append(api_config_id)
        elif action == "remove" and api_config_id in index:
            index.remove(api_config_id)

        with index_path.open("w") as f:
            json.dump(index, f)

    def create(self, api_config: APIConfig) -> APIConfig:
        file_path = self._get_file_path(api_config.config_id)
        with file_path.open("w") as f:
            json.dump(api_config.to_dict(), f, indent=2)
        self._update_index(api_config.config_id, "add")
        return api_config

    def get_by_id(self, api_config_id: str) -> Optional[APIConfig]:
        file_path = self._get_file_path(api_config_id)
        if not file_path.exists():
            return None

        with file_path.open() as f:
            data = json.load(f)
        return APIConfig.from_dict(data)

    def get_all(self) -> list[APIConfig]:
        index_path = self._get_all_api_configs_index_path()
        if not index_path.exists():
            return []

        with index_path.open() as f:
            api_config_ids = json.load(f)

        api_configs = []
        for api_config_id in api_config_ids:
            api_config = self.get_by_id(api_config_id)
            if api_config:
                api_configs.append(api_config)

        return api_configs

    def update(
        self, api_config_id: str, api_config_update: APIConfigUpdate
    ) -> Optional[APIConfig]:
        api_config = self.get_by_id(api_config_id)
        if not api_config:
            return None

        if api_config_update.users is not None:
            api_config.users = api_config_update.users
        if api_config_update.datasets is not None:
            api_config.datasets = api_config_update.datasets

        api_config.updated_at = datetime.utcnow()

        file_path = self._get_file_path(api_config_id)
        with file_path.open("w") as f:
            json.dump(api_config.to_dict(), f, indent=2)

        return api_config

    def delete(self, api_config_id: str) -> bool:
        file_path = self._get_file_path(api_config_id)
        if not file_path.exists():
            return False

        file_path.unlink()
        self._update_index(api_config_id, "remove")
        return True
