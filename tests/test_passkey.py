"""Tests for passkey authentication functionality."""
import base64
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.database import get_db_session
from app.repositories.user_repository import UserRepository
from app.repositories.passkey_repository import PasskeyCredentialRepository
from app.auth.models import UserCreate
from app.auth.webauthn_service import webauthn_service
from app.auth.passkey_models import PasskeyCredentialCreate


client = TestClient(app)


@pytest.fixture
async def test_user(db_session: AsyncSession):
    """Create a test user."""
    user_repo = UserRepository(db_session)
    user_data = UserCreate(
        email="testuser@example.com",
        username="testuser",
        password="testpassword123"
    )
    user = await user_repo.create(user_data)
    return user


@pytest.fixture
def mock_webauthn_service():
    """Mock WebAuthn service for testing."""
    with patch('app.api.passkey.webauthn_service') as mock:
        yield mock


class TestPasskeyRegistration:
    """Test passkey registration endpoints."""
    
    async def test_begin_passkey_registration_success(self, test_user, db_session):
        """Test beginning passkey registration for valid user."""
        
        # Mock database session
        app.dependency_overrides[get_db_session] = lambda: db_session
        
        request_data = {
            "username": test_user.username
        }
        
        response = client.post("/api/v1/passkey/register/begin", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check required WebAuthn fields
        assert "challenge" in data
        assert "rp" in data
        assert "user" in data
        assert "pubKeyCredParams" in data
        assert data["rp"]["id"] == "localhost"
        assert data["user"]["name"] == test_user.username
        
        # Clean up
        app.dependency_overrides.clear()
    
    async def test_begin_passkey_registration_user_not_found(self, db_session):
        """Test beginning passkey registration for non-existent user."""
        
        app.dependency_overrides[get_db_session] = lambda: db_session
        
        request_data = {
            "username": "nonexistent"
        }
        
        response = client.post("/api/v1/passkey/register/begin", json=request_data)
        
        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]
        
        app.dependency_overrides.clear()
    
    async def test_complete_passkey_registration_success(self, test_user, db_session, mock_webauthn_service):
        """Test completing passkey registration successfully."""
        
        # Mock WebAuthn verification
        mock_webauthn_service.verify_registration_response.return_value = (True, {
            'credential_id': 'test_credential_id_123',
            'public_key': b'mock_public_key_data',
            'sign_count': 0,
            'aaguid': 'test_aaguid'
        })
        
        # Mock authentication dependency
        async def mock_get_current_user():
            return test_user
        
        app.dependency_overrides[get_db_session] = lambda: db_session
        
        # Create a mock registration response
        registration_response = {
            "id": "test_credential_id_123",
            "rawId": "test_credential_id_123",
            "response": {
                "attestationObject": base64.b64encode(b"mock_attestation").decode(),
                "clientDataJSON": base64.b64encode(json.dumps({
                    "type": "webauthn.create",
                    "challenge": "mock_challenge",
                    "origin": "http://localhost:8000"
                }).encode()).decode()
            },
            "type": "public-key",
            "name": "My Test Passkey"
        }
        
        # Mock the current user dependency
        from app.auth.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = mock_get_current_user
        
        response = client.post("/api/v1/passkey/register/complete", json=registration_response)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["credential_id"] == "test_credential_id_123"
        assert data["name"] == "My Test Passkey"
        assert data["is_active"] is True
        
        app.dependency_overrides.clear()
    
    async def test_complete_passkey_registration_verification_failed(self, test_user, db_session, mock_webauthn_service):
        """Test completing passkey registration with verification failure."""
        
        # Mock WebAuthn verification failure
        mock_webauthn_service.verify_registration_response.return_value = (False, {
            'error': 'Challenge mismatch'
        })
        
        async def mock_get_current_user():
            return test_user
        
        app.dependency_overrides[get_db_session] = lambda: db_session
        
        registration_response = {
            "id": "test_credential_id_123",
            "rawId": "test_credential_id_123",
            "response": {
                "attestationObject": base64.b64encode(b"mock_attestation").decode(),
                "clientDataJSON": base64.b64encode(json.dumps({
                    "type": "webauthn.create",
                    "challenge": "wrong_challenge",
                    "origin": "http://localhost:8000"
                }).encode()).decode()
            },
            "type": "public-key"
        }
        
        from app.auth.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = mock_get_current_user
        
        response = client.post("/api/v1/passkey/register/complete", json=registration_response)
        
        assert response.status_code == 400
        assert "Registration verification failed" in response.json()["detail"]
        
        app.dependency_overrides.clear()


