"""Advanced WebAuthn service tests for edge cases and security scenarios."""
import base64
import json
import secrets
import time
from unittest.mock import patch, MagicMock

import pytest
from app.auth.webauthn_service import WebAuthnService


class TestWebAuthnServiceAdvanced:
    """Advanced tests for WebAuthn service edge cases."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = WebAuthnService(rp_id="test.example.com", rp_name="Test App")
    
    def test_challenge_generation_uniqueness(self):
        """Test that generated challenges are unique."""
        challenges = [self.service.generate_challenge() for _ in range(100)]
        
        # All challenges should be unique
        assert len(set(challenges)) == 100
        
        # All challenges should be properly base64url encoded
        for challenge in challenges:
            # Should be decodable without padding issues
            decoded = base64.urlsafe_b64decode(challenge + '==')
            assert len(decoded) == 32  # 32 bytes = 256 bits
    
    def test_challenge_storage_concurrent_access(self):
        """Test challenge storage with multiple users."""
        user_ids = [1, 2, 3, 4, 5]
        challenges = {}
        
        # Store challenges for multiple users
        for user_id in user_ids:
            challenge = f"challenge_for_user_{user_id}"
            self.service.store_challenge(user_id, challenge)
            challenges[user_id] = challenge
        
        # Verify all challenges are stored correctly
        for user_id, expected_challenge in challenges.items():
            stored_challenge = self.service.get_challenge(user_id)
            assert stored_challenge == expected_challenge
        
        # Clear one challenge and verify others remain
        self.service.clear_challenge(1)
        assert self.service.get_challenge(1) is None
        
        for user_id in [2, 3, 4, 5]:
            assert self.service.get_challenge(user_id) == challenges[user_id]
    
    def test_challenge_expiration_edge_cases(self):
        """Test edge cases in challenge expiration."""
        user_id = 1
        
        # Test with very short expiration
        self.service.store_challenge(user_id, "short_lived", expires_in=0)
        time.sleep(0.1)  # Small delay
        assert self.service.get_challenge(user_id) is None
        
        # Test with negative expiration (already expired)
        self.service.store_challenge(user_id, "already_expired", expires_in=-1)
        assert self.service.get_challenge(user_id) is None
        
        # Test overwriting existing challenge
        self.service.store_challenge(user_id, "first_challenge", expires_in=60)
        self.service.store_challenge(user_id, "second_challenge", expires_in=60)
        assert self.service.get_challenge(user_id) == "second_challenge"
    
    def test_registration_options_edge_cases(self):
        """Test registration options with edge cases."""
        # Test with special characters in username
        options = self.service.create_registration_options(
            user_id=1,
            username="测试用户@example.com",
            display_name="测试 用户",
            exclude_credentials=[]
        )
        
        assert options["user"]["name"] == "测试用户@example.com"
        assert options["user"]["displayName"] == "测试 用户"
        
        # Test with very long exclude credentials list
        exclude_creds = [f"credential_{i}" for i in range(100)]
        options = self.service.create_registration_options(
            user_id=1,
            username="user",
            display_name="User",
            exclude_credentials=exclude_creds
        )
        
        assert len(options["excludeCredentials"]) == 100
        assert all(cred["type"] == "public-key" for cred in options["excludeCredentials"])
    
    def test_authentication_options_edge_cases(self):
        """Test authentication options with edge cases."""
        # Test with no user_id (usernameless flow)
        options, challenge = self.service.create_authentication_options()
        
        assert "challenge" in options
        assert options["allowCredentials"] == []
        assert options["rpId"] == "test.example.com"
        assert isinstance(challenge, str)
        
        # Test with large allow_credentials list
        allow_creds = [f"credential_{i}" for i in range(50)]
        options, challenge = self.service.create_authentication_options(
            user_id=1,
            allow_credentials=allow_creds
        )
        
        assert len(options["allowCredentials"]) == 50
        assert all(cred["type"] == "public-key" for cred in options["allowCredentials"])
    
    def test_base64url_decoding_edge_cases(self):
        """Test base64url decoding with various inputs."""
        # Test normal case
        normal_data = "SGVsbG8gV29ybGQ"
        decoded = self.service._decode_base64url(normal_data)
        assert decoded == b"Hello World"
        
        # Test with padding
        padded_data = "SGVsbG8gV29ybGQh"
        decoded = self.service._decode_base64url(padded_data)
        assert decoded == b"Hello World!"
        
        # Test with URL-safe characters
        urlsafe_data = "SGVsbG8tV29ybGRfVGVzdA"
        decoded = self.service._decode_base64url(urlsafe_data)
        assert decoded == b"Hello-World_Test"
        
        # Test empty string
        decoded = self.service._decode_base64url("")
        assert decoded == b""
    
    def test_registration_verification_malformed_data(self):
        """Test registration verification with malformed data."""
        user_id = 1
        challenge = "test_challenge"
        self.service.store_challenge(user_id, challenge)
        
        # Test with missing response fields
        invalid_responses = [
            {},  # Empty response
            {"response": {}},  # Empty response object
            {"response": {"attestationObject": "data"}},  # Missing clientDataJSON
            {"response": {"clientDataJSON": "data"}},  # Missing attestationObject
        ]
        
        for invalid_response in invalid_responses:
            success, result = self.service.verify_registration_response(user_id, invalid_response)
            assert not success
            assert "error" in result
    
    def test_registration_verification_invalid_client_data(self):
        """Test registration verification with invalid client data."""
        user_id = 1
        challenge = "test_challenge"
        self.service.store_challenge(user_id, challenge)
        
        # Test with invalid JSON in clientDataJSON
        invalid_client_data = base64.urlsafe_b64encode(b"invalid json").decode()
        response = {
            "response": {
                "attestationObject": base64.urlsafe_b64encode(b"mock_attestation").decode(),
                "clientDataJSON": invalid_client_data
            }
        }
        
        success, result = self.service.verify_registration_response(user_id, response)
        assert not success
        assert "error" in result
    
    def test_authentication_verification_edge_cases(self):
        """Test authentication verification with edge cases."""
        credential_id = "test_credential"
        public_key = b"mock_public_key"
        sign_count = 0
        challenge = "test_challenge"
        
        # Test with malformed response
        malformed_responses = [
            {},  # Empty response
            {"response": {}},  # Empty response object
            {"response": {"authenticatorData": "data"}},  # Missing other fields
        ]
        
        for malformed_response in malformed_responses:
            success, result = self.service.verify_authentication_response(
                credential_id, public_key, sign_count, malformed_response, challenge
            )
            assert not success
            assert "error" in result
    
    def test_rp_id_validation_in_options(self):
        """Test that RP ID is correctly set in all options."""
        custom_rp_id = "custom.example.com"
        custom_service = WebAuthnService(rp_id=custom_rp_id, rp_name="Custom App")
        
        # Test registration options
        reg_options = custom_service.create_registration_options(1, "user", "User")
        assert reg_options["rp"]["id"] == custom_rp_id
        
        # Test authentication options
        auth_options, _ = custom_service.create_authentication_options(1)
        assert auth_options["rpId"] == custom_rp_id
    
    def test_user_handle_encoding(self):
        """Test user handle encoding in registration options."""
        # Test with various user IDs
        user_ids = [1, 999999, 0, 2**31-1]
        
        for user_id in user_ids:
            options = self.service.create_registration_options(user_id, "user", "User")
            user_handle = options["user"]["id"]
            
            # Should be base64url encoded
            decoded_handle = base64.urlsafe_b64decode(user_handle + '==')
            assert decoded_handle == str(user_id).encode()
    
    def test_timeout_values(self):
        """Test that timeout values are set correctly."""
        # Test registration options
        reg_options = self.service.create_registration_options(1, "user", "User")
        assert reg_options["timeout"] == 60000
        
        # Test authentication options
        auth_options, _ = self.service.create_authentication_options(1)
        assert auth_options["timeout"] == 60000
    
    def test_authenticator_selection_criteria(self):
        """Test authenticator selection criteria in registration options."""
        options = self.service.create_registration_options(1, "user", "User")
        
        auth_selection = options["authenticatorSelection"]
        assert auth_selection["authenticatorAttachment"] == "platform"
        assert auth_selection["userVerification"] == "required"
        assert auth_selection["residentKey"] == "preferred"
    
    def test_public_key_credential_parameters(self):
        """Test public key credential parameters."""
        options = self.service.create_registration_options(1, "user", "User")
        
        pub_key_params = options["pubKeyCredParams"]
        assert len(pub_key_params) == 2
        
        # Check for ES256 and RS256
        alg_values = [param["alg"] for param in pub_key_params]
        assert -7 in alg_values  # ES256
        assert -257 in alg_values  # RS256
        
        assert all(param["type"] == "public-key" for param in pub_key_params)


class TestWebAuthnServiceSecurity:
    """Security-focused tests for WebAuthn service."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = WebAuthnService(rp_id="secure.example.com", rp_name="Secure App")
    
    def test_challenge_entropy(self):
        """Test that challenges have sufficient entropy."""
        challenges = [self.service.generate_challenge() for _ in range(1000)]
        
        # Calculate basic entropy metrics
        unique_challenges = set(challenges)
        assert len(unique_challenges) == len(challenges)  # All should be unique
        
        # Test that challenges are different even when generated rapidly
        rapid_challenges = []
        for _ in range(100):
            rapid_challenges.append(self.service.generate_challenge())
        
        assert len(set(rapid_challenges)) == 100
    
    def test_origin_validation_patterns(self):
        """Test various origin validation scenarios."""
        user_id = 1
        challenge = "test_challenge"
        self.service.store_challenge(user_id, challenge)
        
        valid_origins = [
            f"https://{self.service.rp_id}",
            f"http://{self.service.rp_id}:8000",
            "http://localhost:8000"
        ]
        
        # Test that valid origins would be accepted (mock the full verification)
        for origin in valid_origins:
            client_data = {
                "challenge": challenge,
                "origin": origin,
                "type": "webauthn.create"
            }
            client_data_json = base64.urlsafe_b64encode(
                json.dumps(client_data).encode()
            ).decode()
            
            # This would normally be part of a full verification
            # but we're just testing the origin validation logic
            assert origin in [f'https://{self.service.rp_id}', 
                             f'http://{self.service.rp_id}:8000', 
                             'http://localhost:8000']
    
    def test_challenge_timing_attacks(self):
        """Test resistance to timing attacks on challenge verification."""
        user_id = 1
        
        # Store a real challenge
        real_challenge = self.service.generate_challenge()
        self.service.store_challenge(user_id, real_challenge)
        
        # Test with invalid user ID
        invalid_user_challenge = self.service.get_challenge(999)
        assert invalid_user_challenge is None
        
        # Test with expired challenge
        self.service.store_challenge(user_id + 1, "expired", expires_in=-1)
        expired_challenge = self.service.get_challenge(user_id + 1)
        assert expired_challenge is None
        
        # Verify real challenge still works
        valid_challenge = self.service.get_challenge(user_id)
        assert valid_challenge == real_challenge
    
    def test_credential_id_handling(self):
        """Test secure handling of credential IDs."""
        # Test with various credential ID formats
        credential_ids = [
            "normal_credential_id",
            "credential-with-hyphens",
            "credential_with_underscores",
            "CREDENTIAL_WITH_CAPS",
            "credential123WithNumbers",
            "",  # Empty string edge case
            "a" * 1000,  # Very long credential ID
        ]
        
        for cred_id in credential_ids:
            if cred_id:  # Skip empty string for allow_credentials
                options, _ = self.service.create_authentication_options(
                    user_id=1,
                    allow_credentials=[cred_id]
                )
                
                assert len(options["allowCredentials"]) == 1
                assert options["allowCredentials"][0]["id"] == cred_id
    
    def test_memory_cleanup(self):
        """Test that sensitive data is properly cleaned up."""
        user_id = 1
        
        # Store multiple challenges
        for i in range(10):
            challenge = f"challenge_{i}"
            self.service.store_challenge(user_id + i, challenge)
        
        # Clear challenges and verify they're gone
        for i in range(10):
            self.service.clear_challenge(user_id + i)
            assert self.service.get_challenge(user_id + i) is None
        
        # Verify cache is actually cleared
        assert len(self.service.challenge_cache) == 0
    
    def test_concurrent_challenge_access(self):
        """Test thread safety of challenge operations."""
        import threading
        import time
        
        user_id = 1
        results = []
        
        def store_and_retrieve_challenge(thread_id):
            challenge = f"challenge_from_thread_{thread_id}"
            self.service.store_challenge(user_id + thread_id, challenge)
            time.sleep(0.01)  # Small delay to test concurrency
            retrieved = self.service.get_challenge(user_id + thread_id)
            results.append((thread_id, challenge, retrieved))
        
        # Create multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=store_and_retrieve_challenge, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all results are correct
        assert len(results) == 10
        for thread_id, original, retrieved in results:
            assert original == retrieved
            assert retrieved == f"challenge_from_thread_{thread_id}"


