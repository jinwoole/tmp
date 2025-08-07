"""Comprehensive end-to-end tests for Passkey authentication flows."""
import base64
import json
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.database import get_db_session
from app.repositories.user_repository import UserRepository
from app.repositories.passkey_repository import PasskeyCredentialRepository
from app.auth.models import UserCreate
from app.auth.webauthn_service import webauthn_service


# Mock WebAuthn response data for testing
MOCK_REGISTRATION_RESPONSE = {
    "id": "test_credential_id_123",
    "rawId": "test_credential_id_123",
    "response": {
        "attestationObject": base64.urlsafe_b64encode(b"mock_attestation_object").decode(),
        "clientDataJSON": base64.urlsafe_b64encode(
            json.dumps({
                "type": "webauthn.create",
                "challenge": "mock_challenge",
                "origin": "http://localhost:8000"
            }).encode()
        ).decode()
    },
    "type": "public-key",
    "clientExtensionResults": {},
    "name": "Test Device"
}

MOCK_AUTHENTICATION_RESPONSE = {
    "id": "test_credential_id_123",
    "rawId": "test_credential_id_123", 
    "response": {
        "authenticatorData": base64.urlsafe_b64encode(b"mock_authenticator_data").decode(),
        "clientDataJSON": base64.urlsafe_b64encode(
            json.dumps({
                "type": "webauthn.get",
                "challenge": "mock_challenge",
                "origin": "http://localhost:8000"
            }).encode()
        ).decode(),
        "signature": base64.urlsafe_b64encode(b"mock_signature").decode()
    },
    "type": "public-key",
    "clientExtensionResults": {}
}


@pytest_asyncio.fixture
async def test_user_for_flows(db_session: AsyncSession):
    """Create a test user for end-to-end flows."""
    user_repo = UserRepository(db_session)
    user_data = UserCreate(
        email="flow_test@example.com",
        username="flowtest",
        password="testpassword123"
    )
    user = await user_repo.create(user_data)
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def authenticated_client(test_user_for_flows, db_session):
    """Create authenticated test client."""
    from app.auth.security import create_access_token
    from datetime import timedelta
    
    # Create access token
    access_token = create_access_token(
        data={"sub": test_user_for_flows.username, "user_id": test_user_for_flows.id},
        expires_delta=timedelta(minutes=30)
    )
    
    def get_test_db():
        return db_session
    
    app.dependency_overrides[get_db_session] = get_test_db
    
    client = TestClient(app)
    client.headers = {"Authorization": f"Bearer {access_token}"}
    
    yield client
    
    app.dependency_overrides.clear()


