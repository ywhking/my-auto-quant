"""Unit tests for qmt_proxy auth module."""

from unittest.mock import patch

import pytest

from qmt_proxy.auth import (
    authenticate_user,
    clear_all_tokens,
    get_active_token_count,
    load_user_credentials,
    revoke_token,
    validate_token,
)
from qmt_proxy.exceptions import AuthenticationError, InvalidTokenError


class TestLoadUserCredentials:
    """Test cases for load_user_credentials function."""

    def test_load_valid_credentials(self) -> None:
        """Test loading valid user credentials."""
        config = load_user_credentials()
        assert config is not None
        assert len(config.users) == 2
        assert config.users[0].name == "initiator"
        assert config.users[1].name == "executor"

    @patch("qmt_proxy.auth.USERS_CONFIG_PATH")
    def test_load_credentials_file_not_found(self, mock_path) -> None:
        """Test loading credentials when file doesn't exist."""
        mock_path.exists.return_value = False
        with pytest.raises(AuthenticationError) as exc_info:
            load_user_credentials()
        assert "User config file not found" in str(exc_info.value)

    @patch("qmt_proxy.auth.USERS_CONFIG_PATH")
    def test_load_credentials_invalid_json(self, mock_path) -> None:
        """Test loading credentials with invalid JSON."""
        mock_path.exists.return_value = True
        mock_path.open.side_effect = Exception("JSON decode error")
        with pytest.raises(AuthenticationError) as exc_info:
            load_user_credentials()
        assert "Failed to load user config" in str(exc_info.value)


class TestAuthenticateUser:
    """Test cases for authenticate_user function."""

    def test_authenticate_valid_user_initiator(self) -> None:
        """Test authenticating valid initiator user."""
        token = authenticate_user("initiator", "xxxxxxx")
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_authenticate_valid_user_executor(self) -> None:
        """Test authenticating valid executor user."""
        token = authenticate_user("executor", "xxxxxxx")
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_authenticate_invalid_username(self) -> None:
        """Test authenticating with invalid username."""
        with pytest.raises(AuthenticationError) as exc_info:
            authenticate_user("invalid_user", "xxxxxxx")
        assert "Invalid credentials" in str(exc_info.value)

    def test_authenticate_invalid_password(self) -> None:
        """Test authenticating with invalid password."""
        with pytest.raises(AuthenticationError) as exc_info:
            authenticate_user("initiator", "wrong_password")
        assert "Invalid credentials" in str(exc_info.value)

    def test_authenticate_empty_credentials(self) -> None:
        """Test authenticating with empty credentials."""
        with pytest.raises(AuthenticationError) as exc_info:
            authenticate_user("", "")
        assert "Invalid credentials" in str(exc_info.value)

    def test_authenticate_returns_unique_tokens(self) -> None:
        """Test that each authentication returns a unique token."""
        token1 = authenticate_user("initiator", "xxxxxxx")
        token2 = authenticate_user("executor", "xxxxxxx")
        assert token1 != token2


class TestValidateToken:
    """Test cases for validate_token function."""

    def test_validate_valid_token(self) -> None:
        """Test validating a valid token."""
        token = authenticate_user("initiator", "xxxxxxx")
        username, role = validate_token(token)
        assert username == "initiator"
        assert role == "initiator"

    def test_validate_executor_token(self) -> None:
        """Test validating an executor token."""
        token = authenticate_user("executor", "xxxxxxx")
        username, role = validate_token(token)
        assert username == "executor"
        assert role == "executor"

    def test_validate_invalid_token(self) -> None:
        """Test validating an invalid token."""
        with pytest.raises(InvalidTokenError) as exc_info:
            validate_token("invalid-token-12345")
        assert "Invalid or expired token" in str(exc_info.value)

    def test_validate_empty_token(self) -> None:
        """Test validating an empty token."""
        with pytest.raises(InvalidTokenError) as exc_info:
            validate_token("")
        assert "Token cannot be empty" in str(exc_info.value)

    def test_validate_revoked_token(self) -> None:
        """Test validating a token that has been revoked."""
        token = authenticate_user("initiator", "xxxxxxx")
        revoke_token(token)
        with pytest.raises(InvalidTokenError) as exc_info:
            validate_token(token)
        assert "Invalid or expired token" in str(exc_info.value)


class TestRevokeToken:
    """Test cases for revoke_token function."""

    def test_revoke_valid_token(self) -> None:
        """Test revoking a valid token."""
        token = authenticate_user("initiator", "xxxxxxx")
        revoke_token(token)
        with pytest.raises(InvalidTokenError):
            validate_token(token)

    def test_revoke_non_existent_token(self) -> None:
        """Test revoking a token that doesn't exist (should not raise)."""
        revoke_token("non-existent-token")  # Should not raise

    def test_revoke_token_twice(self) -> None:
        """Test revoking the same token twice."""
        token = authenticate_user("initiator", "xxxxxxx")
        revoke_token(token)
        revoke_token(token)  # Should not raise


class TestClearAllTokens:
    """Test cases for clear_all_tokens function."""

    def test_clear_all_tokens(self) -> None:
        """Test clearing all tokens."""
        # Create multiple tokens
        token1 = authenticate_user("initiator", "xxxxxxx")
        token2 = authenticate_user("executor", "xxxxxxx")

        assert get_active_token_count() >= 2

        # Clear all tokens
        clear_all_tokens()

        # All tokens should now be invalid
        with pytest.raises(InvalidTokenError):
            validate_token(token1)
        with pytest.raises(InvalidTokenError):
            validate_token(token2)

        assert get_active_token_count() == 0

    def test_clear_empty_tokens(self) -> None:
        """Test clearing tokens when none exist."""
        clear_all_tokens()
        assert get_active_token_count() == 0
        # Should not raise
        clear_all_tokens()


class TestGetActiveTokenCount:
    """Test cases for get_active_token_count function."""

    def test_get_active_token_count_empty(self) -> None:
        """Test getting token count when none exist."""
        clear_all_tokens()
        count = get_active_token_count()
        assert count == 0

    def test_get_active_token_count_multiple(self) -> None:
        """Test getting token count with multiple tokens."""
        clear_all_tokens()
        authenticate_user("initiator", "xxxxxxx")
        authenticate_user("executor", "xxxxxxx")
        count = get_active_token_count()
        assert count >= 2

    def test_get_active_token_count_after_revoke(self) -> None:
        """Test getting token count after revoking a token."""
        clear_all_tokens()
        token1 = authenticate_user("initiator", "xxxxxxx")
        token2 = authenticate_user("executor", "xxxxxxx")
        assert get_active_token_count() == 2
        revoke_token(token1)
        assert get_active_token_count() == 1