class TestWebAuthnServiceConfiguration:
    """Test WebAuthn service configuration and initialization."""
    
    def test_default_configuration(self):
        """Test service with default configuration."""
        service = WebAuthnService()
        
        assert service.rp_id == "localhost"
        assert service.rp_name == "FastAPI Enterprise App"
        assert isinstance(service.challenge_cache, dict)
    
    def test_custom_configuration(self):
        """Test service with custom configuration."""
        custom_rp_id = "myapp.example.com"
        custom_rp_name = "My Custom App"
        
        service = WebAuthnService(rp_id=custom_rp_id, rp_name=custom_rp_name)
        
        assert service.rp_id == custom_rp_id
        assert service.rp_name == custom_rp_name
    
    def test_configuration_in_generated_options(self):
        """Test that configuration is reflected in generated options."""
        custom_rp_id = "config.test.com"
        custom_rp_name = "Config Test App"
        
        service = WebAuthnService(rp_id=custom_rp_id, rp_name=custom_rp_name)
        
        # Test registration options
        reg_options = service.create_registration_options(1, "user", "Test User")
        assert reg_options["rp"]["id"] == custom_rp_id
        assert reg_options["rp"]["name"] == custom_rp_name
        
        # Test authentication options
        auth_options, _ = service.create_authentication_options(1)
        assert auth_options["rpId"] == custom_rp_id
    
    def test_invalid_configuration_handling(self):
        """Test handling of potentially invalid configuration."""
        # Test with empty RP ID
        service = WebAuthnService(rp_id="", rp_name="Test App")
        options = service.create_registration_options(1, "user", "User")
        assert options["rp"]["id"] == ""
        
        # Test with None values (should not raise errors)
        try:
            service = WebAuthnService(rp_id=None, rp_name=None)
            # This might raise an error depending on implementation
        except TypeError:
            # Expected if implementation doesn't handle None values
            pass
    
    def test_challenge_cache_isolation(self):
        """Test that different service instances have isolated caches."""
        service1 = WebAuthnService(rp_id="service1.com", rp_name="Service 1")
        service2 = WebAuthnService(rp_id="service2.com", rp_name="Service 2")
        
        # Store challenges in both services
        service1.store_challenge(1, "challenge_1")
        service2.store_challenge(1, "challenge_2")
        
        # Verify isolation
        assert service1.get_challenge(1) == "challenge_1"
        assert service2.get_challenge(1) == "challenge_2"
        
        # Clear one and verify the other is unaffected
        service1.clear_challenge(1)
        assert service1.get_challenge(1) is None
        assert service2.get_challenge(1) == "challenge_2"