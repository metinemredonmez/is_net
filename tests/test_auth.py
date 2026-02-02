"""
IOSP - Authentication Tests
Comprehensive tests for authentication endpoints.
"""
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from tests.factories import UserFactory


@pytest.mark.django_db
class TestUserRegistration:
    """Tests for user registration endpoint."""

    def test_register_success(self, api_client):
        """Test successful user registration."""
        url = reverse('accounts:register')
        data = {
            'email': 'newuser@example.com',
            'full_name': 'Test User',
            'phone': '+905551234567',
            'password': 'SecurePass123',
            'password_confirm': 'SecurePass123',
        }
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert 'tokens' in response.data
        assert 'access' in response.data['tokens']
        assert 'refresh' in response.data['tokens']
        assert response.data['user']['email'] == 'newuser@example.com'
        assert response.data['user']['role'] == 'viewer'

    def test_register_duplicate_email(self, api_client, user):
        """Test registration with existing email fails."""
        url = reverse('accounts:register')
        data = {
            'email': user.email,  # Existing user email
            'full_name': 'Another User',
            'password': 'SecurePass123',
            'password_confirm': 'SecurePass123',
        }
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'email' in response.data

    def test_register_weak_password(self, api_client):
        """Test registration with weak password fails."""
        url = reverse('accounts:register')
        data = {
            'email': 'newuser@example.com',
            'full_name': 'Test User',
            'password': '12345678',  # No letters
            'password_confirm': '12345678',
        }
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'password' in response.data

    def test_register_password_mismatch(self, api_client):
        """Test registration with mismatched passwords fails."""
        url = reverse('accounts:register')
        data = {
            'email': 'newuser@example.com',
            'full_name': 'Test User',
            'password': 'SecurePass123',
            'password_confirm': 'DifferentPass123',
        }
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'password_confirm' in response.data

    def test_register_missing_required_fields(self, api_client):
        """Test registration with missing fields fails."""
        url = reverse('accounts:register')
        data = {
            'email': 'newuser@example.com',
            # missing full_name, password
        }
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_invalid_email(self, api_client):
        """Test registration with invalid email fails."""
        url = reverse('accounts:register')
        data = {
            'email': 'invalid-email',
            'full_name': 'Test User',
            'password': 'SecurePass123',
            'password_confirm': 'SecurePass123',
        }
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'email' in response.data


