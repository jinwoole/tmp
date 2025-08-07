"""Tests for PasskeyCredentialRepository functionality."""
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.passkey_repository import PasskeyCredentialRepository
from app.repositories.user_repository import UserRepository
from app.auth.models import UserCreate
from app.auth.passkey_models import PasskeyCredentialCreate


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession):
    """Create a test user for passkey tests."""
    user_repo = UserRepository(db_session)
    user_data = UserCreate(
        email="passkey_user@example.com",
        username="passkeyuser",
        password="testpassword123"
    )
    user = await user_repo.create(user_data)
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def passkey_repo(db_session: AsyncSession):
    """Create PasskeyCredentialRepository instance."""
    return PasskeyCredentialRepository(db_session)


@pytest_asyncio.fixture
async def sample_credential_data():
    """Sample passkey credential data for testing."""
    return PasskeyCredentialCreate(
        credential_id="test_credential_123",
        public_key=b"mock_public_key_data",
        sign_count=0,
        name="Test Passkey"
    )


class TestPasskeyCredentialRepository:
    """Test PasskeyCredentialRepository CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_create_credential(self, passkey_repo, test_user, sample_credential_data):
        """Test creating a new passkey credential."""
        credential = await passkey_repo.create(test_user.id, sample_credential_data)
        
        assert credential.id is not None
        assert credential.user_id == test_user.id
        assert credential.credential_id == sample_credential_data.credential_id
        assert credential.public_key == sample_credential_data.public_key
        assert credential.sign_count == sample_credential_data.sign_count
        assert credential.name == sample_credential_data.name
        assert credential.is_active is True
        assert isinstance(credential.created_at, datetime)
    
    @pytest.mark.asyncio
    async def test_get_by_credential_id(self, passkey_repo, test_user, sample_credential_data):
        """Test retrieving credential by credential ID."""
        # Create credential
        created_credential = await passkey_repo.create(test_user.id, sample_credential_data)
        
        # Retrieve credential
        retrieved_credential = await passkey_repo.get_by_credential_id(sample_credential_data.credential_id)
        
        assert retrieved_credential is not None
        assert retrieved_credential.id == created_credential.id
        assert retrieved_credential.user_id == test_user.id
        assert retrieved_credential.user.username == test_user.username
    
    @pytest.mark.asyncio
    async def test_get_by_credential_id_not_found(self, passkey_repo):
        """Test retrieving non-existent credential returns None."""
        result = await passkey_repo.get_by_credential_id("non_existent_credential")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_by_user_id(self, passkey_repo, test_user):
        """Test retrieving all credentials for a user."""
        # Create multiple credentials
        credential_data_1 = PasskeyCredentialCreate(
            credential_id="test_credential_1",
            public_key=b"mock_public_key_1",
            sign_count=0,
            name="Passkey 1"
        )
        credential_data_2 = PasskeyCredentialCreate(
            credential_id="test_credential_2",
            public_key=b"mock_public_key_2",
            sign_count=5,
            name="Passkey 2"
        )
        
        await passkey_repo.create(test_user.id, credential_data_1)
        await passkey_repo.create(test_user.id, credential_data_2)
        
        # Retrieve all credentials for user
        credentials = await passkey_repo.get_by_user_id(test_user.id)
        
        assert len(credentials) == 2
        assert all(cred.user_id == test_user.id for cred in credentials)
        assert all(cred.is_active is True for cred in credentials)
        # Should be ordered by created_at desc
        assert credentials[0].created_at >= credentials[1].created_at
    
    @pytest.mark.asyncio
    async def test_get_by_user_id_empty(self, passkey_repo, test_user):
        """Test retrieving credentials for user with no credentials."""
        credentials = await passkey_repo.get_by_user_id(test_user.id)
        assert credentials == []
    
    @pytest.mark.asyncio
    async def test_update_sign_count(self, passkey_repo, test_user, sample_credential_data):
        """Test updating sign count for a credential."""
        # Create credential
        credential = await passkey_repo.create(test_user.id, sample_credential_data)
        initial_sign_count = credential.sign_count
        
        # Update sign count
        new_sign_count = initial_sign_count + 10
        result = await passkey_repo.update_sign_count(credential.credential_id, new_sign_count)
        
        assert result is True
        
        # Verify update
        updated_credential = await passkey_repo.get_by_credential_id(credential.credential_id)
        assert updated_credential.sign_count == new_sign_count
        assert updated_credential.last_used is not None
    
    @pytest.mark.asyncio
    async def test_update_sign_count_not_found(self, passkey_repo):
        """Test updating sign count for non-existent credential."""
        result = await passkey_repo.update_sign_count("non_existent_credential", 10)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_deactivate_credential(self, passkey_repo, test_user, sample_credential_data):
        """Test deactivating a passkey credential."""
        # Create credential
        credential = await passkey_repo.create(test_user.id, sample_credential_data)
        
        # Deactivate credential
        result = await passkey_repo.deactivate(credential.credential_id, test_user.id)
        assert result is True
        
        # Verify credential is deactivated
        deactivated_credential = await passkey_repo.get_by_credential_id(credential.credential_id)
        assert deactivated_credential is None  # Should not be returned as it's inactive
    
    @pytest.mark.asyncio
    async def test_deactivate_credential_not_found(self, passkey_repo, test_user):
        """Test deactivating non-existent credential."""
        result = await passkey_repo.deactivate("non_existent_credential", test_user.id)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_deactivate_credential_wrong_user(self, passkey_repo, test_user, sample_credential_data):
        """Test deactivating credential with wrong user ID."""
        # Create credential
        credential = await passkey_repo.create(test_user.id, sample_credential_data)
        
        # Try to deactivate with wrong user ID
        result = await passkey_repo.deactivate(credential.credential_id, test_user.id + 999)
        assert result is False
        
        # Verify credential is still active
        active_credential = await passkey_repo.get_by_credential_id(credential.credential_id)
        assert active_credential is not None
        assert active_credential.is_active is True
    
    @pytest.mark.asyncio
    async def test_delete_credential(self, passkey_repo, test_user, sample_credential_data):
        """Test permanently deleting a passkey credential."""
        # Create credential
        credential = await passkey_repo.create(test_user.id, sample_credential_data)
        
        # Delete credential
        result = await passkey_repo.delete(credential.credential_id, test_user.id)
        assert result is True
        
        # Verify credential is deleted
        deleted_credential = await passkey_repo.get_by_credential_id(credential.credential_id)
        assert deleted_credential is None
    
    @pytest.mark.asyncio
    async def test_delete_credential_not_found(self, passkey_repo, test_user):
        """Test deleting non-existent credential."""
        result = await passkey_repo.delete("non_existent_credential", test_user.id)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_delete_credential_wrong_user(self, passkey_repo, test_user, sample_credential_data):
        """Test deleting credential with wrong user ID."""
        # Create credential
        credential = await passkey_repo.create(test_user.id, sample_credential_data)
        
        # Try to delete with wrong user ID
        result = await passkey_repo.delete(credential.credential_id, test_user.id + 999)
        assert result is False
        
        # Verify credential still exists
        existing_credential = await passkey_repo.get_by_credential_id(credential.credential_id)
        assert existing_credential is not None
    
    @pytest.mark.asyncio
    async def test_get_credential_ids_for_user(self, passkey_repo, test_user):
        """Test getting all credential IDs for a user."""
        # Create multiple credentials
        credential_data_1 = PasskeyCredentialCreate(
            credential_id="cred_id_1",
            public_key=b"public_key_1",
            sign_count=0,
            name="Passkey 1"
        )
        credential_data_2 = PasskeyCredentialCreate(
            credential_id="cred_id_2",
            public_key=b"public_key_2",
            sign_count=0,
            name="Passkey 2"
        )
        
        await passkey_repo.create(test_user.id, credential_data_1)
        await passkey_repo.create(test_user.id, credential_data_2)
        
        # Get credential IDs
        credential_ids = await passkey_repo.get_credential_ids_for_user(test_user.id)
        
        assert len(credential_ids) == 2
        assert "cred_id_1" in credential_ids
        assert "cred_id_2" in credential_ids
    
    @pytest.mark.asyncio
    async def test_get_credential_ids_excludes_inactive(self, passkey_repo, test_user):
        """Test that get_credential_ids_for_user excludes inactive credentials."""
        # Create two credentials
        credential_data_1 = PasskeyCredentialCreate(
            credential_id="active_cred",
            public_key=b"active_key",
            sign_count=0,
            name="Active Passkey"
        )
        credential_data_2 = PasskeyCredentialCreate(
            credential_id="inactive_cred",
            public_key=b"inactive_key",
            sign_count=0,
            name="Inactive Passkey"
        )
        
        await passkey_repo.create(test_user.id, credential_data_1)
        await passkey_repo.create(test_user.id, credential_data_2)
        
        # Deactivate one credential
        await passkey_repo.deactivate("inactive_cred", test_user.id)
        
        # Get credential IDs - should only return active ones
        credential_ids = await passkey_repo.get_credential_ids_for_user(test_user.id)
        
        assert len(credential_ids) == 1
        assert "active_cred" in credential_ids
        assert "inactive_cred" not in credential_ids


class TestPasskeyCredentialRepositoryEdgeCases:
    """Test edge cases and error scenarios for PasskeyCredentialRepository."""
    
    @pytest.mark.asyncio
    async def test_create_credential_with_duplicate_id(self, passkey_repo, test_user):
        """Test creating credential with duplicate credential_id should fail."""
        credential_data = PasskeyCredentialCreate(
            credential_id="duplicate_cred_id",
            public_key=b"public_key_1",
            sign_count=0,
            name="First Passkey"
        )
        
        # Create first credential
        await passkey_repo.create(test_user.id, credential_data)
        
        # Try to create another with same credential_id
        duplicate_credential_data = PasskeyCredentialCreate(
            credential_id="duplicate_cred_id",
            public_key=b"public_key_2",
            sign_count=0,
            name="Duplicate Passkey"
        )
        
        with pytest.raises(Exception):  # Should raise integrity error
            await passkey_repo.create(test_user.id, duplicate_credential_data)
    
    @pytest.mark.asyncio
    async def test_create_credential_with_none_values(self, passkey_repo, test_user):
        """Test creating credential with optional None values."""
        credential_data = PasskeyCredentialCreate(
            credential_id="cred_with_none",
            public_key=b"public_key",
            sign_count=0,
            name=None  # None name should be allowed
        )
        
        credential = await passkey_repo.create(test_user.id, credential_data)
        assert credential.name is None
        assert credential.last_used is None
        
        # Should still be retrievable
        retrieved = await passkey_repo.get_by_credential_id("cred_with_none")
        assert retrieved is not None
        assert retrieved.name is None