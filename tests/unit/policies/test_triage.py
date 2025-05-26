"""Unit tests for triage functionality."""

import pytest
from datetime import datetime, timezone

from policies.models import PolicyRule, RuleOperator
from policies.triage_models import TriageRequest, TriageUpdate
from policies.triage_repository import TriageRepository


@pytest.fixture
def temp_triage_dir(tmp_path):
    """Create a temporary directory for triage files."""
    return str(tmp_path / "triage")


@pytest.fixture
def triage_repo(temp_triage_dir):
    """Create a TriageRepository with temporary directory."""
    return TriageRepository(base_path=temp_triage_dir)


@pytest.fixture
def sample_triage_request():
    """Create a sample triage request."""
    return TriageRequest(
        user_id="test_user",
        prompt_id="prompt_123",
        api_config_id="api_config_456",
        policy_rule_id="rule_789",
        prompt_query="What is the weather today?",
        documents_retrieved=["doc1", "doc2"],
        generated_response="I cannot provide weather information.",
        conversation_key="test_user_conversation",
    )


def test_triage_request_creation(sample_triage_request):
    """Test creating a triage request."""
    assert sample_triage_request.status == "pending"
    assert sample_triage_request.user_id == "test_user"
    assert sample_triage_request.prompt_id == "prompt_123"
    assert len(sample_triage_request.documents_retrieved) == 2


def test_triage_request_serialization(sample_triage_request):
    """Test triage request to_dict and from_dict."""
    data = sample_triage_request.to_dict()
    assert data["user_id"] == "test_user"
    assert data["status"] == "pending"

    # Test deserialization
    restored = TriageRequest.from_dict(data)
    assert restored.user_id == sample_triage_request.user_id
    assert restored.prompt_id == sample_triage_request.prompt_id
    assert restored.status == sample_triage_request.status


def test_triage_repository_create(triage_repo, sample_triage_request):
    """Test creating a triage request in repository."""
    created = triage_repo.create(sample_triage_request)
    assert created.triage_id == sample_triage_request.triage_id

    # Verify it was saved
    retrieved = triage_repo.get(created.triage_id)
    assert retrieved is not None
    assert retrieved.user_id == sample_triage_request.user_id


def test_triage_repository_list_pending(triage_repo):
    """Test listing pending triage requests."""
    # Create multiple requests
    for i in range(3):
        request = TriageRequest(
            user_id=f"user_{i}",
            prompt_id=f"prompt_{i}",
            api_config_id="api_config_1",
            policy_rule_id="rule_1",
            prompt_query=f"Query {i}",
            generated_response=f"Response {i}",
        )
        triage_repo.create(request)

    # List pending
    pending = triage_repo.list_pending()
    assert len(pending) == 3
    assert all(r.status == "pending" for r in pending)


def test_triage_repository_update_status(triage_repo, sample_triage_request):
    """Test updating triage request status."""
    created = triage_repo.create(sample_triage_request)

    # Approve the request
    update = TriageUpdate(
        status="approved",
        reviewed_by="admin",
    )
    updated = triage_repo.update_status(created.triage_id, update)

    assert updated is not None
    assert updated.status == "approved"
    assert updated.reviewed_by == "admin"
    assert updated.reviewed_at is not None


def test_triage_repository_reject_with_reason(triage_repo, sample_triage_request):
    """Test rejecting a triage request with reason."""
    created = triage_repo.create(sample_triage_request)

    # Reject the request
    update = TriageUpdate(
        status="rejected",
        reviewed_by="admin",
        rejection_reason="Content violates policy",
    )
    updated = triage_repo.update_status(created.triage_id, update)

    assert updated is not None
    assert updated.status == "rejected"
    assert updated.rejection_reason == "Content violates policy"


def test_triage_action_in_policy_rule():
    """Test that triage action is valid in PolicyRule."""
    rule = PolicyRule(
        metric_key="content_sensitivity",
        operator=RuleOperator.GREATER_THAN,
        threshold=0.7,
        action="triage",
        message="Content requires manual review",
    )

    assert rule.action == "triage"
    assert rule.message == "Content requires manual review"

    # Test serialization
    data = rule.to_dict()
    assert data["action"] == "triage"


def test_triage_repository_cleanup(triage_repo):
    """Test cleanup of old triage requests."""
    # Create an old approved request
    old_request = TriageRequest(
        user_id="user_old",
        prompt_id="prompt_old",
        api_config_id="api_1",
        policy_rule_id="rule_1",
        prompt_query="Old query",
        generated_response="Old response",
    )
    old_request.created_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
    created = triage_repo.create(old_request)

    # Approve it with old date
    update = TriageUpdate(
        status="approved",
        reviewed_by="admin",
        reviewed_at=datetime(2020, 1, 2, tzinfo=timezone.utc),
    )
    triage_repo.update_status(created.triage_id, update)

    # Create a recent pending request
    recent_request = TriageRequest(
        user_id="user_recent",
        prompt_id="prompt_recent",
        api_config_id="api_1",
        policy_rule_id="rule_1",
        prompt_query="Recent query",
        generated_response="Recent response",
    )
    triage_repo.create(recent_request)

    # Cleanup requests older than 30 days
    deleted_count = triage_repo.cleanup_old_requests(days=30)

    assert deleted_count == 1
    assert triage_repo.get(created.triage_id) is None
    assert triage_repo.get(recent_request.triage_id) is not None
