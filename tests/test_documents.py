"""
IOSP - Document Tests
Comprehensive tests for document upload, validation, processing, and permissions.
"""
import io
import pytest
from unittest.mock import patch, MagicMock
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status

from apps.documents.models import Document, DocumentCategory, DocumentChunk
from tests.factories import (
    UserFactory,
    DocumentFactory,
    DocumentCategoryFactory,
)


# ===========================================
# Test Fixtures
# ===========================================

@pytest.fixture
def pdf_file():
    """Create a valid PDF file for testing."""
    pdf_content = b"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >> endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
trailer << /Size 4 /Root 1 0 R >>
startxref
196
%%EOF"""
    return SimpleUploadedFile(
        name='test_document.pdf',
        content=pdf_content,
        content_type='application/pdf'
    )


@pytest.fixture
def txt_file():
    """Create a valid text file for testing."""
    return SimpleUploadedFile(
        name='test_document.txt',
        content=b'This is test content for the document.',
        content_type='text/plain'
    )


@pytest.fixture
def invalid_file():
    """Create an invalid file type for testing."""
    return SimpleUploadedFile(
        name='malware.exe',
        content=b'MZ\x90\x00\x03\x00\x00\x00',
        content_type='application/x-msdownload'
    )


@pytest.fixture
def large_file():
    """Create a file that exceeds size limit."""
    # 60MB file (exceeds 50MB limit)
    content = b'x' * (60 * 1024 * 1024)
    return SimpleUploadedFile(
        name='large_file.txt',
        content=content,
        content_type='text/plain'
    )


# ===========================================
# File Validation Tests
# ===========================================

@pytest.mark.django_db
class TestFileValidation:
    """Tests for file validation."""

    def test_validate_valid_pdf(self, pdf_file):
        """Test that valid PDF passes validation."""
        from apps.documents.validators import validate_file_upload
        is_valid, error = validate_file_upload(pdf_file)
        assert is_valid is True
        assert error is None

    def test_validate_valid_txt(self, txt_file):
        """Test that valid TXT passes validation."""
        from apps.documents.validators import validate_file_upload
        is_valid, error = validate_file_upload(txt_file)
        assert is_valid is True
        assert error is None

    def test_validate_invalid_extension(self):
        """Test that invalid extension fails validation."""
        from apps.documents.validators import validate_filename
        is_valid, error = validate_filename('malware.exe')
        assert is_valid is False
        assert 'Desteklenmeyen' in error

    def test_validate_dangerous_filename(self):
        """Test that dangerous filenames are rejected."""
        from apps.documents.validators import validate_filename

        dangerous_names = [
            '../../../etc/passwd',
            'file<script>.pdf',
            'file\x00.pdf',
            '.htaccess',
        ]

        for name in dangerous_names:
            is_valid, _ = validate_filename(name)
            assert is_valid is False, f"Should reject: {name}"

    def test_validate_file_size_limit(self, large_file):
        """Test that large files are rejected."""
        from apps.documents.validators import validate_file_size
        is_valid, error = validate_file_size(large_file)
        assert is_valid is False
        assert 'çok büyük' in error

    def test_sanitize_filename(self):
        """Test filename sanitization."""
        from apps.documents.validators import sanitize_filename

        test_cases = [
            ('Normal File.pdf', 'Normal_File.pdf'),
            ('file<>:"|?.pdf', 'file.pdf'),
            ('a' * 300 + '.pdf', 'a' * 200 + '.pdf'),
            ('   .pdf', '.pdf'),  # Empty name gets UUID
        ]

        for original, _ in test_cases:
            result = sanitize_filename(original)
            assert '..' not in result
            assert '<' not in result
            assert '>' not in result


# ===========================================
# Document Upload Tests
# ===========================================

@pytest.mark.django_db
class TestDocumentUpload:
    """Tests for document upload endpoint."""

    @patch('apps.documents.serializers.process_document')
    def test_upload_document_success(self, mock_task, analyst_client, pdf_file, category):
        """Test successful document upload."""
        mock_task.delay.return_value = MagicMock(id='test-task-id')

        url = reverse('documents:document_list')
        data = {
            'title': 'Test Document',
            'description': 'Test description',
            'file': pdf_file,
            'category_id': str(category.id),
        }
        response = analyst_client.post(url, data, format='multipart')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['title'] == 'Test Document'
        assert Document.objects.filter(title='Test Document').exists()

    def test_upload_without_authentication(self, api_client, pdf_file):
        """Test upload without authentication fails."""
        url = reverse('documents:document_list')
        data = {
            'title': 'Test Document',
            'file': pdf_file,
        }
        response = api_client.post(url, data, format='multipart')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_upload_as_viewer_fails(self, auth_client, pdf_file):
        """Test that viewer role cannot upload."""
        url = reverse('documents:document_list')
        data = {
            'title': 'Test Document',
            'file': pdf_file,
        }
        response = auth_client.post(url, data, format='multipart')

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch('apps.documents.validators.magic.from_buffer')
    def test_upload_invalid_file_type(self, mock_magic, analyst_client, invalid_file):
        """Test upload with invalid file type fails."""
        mock_magic.return_value = 'application/x-msdownload'

        url = reverse('documents:document_list')
        data = {
            'title': 'Test Document',
            'file': invalid_file,
        }
        response = analyst_client.post(url, data, format='multipart')

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ===========================================
# Document Processing Tests
# ===========================================

@pytest.mark.django_db
class TestDocumentProcessing:
    """Tests for document processing."""

    @patch('apps.documents.views.process_document')
    def test_process_document_endpoint(self, mock_task, analyst_client, document):
        """Test process document endpoint."""
        mock_task.delay.return_value = MagicMock(id='test-task-id')

        # Set document status to pending
        document.status = Document.Status.PENDING
        document.save()

        url = reverse('documents:process_document', kwargs={'pk': document.id})
        response = analyst_client.post(url)

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert 'task_id' in response.data
        mock_task.delay.assert_called_once_with(str(document.id))

    def test_process_already_completed_document(self, analyst_client, processed_document):
        """Test processing already completed document."""
        url = reverse('documents:process_document', kwargs={'pk': processed_document.id})
        response = analyst_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'zaten işlenmiş' in response.data['message']

    def test_process_document_without_permission(self, auth_client, document):
        """Test processing document without permission."""
        # Create a different user's document
        other_user = UserFactory(role='analyst')
        document.uploaded_by = other_user
        document.is_public = False
        document.save()

        url = reverse('documents:process_document', kwargs={'pk': document.id})
        response = auth_client.post(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN


# ===========================================
# Document Status Tests
# ===========================================

@pytest.mark.django_db
class TestDocumentStatus:
    """Tests for document status endpoint."""

    def test_get_document_status(self, analyst_client, document):
        """Test getting document status."""
        url = reverse('documents:document_status', kwargs={'pk': document.id})
        response = analyst_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'status' in response.data
        assert 'processing_progress' in response.data

    def test_get_status_nonexistent_document(self, analyst_client):
        """Test getting status of nonexistent document."""
        import uuid
        url = reverse('documents:document_status', kwargs={'pk': uuid.uuid4()})
        response = analyst_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_public_document_status(self, auth_client, public_document):
        """Test that any user can get public document status."""
        url = reverse('documents:document_status', kwargs={'pk': public_document.id})
        response = auth_client.get(url)

        assert response.status_code == status.HTTP_200_OK


# ===========================================
# Document Permission Tests
# ===========================================

@pytest.mark.django_db
class TestDocumentPermissions:
    """Tests for document permissions."""

    def test_viewer_can_see_own_documents(self, auth_client, user):
        """Test viewer can see their own documents."""
        doc = DocumentFactory(uploaded_by=user, is_public=False)

        url = reverse('documents:document_list')
        response = auth_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        doc_ids = [d['id'] for d in response.data['results']]
        assert str(doc.id) in doc_ids

    def test_viewer_can_see_public_documents(self, auth_client):
        """Test viewer can see public documents."""
        public_doc = DocumentFactory(is_public=True)

        url = reverse('documents:document_list')
        response = auth_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        doc_ids = [d['id'] for d in response.data['results']]
        assert str(public_doc.id) in doc_ids

    def test_viewer_cannot_see_others_private_documents(self, auth_client):
        """Test viewer cannot see other users' private documents."""
        other_user = UserFactory()
        private_doc = DocumentFactory(uploaded_by=other_user, is_public=False)

        url = reverse('documents:document_list')
        response = auth_client.get(url)

        doc_ids = [d['id'] for d in response.data['results']]
        assert str(private_doc.id) not in doc_ids

    def test_admin_can_see_all_documents(self, admin_client):
        """Test admin can see all documents."""
        private_doc = DocumentFactory(is_public=False)
        public_doc = DocumentFactory(is_public=True)

        url = reverse('documents:document_list')
        response = admin_client.get(url)

        doc_ids = [d['id'] for d in response.data['results']]
        assert str(private_doc.id) in doc_ids
        assert str(public_doc.id) in doc_ids

    def test_only_owner_or_admin_can_delete(self, auth_client, analyst_client, document):
        """Test that only owner or admin can delete documents."""
        # Non-owner viewer cannot delete
        url = reverse('documents:document_detail', kwargs={'pk': document.id})
        response = auth_client.delete(url)
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]