class TestPasskeyRegistrationFlow:
    """Test complete passkey registration flow."""
    
    @pytest.mark.asyncio
    async def test_complete_registration_flow_success(self, test_user_for_flows, authenticated_client, db_session):
        """Test successful complete passkey registration flow."""
        
        # Step 1: Begin registration
        response = authenticated_client.post(
            "/api/v1/passkey/register/begin",
            json={"username": test_user_for_flows.username}
        )
        
        assert response.status_code == 200
        registration_options = response.json()
        
        # Verify registration options structure
        assert "challenge" in registration_options
        assert "rp" in registration_options
        assert "user" in registration_options
        assert "pubKeyCredParams" in registration_options
        assert registration_options["rp"]["id"] == "localhost"
        assert registration_options["user"]["name"] == test_user_for_flows.username
        
        # Step 2: Mock successful registration response verification
        mock_challenge = registration_options["challenge"]
        
        with patch.object(webauthn_service, 'verify_registration_response') as mock_verify:
            mock_verify.return_value = (True, {
                'credential_id': 'test_credential_id_123',
                'public_key': b'mock_public_key_data',
                'sign_count': 0,
                'aaguid': 'mock_aaguid'
            })
            
            # Complete registration
            registration_response = MOCK_REGISTRATION_RESPONSE.copy()
            response = authenticated_client.post(
                "/api/v1/passkey/register/complete",
                json=registration_response
            )
            
            assert response.status_code == 200
            credential_data = response.json()
            
            # Verify credential was created
            assert credential_data["credential_id"] == "test_credential_id_123"
            assert credential_data["name"] == "Test Device"
            assert credential_data["sign_count"] == 0
            assert credential_data["is_active"] is True
            
            # Verify mock was called with correct parameters
            mock_verify.assert_called_once_with(
                user_id=test_user_for_flows.id,
                response=registration_response
            )
    
    @pytest.mark.asyncio
    async def test_registration_flow_verification_failure(self, test_user_for_flows, authenticated_client):
        """Test registration flow with verification failure."""
        
        # Begin registration
        response = authenticated_client.post(
            "/api/v1/passkey/register/begin",
            json={"username": test_user_for_flows.username}
        )
        assert response.status_code == 200
        
        # Mock failed verification
        with patch.object(webauthn_service, 'verify_registration_response') as mock_verify:
            mock_verify.return_value = (False, {'error': 'Challenge mismatch'})
            
            response = authenticated_client.post(
                "/api/v1/passkey/register/complete",
                json=MOCK_REGISTRATION_RESPONSE
            )
            
            assert response.status_code == 400
            assert "Registration verification failed" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_registration_begin_without_authentication(self, test_user_for_flows, db_session):
        """Test that registration completion requires authentication."""
        def get_test_db():
            return db_session
        
        app.dependency_overrides[get_db_session] = get_test_db
        
        try:
            client = TestClient(app)
            
            response = client.post(
                "/api/v1/passkey/register/complete",
                json=MOCK_REGISTRATION_RESPONSE
            )
            
            assert response.status_code in [401, 403]  # Could be 401 or 403 depending on auth middleware
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio  
    async def test_registration_with_existing_credentials(self, test_user_for_flows, authenticated_client, db_session):
        """Test registration when user already has credentials."""
        
        # Create existing credential
        passkey_repo = PasskeyCredentialRepository(db_session)
        from app.auth.passkey_models import PasskeyCredentialCreate
        
        existing_cred = PasskeyCredentialCreate(
            credential_id="existing_credential",
            public_key=b"existing_public_key",
            sign_count=0,
            name="Existing Passkey"
        )
        await passkey_repo.create(test_user_for_flows.id, existing_cred)
        
        # Begin registration - should exclude existing credential
        response = authenticated_client.post(
            "/api/v1/passkey/register/begin", 
            json={"username": test_user_for_flows.username}
        )
        
        assert response.status_code == 200
        registration_options = response.json()
        
        # Should have excludeCredentials with existing credential
        assert "excludeCredentials" in registration_options
        exclude_creds = registration_options["excludeCredentials"]
        assert len(exclude_creds) == 1
        assert exclude_creds[0]["id"] == "existing_credential"


