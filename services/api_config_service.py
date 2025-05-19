import logging
from typing import List, Optional

from api_configs.models import APIConfig, APIConfigUpdate
from api_configs.repository import APIConfigRepository
from database import VectorDBManager

logger = logging.getLogger(__name__)


class APIConfigService:
    """Service layer for API configuration management."""
    
    def __init__(self):
        self.repository = APIConfigRepository()
        self.db_manager = VectorDBManager()
    
    def create_api_config(self, users: List[str], datasets: List[str]) -> APIConfig:
        api_config = APIConfig(users=users, datasets=datasets)
        created_config = self.repository.create(api_config)
        
        # Update metadata for all documents in the datasets
        self._update_document_metadata(created_config.id, datasets)
        
        return created_config
    
    def get_api_config(self, api_config_id: str) -> Optional[APIConfig]:
        return self.repository.get_by_id(api_config_id)
    
    def get_all_api_configs(self) -> List[APIConfig]:
        return self.repository.get_all()
    
    def update_api_config(self, api_config_id: str, api_config_update: APIConfigUpdate) -> Optional[APIConfig]:
        # Get the existing config to compare datasets
        existing_config = self.repository.get_by_id(api_config_id)
        if not existing_config:
            return None
            
        # Update the config
        updated_config = self.repository.update(api_config_id, api_config_update)
        
        if updated_config and api_config_update.datasets is not None:
            # Find newly added datasets
            existing_datasets = set(existing_config.datasets)
            new_datasets = set(api_config_update.datasets)
            added_datasets = new_datasets - existing_datasets
            removed_datasets = existing_datasets - new_datasets
            
            # Update metadata for newly added datasets
            if added_datasets:
                self._update_document_metadata(api_config_id, list(added_datasets))
            
            # Remove metadata from removed datasets
            if removed_datasets:
                self._remove_document_metadata(api_config_id, list(removed_datasets))
        
        return updated_config
    
    def delete_api_config(self, api_config_id: str) -> bool:
        # Get the config before deletion to clean up metadata
        config = self.repository.get_by_id(api_config_id)
        if config:
            # Remove metadata from all documents in this config
            self._remove_document_metadata(api_config_id, config.datasets)
        
        return self.repository.delete(api_config_id)
    
    def check_user_access(self, user: str, dataset: str) -> bool:
        """Check if a user has access to a dataset based on API configurations"""
        api_configs = self.get_all_api_configs()
        
        for api_config in api_configs:
            if user in api_config.users and dataset in api_config.datasets:
                return True
        
        return False
    
    def get_user_accessible_datasets(self, user: str) -> List[str]:
        """Get all datasets a user has access to"""
        accessible_datasets = set()
        api_configs = self.get_all_api_configs()
        
        for api_config in api_configs:
            if user in api_config.users:
                accessible_datasets.update(api_config.datasets)
        
        return list(accessible_datasets)
    
    def get_dataset_authorized_users(self, dataset: str) -> List[str]:
        """Get all users who have access to a dataset"""
        authorized_users = set()
        api_configs = self.get_all_api_configs()
        
        for api_config in api_configs:
            if dataset in api_config.datasets:
                authorized_users.update(api_config.users)
        
        return list(authorized_users)
    
    def _update_document_metadata(self, policy_id: str, dataset_ids: List[str]) -> None:
        """Add policy_id to the metadata of all documents in the datasets."""
        try:
            # We need to update documents one by one to preserve existing metadata
            for dataset_id in dataset_ids:
                # Get the current document data including metadata
                result = self.db_manager.get(
                    collection_name="documents",
                    ids=[dataset_id],
                    include=["metadatas", "documents", "embeddings"]
                )
                
                if result["ids"]:
                    # Get existing metadata
                    current_metadata = result["metadatas"][0] if result["metadatas"] else {}
                    
                    # Add the policy_id to metadata
                    updated_metadata = current_metadata.copy()
                    updated_metadata[policy_id] = True
                    
                    # Update the document with the new metadata
                    self.db_manager.update_data(
                        collection_name="documents",
                        ids=[dataset_id],
                        metadatas=[updated_metadata]
                    )
                    
        except Exception as e:
            # Log error but don't fail the API config creation
            logger.error(f"Failed to update document metadata for policy {policy_id}: {e}")
    
    def _remove_document_metadata(self, policy_id: str, dataset_ids: List[str]) -> None:
        """Remove policy_id from the metadata of all documents in the datasets."""
        try:
            for dataset_id in dataset_ids:
                # Get the current document data including metadata
                result = self.db_manager.get(
                    collection_name="documents",
                    ids=[dataset_id],
                    include=["metadatas", "documents", "embeddings"]
                )
                
                if result["ids"]:
                    # Get existing metadata
                    current_metadata = result["metadatas"][0] if result["metadatas"] else {}
                    
                    # Remove the policy_id from metadata
                    if policy_id in current_metadata:
                        updated_metadata = current_metadata.copy()
                        del updated_metadata[policy_id]
                        
                        # Update the document with the new metadata
                        self.db_manager.update_data(
                            collection_name="documents",
                            ids=[dataset_id],
                            metadatas=[updated_metadata]
                        )
                        
        except Exception as e:
            # Log error but don't fail the operation
            logger.error(f"Failed to remove document metadata for policy {policy_id}: {e}")