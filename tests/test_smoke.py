"""
IOSP - Smoke Tests
Basic tests to verify the test infrastructure is working.
"""
import pytest
from django.conf import settings


class TestSmokeTests:
    """Basic smoke tests to verify pytest setup."""

    def test_django_settings_loaded(self):
        """Verify Django settings are loaded correctly."""
        assert settings.configured
        assert settings.ROOT_URLCONF == 'iosp.urls'

    def test_installed_apps(self):
        """Verify required apps are installed."""
        required_apps = [
            'apps.core',
            'apps.accounts',
            'apps.documents',
            'apps.rag',
            'apps.chat',
        ]
        for app in required_apps:
            assert app in settings.INSTALLED_APPS, f"{app} not in INSTALLED_APPS"

    def test_rest_framework_configured(self):
        """Verify REST framework is configured."""
        assert 'rest_framework' in settings.INSTALLED_APPS
        assert 'DEFAULT_AUTHENTICATION_CLASSES' in settings.REST_FRAMEWORK
        assert 'DEFAULT_THROTTLE_CLASSES' in settings.REST_FRAMEWORK

    def test_security_settings(self):
        """Verify security settings are configured."""
        assert settings.X_FRAME_OPTIONS == 'DENY'
        assert settings.SECURE_BROWSER_XSS_FILTER is True
        assert settings.SECURE_CONTENT_TYPE_NOSNIFF is True

    def test_custom_user_model(self):
        """Verify custom user model is set."""
        assert settings.AUTH_USER_MODEL == 'accounts.User'


@pytest.mark.django_db
class TestDatabaseConnection:
    """Tests to verify database connectivity."""

    def test_database_connection(self):
        """Verify database is accessible."""
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result[0] == 1

    def test_user_model_exists(self):
        """Verify User model is accessible."""
        from apps.accounts.models import User
        # Should not raise an exception
        assert User._meta.db_table == 'accounts_user'


@pytest.mark.django_db
class TestFactories:
    """Tests to verify factory_boy factories work."""

    def test_department_factory(self):
        """Test DepartmentFactory creates valid department."""
        from tests.factories import DepartmentFactory
        dept = DepartmentFactory()
        assert dept.pk is not None
        assert dept.name
        assert dept.code

    def test_user_factory(self):
        """Test UserFactory creates valid user."""
        from tests.factories import UserFactory
        user = UserFactory()
        assert user.pk is not None
        assert user.email
        assert user.check_password('testpass123')

    def test_user_factory_with_custom_role(self):
        """Test UserFactory with custom role."""
        from tests.factories import UserFactory
        admin = UserFactory(role='admin', is_staff=True)
        assert admin.role == 'admin'
        assert admin.is_staff is True

    def test_document_category_factory(self):
        """Test DocumentCategoryFactory creates valid category."""
        from tests.factories import DocumentCategoryFactory
        category = DocumentCategoryFactory()
        assert category.pk is not None
        assert category.name
        assert category.slug

    def test_document_factory(self):
        """Test DocumentFactory creates valid document."""
        from tests.factories import DocumentFactory
        doc = DocumentFactory()
        assert doc.pk is not None
        assert doc.title
        assert doc.uploaded_by is not None
        assert doc.category is not None

    def test_conversation_factory(self):
        """Test ConversationFactory creates valid conversation."""
        from tests.factories import ConversationFactory
        conv = ConversationFactory()
        assert conv.pk is not None
        assert conv.user is not None
        assert conv.title

    def test_message_factory(self):
        """Test MessageFactory creates valid message."""
        from tests.factories import MessageFactory
        msg = MessageFactory()
        assert msg.pk is not None
        assert msg.conversation is not None
        assert msg.content