class TestPasskeyAuthenticationFlow:
    """Test complete passkey authentication flow."""
    
    @pytest_asyncio.fixture
    async def user_with_passkey(self, test_user_for_flows, db_session):
        """Create user with existing passkey credential."""
        passkey_repo = PasskeyCredentialRepository(db_session)
        from app.auth.passkey_models import PasskeyCredentialCreate
        
        credential_data = PasskeyCredentialCreate(
            credential_id="auth_test_credential",
            public_key=b"mock_public_key_for_auth",
            sign_count=5,
            name="Auth Test Passkey"
        )
        
        credential = await passkey_repo.create(test_user_for_flows.id, credential_data)
        return test_user_for_flows, credential
    
    @pytest.mark.asyncio
    async def test_complete_authentication_flow_success(self, user_with_passkey, db_session):
        """Test successful complete passkey authentication flow."""
        user, credential = user_with_passkey
        
        def get_test_db():
            return db_session
        
        app.dependency_overrides[get_db_session] = get_test_db
        
        try:
            client = TestClient(app)
            
            # Step 1: Begin authentication
            response = client.post(
                "/api/v1/passkey/authenticate/begin",
                json={"username": user.username}
            )
            
            assert response.status_code == 200
            auth_options = response.json()
            
            # Verify authentication options structure
            assert "challenge" in auth_options
            assert "allowCredentials" in auth_options
            assert "rpId" in auth_options
            assert auth_options["rpId"] == "localhost"
            
            # Should include user's credential
            allow_creds = auth_options["allowCredentials"]
            assert len(allow_creds) == 1
            assert allow_creds[0]["id"] == "auth_test_credential"
            
            # Step 2: Mock successful authentication response verification
            with patch.object(webauthn_service, 'verify_authentication_response') as mock_verify:
                mock_verify.return_value = (True, {'sign_count': 6})
                
                auth_response = MOCK_AUTHENTICATION_RESPONSE.copy()
                auth_response["id"] = "auth_test_credential"
                
                response = client.post(
                    "/api/v1/passkey/authenticate/complete",
                    json=auth_response
                )
                
                assert response.status_code == 200
                token_data = response.json()
                
                # Verify token response
                assert "access_token" in token_data
                assert token_data["token_type"] == "bearer"
                assert "expires_in" in token_data
                assert "user" in token_data
                
                # Verify user data in response
                user_data = token_data["user"]
                assert user_data["id"] == user.id
                assert user_data["username"] == user.username
                assert user_data["email"] == user.email
                
                # Verify sign count was updated
                passkey_repo = PasskeyCredentialRepository(db_session)
                updated_credential = await passkey_repo.get_by_credential_id("auth_test_credential")
                assert updated_credential.sign_count == 6
                assert updated_credential.last_used is not None
                
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_authentication_flow_verification_failure(self, user_with_passkey, db_session):
        """Test authentication flow with verification failure."""
        user, credential = user_with_passkey
        
        def get_test_db():
            return db_session
        
        app.dependency_overrides[get_db_session] = get_test_db
        
        try:
            client = TestClient(app)
            
            # Begin authentication
            response = client.post(
                "/api/v1/passkey/authenticate/begin",
                json={"username": user.username}
            )
            assert response.status_code == 200
            
            # Mock failed verification
            with patch.object(webauthn_service, 'verify_authentication_response') as mock_verify:
                mock_verify.return_value = (False, {'error': 'Signature verification failed'})
                
                auth_response = MOCK_AUTHENTICATION_RESPONSE.copy()
                auth_response["id"] = "auth_test_credential"
                
                response = client.post(
                    "/api/v1/passkey/authenticate/complete",
                    json=auth_response
                )
                
                assert response.status_code == 401
                assert "Authentication failed" in response.json()["detail"]
                
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_usernameless_authentication_flow(self, user_with_passkey, db_session):
        """Test usernameless authentication flow."""
        user, credential = user_with_passkey
        
        def get_test_db():
            return db_session
        
        app.dependency_overrides[get_db_session] = get_test_db
        
        try:
            client = TestClient(app)
            
            # Begin usernameless authentication (empty JSON)
            response = client.post(
                "/api/v1/passkey/authenticate/begin",
                json={}
            )
            
            assert response.status_code == 200
            auth_options = response.json()
            
            # Should have empty allowCredentials for usernameless flow
            assert "challenge" in auth_options
            assert "allowCredentials" in auth_options
            assert auth_options["allowCredentials"] == []
            assert auth_options["rpId"] == "localhost"
            
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_authentication_with_inactive_user(self, user_with_passkey, db_session):
        """Test authentication with inactive user account."""
        user, credential = user_with_passkey
        
        # Deactivate user
        user_repo = UserRepository(db_session)
        user.is_active = False
        await db_session.commit()
        
        def get_test_db():
            return db_session
        
        app.dependency_overrides[get_db_session] = get_test_db
        
        try:
            client = TestClient(app)
            
            # Try to begin authentication with inactive user
            response = client.post(
                "/api/v1/passkey/authenticate/begin",
                json={"username": user.username}
            )
            
            assert response.status_code == 400
            assert "User account is inactive" in response.json()["detail"]
            
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_authentication_with_nonexistent_credential(self, db_session):
        """Test authentication with credential that doesn't exist."""
        def get_test_db():
            return db_session
        
        app.dependency_overrides[get_db_session] = get_test_db
        
        try:
            client = TestClient(app)
            
            auth_response = MOCK_AUTHENTICATION_RESPONSE.copy()
            auth_response["id"] = "nonexistent_credential"
            
            response = client.post(
                "/api/v1/passkey/authenticate/complete",
                json=auth_response
            )
            
            assert response.status_code == 404
            assert "Credential not found" in response.json()["detail"]
            
        finally:
            app.dependency_overrides.clear()


