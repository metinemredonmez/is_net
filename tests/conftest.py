"""
IOSP - Pytest Configuration and Fixtures
"""
import pytest
from django.conf import settings
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from tests.factories import (
    UserFactory,
    DepartmentFactory,
    DocumentFactory,
    DocumentCategoryFactory,
    ConversationFactory,
    MessageFactory,
)


# ===========================================
# Database Fixtures
# ===========================================

@pytest.fixture(scope='session')
def django_db_setup():
    """Configure test database."""
    settings.DATABASES['default'] = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'iosp_test_db',
        'USER': settings.DATABASES['default']['USER'],
        'PASSWORD': settings.DATABASES['default']['PASSWORD'],
        'HOST': settings.DATABASES['default']['HOST'],
        'PORT': settings.DATABASES['default']['PORT'],
        'ATOMIC_REQUESTS': True,
    }


# ===========================================
# User Fixtures
# ===========================================

@pytest.fixture
def user(db):
    """Create a regular user."""
    return UserFactory(role='viewer')


@pytest.fixture
def analyst_user(db):
    """Create an analyst user (can upload documents)."""
    return UserFactory(role='analyst')


@pytest.fixture
def manager_user(db):
    """Create a manager user."""
    return UserFactory(role='manager')


@pytest.fixture
def admin_user(db):
    """Create an admin user."""
    return UserFactory(role='admin', is_staff=True)


@pytest.fixture
def superuser(db):
    """Create a superuser."""
    return UserFactory(role='admin', is_staff=True, is_superuser=True)


# ===========================================
# API Client Fixtures
# ===========================================

@pytest.fixture
def api_client():
    """Create an unauthenticated API client."""
    return APIClient()


@pytest.fixture
def auth_client(user):
    """Create an authenticated API client with regular user."""
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    client.user = user
    return client


@pytest.fixture
def analyst_client(analyst_user):
    """Create an authenticated API client with analyst user."""
    client = APIClient()
    refresh = RefreshToken.for_user(analyst_user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    client.user = analyst_user
    return client


@pytest.fixture
def manager_client(manager_user):
    """Create an authenticated API client with manager user."""
    client = APIClient()
    refresh = RefreshToken.for_user(manager_user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    client.user = manager_user
    return client


@pytest.fixture
def admin_client(admin_user):
    """Create an authenticated API client with admin user."""
    client = APIClient()
    refresh = RefreshToken.for_user(admin_user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    client.user = admin_user
    return client


# ===========================================
# Token Fixtures
# ===========================================

@pytest.fixture
def user_tokens(user):
    """Get JWT tokens for a user."""
    refresh = RefreshToken.for_user(user)
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
    }


# ===========================================
# Department Fixtures
# ===========================================

@pytest.fixture
def department(db):
    """Create a department."""
    return DepartmentFactory()


@pytest.fixture
def department_with_users(db):
    """Create a department with users."""
    dept = DepartmentFactory()
    UserFactory.create_batch(3, department=dept)
    return dept


# ===========================================
# Document Fixtures
# ===========================================

@pytest.fixture
def category(db):
    """Create a document category."""
    return DocumentCategoryFactory()


@pytest.fixture
def document(analyst_user, category):
    """Create a document."""
    return DocumentFactory(
        uploaded_by=analyst_user,
        category=category,
    )


@pytest.fixture
def public_document(analyst_user, category):
    """Create a public document."""
    return DocumentFactory(
        uploaded_by=analyst_user,
        category=category,
        is_public=True,
    )


@pytest.fixture
def processed_document(analyst_user, category):
    """Create a processed (completed) document."""
    return DocumentFactory(
        uploaded_by=analyst_user,
        category=category,
        status='completed',
        chunk_count=10,
    )


# ===========================================
# Chat Fixtures
# ===========================================

@pytest.fixture
def conversation(user):
    """Create a conversation."""
    return ConversationFactory(user=user)


@pytest.fixture
def conversation_with_messages(user):
    """Create a conversation with messages."""
    conv = ConversationFactory(user=user)
    MessageFactory(conversation=conv, role='user', content='Test question')
    MessageFactory(conversation=conv, role='assistant', content='Test answer')
    return conv


# ===========================================
# Utility Fixtures
# ===========================================

@pytest.fixture
def sample_pdf_file(tmp_path):
    """Create a sample PDF file for testing."""
    from io import BytesIO
    from django.core.files.uploadedfile import SimpleUploadedFile

    # Simple PDF content (minimal valid PDF)
    pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>
endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
trailer
<< /Size 4 /Root 1 0 R >>
startxref
196
%%EOF"""

    return SimpleUploadedFile(
        name='test_document.pdf',
        content=pdf_content,
        content_type='application/pdf'
    )


@pytest.fixture
def sample_txt_file():
    """Create a sample text file for testing."""
    from django.core.files.uploadedfile import SimpleUploadedFile

    return SimpleUploadedFile(
        name='test_document.txt',
        content=b'This is a test document content.',
        content_type='text/plain'
    )


# ===========================================
# Settings Fixtures
# ===========================================

@pytest.fixture
def enable_debug(settings):
    """Enable DEBUG mode for a test."""
    settings.DEBUG = True


@pytest.fixture
def disable_throttling(settings):
    """Disable throttling for a test."""
    settings.REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = []
    settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {}
