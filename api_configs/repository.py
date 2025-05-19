from typing import List, Optional, Dict
from datetime import datetime
from api_configs.models import APIConfig, APIConfigUpdate
import json
import os


class APIConfigRepository:
    def __init__(self, database_path: str = "./cache/apis"):
        self.database_path = database_path
        os.makedirs(self.database_path, exist_ok=True)

    def _get_file_path(self, api_config_id: str) -> str:
        return os.path.join(self.database_path, f"{api_config_id}.json")

    def _get_all_api_configs_index_path(self) -> str:
        return os.path.join(self.database_path, "_index.json")

    def _update_index(self, api_config_id: str, action: str = "add"):
        index_path = self._get_all_api_configs_index_path()
        index = set()

        if os.path.exists(index_path):
            with open(index_path, "r") as f:
                index = set(json.load(f))

        if action == "add":
            index.add(api_config_id)
        elif action == "remove":
            index.discard(api_config_id)

        with open(index_path, "w") as f:
            json.dump(list(index), f)

    def create(self, api_config: APIConfig) -> APIConfig:
        file_path = self._get_file_path(api_config.id)
        with open(file_path, "w") as f:
            json.dump(api_config.to_dict(), f, indent=2)
        self._update_index(api_config.id, "add")
        return api_config

    def get_by_id(self, api_config_id: str) -> Optional[APIConfig]:
        file_path = self._get_file_path(api_config_id)
        if not os.path.exists(file_path):
            return None

        with open(file_path, "r") as f:
            data = json.load(f)
        return APIConfig.from_dict(data)

    def get_all(self) -> List[APIConfig]:
        index_path = self._get_all_api_configs_index_path()
        if not os.path.exists(index_path):
            return []

        with open(index_path, "r") as f:
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
        with open(file_path, "w") as f:
            json.dump(api_config.to_dict(), f, indent=2)

        return api_config

    def delete(self, api_config_id: str) -> bool:
        file_path = self._get_file_path(api_config_id)
        if not os.path.exists(file_path):
            return False

        os.remove(file_path)
        self._update_index(api_config_id, "remove")
        return True