class TestPasskeyCredentialManagement:
    """Test passkey credential management endpoints."""
    
    @pytest_asyncio.fixture
    async def user_with_multiple_passkeys(self, test_user_for_flows, db_session):
        """Create user with multiple passkey credentials."""
        passkey_repo = PasskeyCredentialRepository(db_session)
        from app.auth.passkey_models import PasskeyCredentialCreate
        
        cred1_data = PasskeyCredentialCreate(
            credential_id="multi_cred_1",
            public_key=b"public_key_1",
            sign_count=10,
            name="iPhone Passkey"
        )
        cred2_data = PasskeyCredentialCreate(
            credential_id="multi_cred_2", 
            public_key=b"public_key_2",
            sign_count=5,
            name="MacBook Passkey"
        )
        
        cred1 = await passkey_repo.create(test_user_for_flows.id, cred1_data)
        cred2 = await passkey_repo.create(test_user_for_flows.id, cred2_data)
        
        return test_user_for_flows, [cred1, cred2]
    
    @pytest.mark.asyncio
    async def test_list_user_passkeys(self, user_with_multiple_passkeys, authenticated_client):
        """Test listing user's passkey credentials."""
        user, credentials = user_with_multiple_passkeys
        
        response = authenticated_client.get("/api/v1/passkey/credentials")
        
        assert response.status_code == 200
        creds_data = response.json()
        
        assert len(creds_data) == 2
        
        # Verify credential data (ordered by created_at desc)
        assert creds_data[0]["credential_id"] in ["multi_cred_1", "multi_cred_2"]
        assert creds_data[1]["credential_id"] in ["multi_cred_1", "multi_cred_2"]
        
        # Check all expected fields are present
        for cred in creds_data:
            assert "id" in cred
            assert "credential_id" in cred
            assert "name" in cred
            assert "sign_count" in cred
            assert "created_at" in cred
            assert "is_active" in cred
            assert cred["is_active"] is True
    
    @pytest.mark.asyncio
    async def test_delete_passkey_credential(self, user_with_multiple_passkeys, authenticated_client, db_session):
        """Test deleting a passkey credential."""
        user, credentials = user_with_multiple_passkeys
        
        # Delete first credential
        cred_to_delete = credentials[0]
        response = authenticated_client.delete(f"/api/v1/passkey/credentials/{cred_to_delete.credential_id}")
        
        assert response.status_code == 200
        assert "Credential deleted successfully" in response.json()["message"]
        
        # Verify credential was deleted
        passkey_repo = PasskeyCredentialRepository(db_session)
        deleted_cred = await passkey_repo.get_by_credential_id(cred_to_delete.credential_id)
        assert deleted_cred is None
        
        # Verify other credential still exists
        remaining_cred = await passkey_repo.get_by_credential_id(credentials[1].credential_id)
        assert remaining_cred is not None
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_passkey(self, test_user_for_flows, authenticated_client):
        """Test deleting non-existent passkey credential."""
        response = authenticated_client.delete("/api/v1/passkey/credentials/nonexistent_credential")
        
        assert response.status_code == 404
        assert "Credential not found or not owned by user" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_delete_passkey_without_authentication(self, user_with_multiple_passkeys, db_session):
        """Test that deleting passkey requires authentication."""
        user, credentials = user_with_multiple_passkeys
        
        def get_test_db():
            return db_session
        
        app.dependency_overrides[get_db_session] = get_test_db
        
        try:
            client = TestClient(app)
            
            response = client.delete(f"/api/v1/passkey/credentials/{credentials[0].credential_id}")
            
            assert response.status_code in [401, 403]  # Could be 401 or 403 depending on auth middleware
            
        finally:
            app.dependency_overrides.clear()