@pytest.mark.django_db
class TestUserLogin:
    """Tests for user login endpoint."""

    def test_login_success(self, api_client, user):
        """Test successful login."""
        url = reverse('accounts:token_obtain')
        data = {
            'email': user.email,
            'password': 'testpass123',
        }
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert 'refresh' in response.data

    def test_login_wrong_password(self, api_client, user):
        """Test login with wrong password fails."""
        url = reverse('accounts:token_obtain')
        data = {
            'email': user.email,
            'password': 'wrongpassword',
        }
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_nonexistent_user(self, api_client):
        """Test login with non-existent user fails."""
        url = reverse('accounts:token_obtain')
        data = {
            'email': 'nonexistent@example.com',
            'password': 'somepassword',
        }
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_inactive_user(self, api_client):
        """Test login with inactive user fails."""
        user = UserFactory(is_active=False)
        url = reverse('accounts:token_obtain')
        data = {
            'email': user.email,
            'password': 'testpass123',
        }
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestTokenRefresh:
    """Tests for token refresh endpoint."""

    def test_token_refresh_success(self, api_client, user_tokens):
        """Test successful token refresh."""
        url = reverse('accounts:token_refresh')
        data = {
            'refresh': user_tokens['refresh'],
        }
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data

    def test_token_refresh_invalid_token(self, api_client):
        """Test token refresh with invalid token fails."""
        url = reverse('accounts:token_refresh')
        data = {
            'refresh': 'invalid-token',
        }
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestUserLogout:
    """Tests for user logout endpoints."""

    def test_logout_success(self, auth_client, user_tokens):
        """Test successful logout."""
        url = reverse('accounts:logout')
        data = {
            'refresh': user_tokens['refresh'],
        }
        response = auth_client.post(url, data)

        assert response.status_code == status.HTTP_200_OK

        # Verify token is blacklisted - refresh should fail
        refresh_url = reverse('accounts:token_refresh')
        refresh_response = auth_client.post(refresh_url, data)
        assert refresh_response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_logout_without_token(self, auth_client):
        """Test logout without refresh token fails."""
        url = reverse('accounts:logout')
        response = auth_client.post(url, {})

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_logout_unauthenticated(self, api_client):
        """Test logout without authentication fails."""
        url = reverse('accounts:logout')
        response = api_client.post(url, {'refresh': 'some-token'})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_logout_all_devices(self, auth_client, user):
        """Test logout from all devices."""
        url = reverse('accounts:logout_all')
        response = auth_client.post(url)

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestPasswordChange:
    """Tests for password change endpoint."""

    def test_password_change_success(self, auth_client):
        """Test successful password change."""
        url = reverse('accounts:password_change')
        data = {
            'old_password': 'testpass123',
            'new_password': 'NewSecurePass456',
            'new_password_confirm': 'NewSecurePass456',
        }
        response = auth_client.post(url, data)

        assert response.status_code == status.HTTP_200_OK
        assert 'tokens' in response.data

        # Verify new password works
        auth_client.user.refresh_from_db()
        assert auth_client.user.check_password('NewSecurePass456')

    def test_password_change_wrong_old_password(self, auth_client):
        """Test password change with wrong old password fails."""
        url = reverse('accounts:password_change')
        data = {
            'old_password': 'wrongpassword',
            'new_password': 'NewSecurePass456',
            'new_password_confirm': 'NewSecurePass456',
        }
        response = auth_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'old_password' in response.data

    def test_password_change_mismatch(self, auth_client):
        """Test password change with mismatched passwords fails."""
        url = reverse('accounts:password_change')
        data = {
            'old_password': 'testpass123',
            'new_password': 'NewSecurePass456',
            'new_password_confirm': 'DifferentPass789',
        }
        response = auth_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'new_password_confirm' in response.data

    def test_password_change_same_password(self, auth_client):
        """Test password change with same old and new password fails."""
        url = reverse('accounts:password_change')
        data = {
            'old_password': 'testpass123',
            'new_password': 'testpass123',
            'new_password_confirm': 'testpass123',
        }
        response = auth_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'new_password' in response.data

    def test_password_change_weak_password(self, auth_client):
        """Test password change with weak password fails."""
        url = reverse('accounts:password_change')
        data = {
            'old_password': 'testpass123',
            'new_password': 'weak',
            'new_password_confirm': 'weak',
        }
        response = auth_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_password_change_unauthenticated(self, api_client):
        """Test password change without authentication fails."""
        url = reverse('accounts:password_change')
        data = {
            'old_password': 'testpass123',
            'new_password': 'NewSecurePass456',
            'new_password_confirm': 'NewSecurePass456',
        }
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestPasswordReset:
    """Tests for password reset endpoints."""

    def test_password_reset_request_existing_email(self, api_client, user):
        """Test password reset request with existing email."""
        url = reverse('accounts:password_reset')
        data = {
            'email': user.email,
        }
        response = api_client.post(url, data)

        # Should always return 200 (security - don't reveal if email exists)
        assert response.status_code == status.HTTP_200_OK

    def test_password_reset_request_nonexistent_email(self, api_client):
        """Test password reset request with non-existent email."""
        url = reverse('accounts:password_reset')
        data = {
            'email': 'nonexistent@example.com',
        }
        response = api_client.post(url, data)

        # Should still return 200 (security - don't reveal if email exists)
        assert response.status_code == status.HTTP_200_OK

    def test_password_reset_confirm_invalid_token(self, api_client):
        """Test password reset confirm with invalid token fails."""
        url = reverse('accounts:password_reset_confirm')
        data = {
            'token': 'invalid-token',
            'new_password': 'NewSecurePass456',
            'new_password_confirm': 'NewSecurePass456',
        }
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestCurrentUser:
    """Tests for current user endpoint."""

    def test_get_current_user(self, auth_client, user):
        """Test getting current user info."""
        url = reverse('accounts:current_user')
        response = auth_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['email'] == user.email
        assert response.data['full_name'] == user.full_name

    def test_get_current_user_unauthenticated(self, api_client):
        """Test getting current user without authentication fails."""
        url = reverse('accounts:current_user')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestUserList:
    """Tests for user list endpoint."""

    def test_user_list_as_admin(self, admin_client):
        """Test user list as admin."""
        UserFactory.create_batch(3)
        url = reverse('accounts:user_list')
        response = admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data or isinstance(response.data, list)

    def test_user_list_as_regular_user(self, auth_client):
        """Test user list as regular user fails."""
        url = reverse('accounts:user_list')
        response = auth_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_user_list_unauthenticated(self, api_client):
        """Test user list without authentication fails."""
        url = reverse('accounts:user_list')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