class TestPasskeyAuthentication:
    """Test passkey authentication endpoints."""
    
    async def test_begin_passkey_authentication_with_username(self, test_user, db_session):
        """Test beginning passkey authentication with username."""
        
        # First create a passkey credential for the user
        passkey_repo = PasskeyCredentialRepository(db_session)
        credential_data = PasskeyCredentialCreate(
            credential_id="test_cred_123",
            public_key=b"mock_public_key",
            sign_count=0,
            name="Test Passkey"
        )
        await passkey_repo.create(test_user.id, credential_data)
        
        app.dependency_overrides[get_db_session] = lambda: db_session
        
        request_data = {
            "username": test_user.username
        }
        
        response = client.post("/api/v1/passkey/authenticate/begin", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "challenge" in data
        assert "rpId" in data
        assert "allowCredentials" in data
        assert len(data["allowCredentials"]) > 0
        
        app.dependency_overrides.clear()
    
    async def test_begin_passkey_authentication_usernameless(self, db_session):
        """Test beginning passkey authentication without username (usernameless flow)."""
        
        app.dependency_overrides[get_db_session] = lambda: db_session
        
        request_data = {}
        
        response = client.post("/api/v1/passkey/authenticate/begin", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "challenge" in data
        assert "rpId" in data
        assert "allowCredentials" in data
        assert len(data["allowCredentials"]) == 0  # Empty for usernameless
        
        app.dependency_overrides.clear()
    
    async def test_begin_passkey_authentication_no_credentials(self, test_user, db_session):
        """Test beginning passkey authentication for user with no credentials."""
        
        app.dependency_overrides[get_db_session] = lambda: db_session
        
        request_data = {
            "username": test_user.username
        }
        
        response = client.post("/api/v1/passkey/authenticate/begin", json=request_data)
        
        assert response.status_code == 404
        assert "No passkey credentials found" in response.json()["detail"]
        
        app.dependency_overrides.clear()
    
    async def test_complete_passkey_authentication_success(self, test_user, db_session, mock_webauthn_service):
        """Test completing passkey authentication successfully."""
        
        # Create a passkey credential for the user
        passkey_repo = PasskeyCredentialRepository(db_session)
        credential_data = PasskeyCredentialCreate(
            credential_id="test_cred_123",
            public_key=b"mock_public_key",
            sign_count=0,
            name="Test Passkey"
        )
        credential = await passkey_repo.create(test_user.id, credential_data)
        
        # Mock WebAuthn verification success
        mock_webauthn_service.verify_authentication_response.return_value = (True, {
            'sign_count': 1
        })
        mock_webauthn_service.get_challenge.return_value = "mock_challenge"
        
        app.dependency_overrides[get_db_session] = lambda: db_session
        
        authentication_response = {
            "id": "test_cred_123",
            "rawId": "test_cred_123",
            "response": {
                "authenticatorData": base64.b64encode(b"mock_auth_data").decode(),
                "clientDataJSON": base64.b64encode(json.dumps({
                    "type": "webauthn.get",
                    "challenge": "mock_challenge",
                    "origin": "http://localhost:8000"
                }).encode()).decode(),
                "signature": base64.b64encode(b"mock_signature").decode()
            },
            "type": "public-key"
        }
        
        response = client.post("/api/v1/passkey/authenticate/complete", json=authentication_response)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "user" in data
        assert data["user"]["username"] == test_user.username
        
        app.dependency_overrides.clear()
    
    async def test_complete_passkey_authentication_invalid_credential(self, db_session, mock_webauthn_service):
        """Test completing passkey authentication with invalid credential."""
        
        app.dependency_overrides[get_db_session] = lambda: db_session
        
        authentication_response = {
            "id": "nonexistent_cred",
            "rawId": "nonexistent_cred",
            "response": {
                "authenticatorData": base64.b64encode(b"mock_auth_data").decode(),
                "clientDataJSON": base64.b64encode(json.dumps({
                    "type": "webauthn.get",
                    "challenge": "mock_challenge",
                    "origin": "http://localhost:8000"
                }).encode()).decode(),
                "signature": base64.b64encode(b"mock_signature").decode()
            },
            "type": "public-key"
        }
        
        response = client.post("/api/v1/passkey/authenticate/complete", json=authentication_response)
        
        assert response.status_code == 404
        assert "Credential not found" in response.json()["detail"]
        
        app.dependency_overrides.clear()


class TestPasskeyManagement:
    """Test passkey management endpoints."""
    
    async def test_list_user_passkeys(self, test_user, db_session):
        """Test listing user's passkey credentials."""
        
        # Create some passkey credentials
        passkey_repo = PasskeyCredentialRepository(db_session)
        
        credential1 = PasskeyCredentialCreate(
            credential_id="cred_1",
            public_key=b"key_1",
            sign_count=0,
            name="First Passkey"
        )
        credential2 = PasskeyCredentialCreate(
            credential_id="cred_2",
            public_key=b"key_2",
            sign_count=5,
            name="Second Passkey"
        )
        
        await passkey_repo.create(test_user.id, credential1)
        await passkey_repo.create(test_user.id, credential2)
        
        # Mock authentication
        async def mock_get_current_user():
            return test_user
        
        app.dependency_overrides[get_db_session] = lambda: db_session
        from app.auth.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = mock_get_current_user
        
        response = client.get("/api/v1/passkey/credentials")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) == 2
        credential_names = [cred["name"] for cred in data]
        assert "First Passkey" in credential_names
        assert "Second Passkey" in credential_names
        
        app.dependency_overrides.clear()
    
    async def test_delete_passkey_credential(self, test_user, db_session):
        """Test deleting a passkey credential."""
        
        # Create a passkey credential
        passkey_repo = PasskeyCredentialRepository(db_session)
        credential_data = PasskeyCredentialCreate(
            credential_id="cred_to_delete",
            public_key=b"key_data",
            sign_count=0,
            name="Credential to Delete"
        )
        await passkey_repo.create(test_user.id, credential_data)
        
        # Mock authentication
        async def mock_get_current_user():
            return test_user
        
        app.dependency_overrides[get_db_session] = lambda: db_session
        from app.auth.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = mock_get_current_user
        
        response = client.delete("/api/v1/passkey/credentials/cred_to_delete")
        
        assert response.status_code == 200
        assert "Credential deleted successfully" in response.json()["message"]
        
        # Verify credential is deleted
        deleted_cred = await passkey_repo.get_by_credential_id("cred_to_delete")
        assert deleted_cred is None
        
        app.dependency_overrides.clear()
    
    async def test_delete_nonexistent_passkey_credential(self, test_user, db_session):
        """Test deleting a non-existent passkey credential."""
        
        async def mock_get_current_user():
            return test_user
        
        app.dependency_overrides[get_db_session] = lambda: db_session
        from app.auth.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = mock_get_current_user
        
        response = client.delete("/api/v1/passkey/credentials/nonexistent_cred")
        
        assert response.status_code == 404
        assert "Credential not found" in response.json()["detail"]
        
        app.dependency_overrides.clear()


class TestWebAuthnService:
    """Test WebAuthn service functionality."""
    
    def test_generate_challenge(self):
        """Test challenge generation."""
        challenge = webauthn_service.generate_challenge()
        
        assert isinstance(challenge, str)
        assert len(challenge) > 0
        
        # Generate another challenge and ensure they're different
        challenge2 = webauthn_service.generate_challenge()
        assert challenge != challenge2
    
    def test_challenge_storage_and_retrieval(self):
        """Test challenge storage and retrieval."""
        user_id = 123
        challenge = "test_challenge_123"
        
        # Store challenge
        webauthn_service.store_challenge(user_id, challenge)
        
        # Retrieve challenge
        retrieved = webauthn_service.get_challenge(user_id)
        assert retrieved == challenge
        
        # Clear challenge
        webauthn_service.clear_challenge(user_id)
        cleared = webauthn_service.get_challenge(user_id)
        assert cleared is None
    
    def test_challenge_expiration(self):
        """Test challenge expiration."""
        user_id = 123
        challenge = "test_challenge_123"
        
        # Store challenge with very short expiration
        webauthn_service.store_challenge(user_id, challenge, expires_in=0)
        
        # Should be expired immediately
        retrieved = webauthn_service.get_challenge(user_id)
        assert retrieved is None
    
    def test_create_registration_options(self):
        """Test creation of registration options."""
        user_id = 123
        username = "testuser"
        display_name = "Test User"
        
        options = webauthn_service.create_registration_options(
            user_id=user_id,
            username=username,
            display_name=display_name
        )
        
        assert "challenge" in options
        assert "rp" in options
        assert "user" in options
        assert "pubKeyCredParams" in options
        
        assert options["rp"]["id"] == "localhost"
        assert options["user"]["name"] == username
        assert options["user"]["displayName"] == display_name
        
        # Check that challenge was stored
        stored_challenge = webauthn_service.get_challenge(user_id)
        assert stored_challenge == options["challenge"]
    
    def test_create_authentication_options(self):
        """Test creation of authentication options."""
        user_id = 123
        allow_credentials = ["cred1", "cred2"]
        
        options, challenge = webauthn_service.create_authentication_options(
            user_id=user_id,
            allow_credentials=allow_credentials
        )
        
        assert "challenge" in options
        assert "rpId" in options
        assert "allowCredentials" in options
        
        assert options["rpId"] == "localhost"
        assert len(options["allowCredentials"]) == 2
        
        # Check that challenge was stored
        stored_challenge = webauthn_service.get_challenge(user_id)
        assert stored_challenge == challenge
        assert stored_challenge == options["challenge"]


# Fixtures for async testing
@pytest.fixture
async def db_session():
    """Create a test database session."""
    # This would typically create a test database session
    # For now, we'll use a mock
    from unittest.mock import MagicMock
    session = MagicMock()
    session.commit = MagicMock()
    session.refresh = MagicMock()
    session.add = MagicMock()
    return session