# ===========================================
# Celery Task Tests (Mocked)
# ===========================================

@pytest.mark.django_db
class TestCeleryTasks:
    """Tests for Celery tasks with mocking."""

    @patch('apps.documents.tasks.extract_document_text')
    @patch('apps.documents.tasks.chunk_document_text')
    @patch('apps.documents.tasks.create_document_embeddings')
    def test_process_document_task(
        self, mock_embeddings, mock_chunk, mock_extract, document
    ):
        """Test process_document task execution."""
        from apps.documents.tasks import process_document

        mock_extract.return_value = "Test document content"
        mock_chunk.return_value = [
            {'id': 'chunk-1', 'index': 0, 'content': 'Test content'}
        ]
        mock_embeddings.return_value = None

        result = process_document(str(document.id))

        assert result['status'] == 'success'
        assert result['chunk_count'] == 1

        # Verify document status updated
        document.refresh_from_db()
        assert document.status == Document.Status.COMPLETED

    def test_process_nonexistent_document(self):
        """Test processing nonexistent document."""
        from apps.documents.tasks import process_document
        import uuid

        result = process_document(str(uuid.uuid4()))

        assert result['status'] == 'error'
        assert 'not found' in result['message']

    def test_cleanup_failed_documents_task(self):
        """Test cleanup_failed_documents task."""
        from apps.documents.tasks import cleanup_failed_documents
        from datetime import timedelta
        from django.utils import timezone

        # Create old failed document
        old_doc = DocumentFactory(
            status=Document.Status.FAILED,
        )
        # Manually update created_at to be old
        Document.objects.filter(id=old_doc.id).update(
            created_at=timezone.now() - timedelta(days=40)
        )

        result = cleanup_failed_documents(days_old=30)

        assert result['deleted_count'] >= 1
        assert not Document.objects.filter(id=old_doc.id).exists()

    def test_update_document_statistics_task(self):
        """Test update_document_statistics task."""
        from apps.documents.tasks import update_document_statistics
        from django.core.cache import cache

        # Create some documents
        DocumentFactory.create_batch(3, status=Document.Status.COMPLETED)
        DocumentFactory(status=Document.Status.FAILED)

        result = update_document_statistics()

        assert result['completed_documents'] >= 3
        assert result['failed_documents'] >= 1

        # Check cache
        cached_stats = cache.get('document_statistics')
        assert cached_stats is not None


# ===========================================
# Document List Filtering Tests
# ===========================================

@pytest.mark.django_db
class TestDocumentFiltering:
    """Tests for document list filtering."""

    def test_filter_by_category(self, analyst_client, category):
        """Test filtering documents by category."""
        doc = DocumentFactory(category=category)
        other_category = DocumentCategoryFactory()
        other_doc = DocumentFactory(category=other_category)

        url = reverse('documents:document_list')
        response = analyst_client.get(url, {'category': category.slug})

        assert response.status_code == status.HTTP_200_OK
        doc_ids = [d['id'] for d in response.data['results']]
        assert str(doc.id) in doc_ids
        assert str(other_doc.id) not in doc_ids

    def test_filter_by_status(self, analyst_client):
        """Test filtering documents by status."""
        completed_doc = DocumentFactory(status=Document.Status.COMPLETED)
        pending_doc = DocumentFactory(status=Document.Status.PENDING)

        url = reverse('documents:document_list')
        response = analyst_client.get(url, {'status': 'completed'})

        assert response.status_code == status.HTTP_200_OK
        doc_ids = [d['id'] for d in response.data['results']]
        assert str(completed_doc.id) in doc_ids
        assert str(pending_doc.id) not in doc_ids