class TestPasskeySecurityValidation:
    """Test security-related validation for passkey operations."""
    
    @pytest.mark.asyncio
    async def test_challenge_reuse_prevention(self, test_user_for_flows, db_session):
        """Test that challenges cannot be reused."""
        passkey_repo = PasskeyCredentialRepository(db_session)
        from app.auth.passkey_models import PasskeyCredentialCreate
        
        # Create credential for authentication test
        cred_data = PasskeyCredentialCreate(
            credential_id="security_test_cred",
            public_key=b"security_public_key", 
            sign_count=0,
            name="Security Test Passkey"
        )
        await passkey_repo.create(test_user_for_flows.id, cred_data)
        
        def get_test_db():
            return db_session
        
        app.dependency_overrides[get_db_session] = get_test_db
        
        try:
            client = TestClient(app)
            
            # Begin authentication to get challenge
            response = client.post(
                "/api/v1/passkey/authenticate/begin",
                json={"username": test_user_for_flows.username}
            )
            assert response.status_code == 200
            
            # Try to use the same challenge twice
            with patch.object(webauthn_service, 'verify_authentication_response') as mock_verify:
                # First attempt - challenge should be valid
                mock_verify.return_value = (True, {'sign_count': 1})
                
                auth_response = MOCK_AUTHENTICATION_RESPONSE.copy()
                auth_response["id"] = "security_test_cred"
                
                response1 = client.post(
                    "/api/v1/passkey/authenticate/complete",
                    json=auth_response
                )
                assert response1.status_code == 200
                
                # Second attempt with same response - should fail due to challenge being cleared
                response2 = client.post(
                    "/api/v1/passkey/authenticate/complete", 
                    json=auth_response
                )
                assert response2.status_code == 400
                assert "No challenge found" in response2.json()["detail"]
                
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_sign_count_validation(self, test_user_for_flows, db_session):
        """Test that sign count is properly validated and updated."""
        passkey_repo = PasskeyCredentialRepository(db_session)
        from app.auth.passkey_models import PasskeyCredentialCreate
        
        # Create credential with initial sign count
        cred_data = PasskeyCredentialCreate(
            credential_id="sign_count_test_cred",
            public_key=b"sign_count_public_key",
            sign_count=10,  # Start with sign count of 10
            name="Sign Count Test Passkey"
        )
        await passkey_repo.create(test_user_for_flows.id, cred_data)
        
        def get_test_db():
            return db_session
        
        app.dependency_overrides[get_db_session] = get_test_db
        
        try:
            client = TestClient(app)
            
            # Begin authentication
            response = client.post(
                "/api/v1/passkey/authenticate/begin",
                json={"username": test_user_for_flows.username}
            )
            assert response.status_code == 200
            
            # Successful authentication with higher sign count
            with patch.object(webauthn_service, 'verify_authentication_response') as mock_verify:
                mock_verify.return_value = (True, {'sign_count': 15})  # Higher than stored value
                
                auth_response = MOCK_AUTHENTICATION_RESPONSE.copy()
                auth_response["id"] = "sign_count_test_cred"
                
                response = client.post(
                    "/api/v1/passkey/authenticate/complete",
                    json=auth_response
                )
                
                assert response.status_code == 200
                
                # Verify sign count was updated
                updated_cred = await passkey_repo.get_by_credential_id("sign_count_test_cred")
                assert updated_cred.sign_count == 15
                
        finally:
            app.dependency_overrides.clear()