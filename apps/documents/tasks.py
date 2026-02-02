"""
IOSP - Document Processing Celery Tasks
Async tasks for document processing, chunking, and embedding
"""
import logging
from datetime import timedelta
from typing import Optional

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from django.utils import timezone
from django.db import transaction

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name='apps.documents.tasks.process_document',
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def process_document(self, document_id: str) -> dict:
    """
    Main document processing task.
    Extracts text, chunks content, and creates embeddings.

    Args:
        document_id: UUID of the document to process

    Returns:
        dict: Processing result with status and chunk count
    """
    from apps.documents.models import Document

    logger.info(f"Starting document processing: {document_id}")

    try:
        document = Document.objects.get(id=document_id)
    except Document.DoesNotExist:
        logger.error(f"Document not found: {document_id}")
        return {'status': 'error', 'message': 'Document not found'}

    # Update status to processing
    document.status = Document.Status.PROCESSING
    document.processing_progress = 0
    document.save(update_fields=['status', 'processing_progress'])

    try:
        # Step 1: Extract text (20% progress)
        logger.info(f"Extracting text from document: {document_id}")
        text_content = extract_document_text(document)
        _update_progress(document, 20)

        # Step 2: Chunk the content (40% progress)
        logger.info(f"Chunking document: {document_id}")
        chunks = chunk_document_text(text_content, document)
        _update_progress(document, 40)

        # Step 3: Create embeddings (80% progress)
        logger.info(f"Creating embeddings for document: {document_id}")
        create_document_embeddings(document, chunks)
        _update_progress(document, 80)

        # Step 4: Finalize (100% progress)
        with transaction.atomic():
            document.status = Document.Status.COMPLETED
            document.processing_progress = 100
            document.processed_at = timezone.now()
            document.chunk_count = len(chunks)
            document.error_message = ''
            document.save()

        logger.info(f"Document processing completed: {document_id}, chunks: {len(chunks)}")

        return {
            'status': 'success',
            'document_id': str(document_id),
            'chunk_count': len(chunks),
        }

    except Exception as e:
        logger.error(f"Document processing failed: {document_id}, error: {e}")

        # Check if we've exceeded max retries
        try:
            self.retry(exc=e)
        except MaxRetriesExceededError:
            # Mark as failed after all retries exhausted
            document.status = Document.Status.FAILED
            document.error_message = str(e)[:500]
            document.save(update_fields=['status', 'error_message'])

            return {
                'status': 'failed',
                'document_id': str(document_id),
                'error': str(e),
            }


def _update_progress(document, progress: int):
    """Helper to update document processing progress."""
    document.processing_progress = progress
    document.save(update_fields=['processing_progress'])


def extract_document_text(document) -> str:
    """
    Extract text content from document based on file type.

    Args:
        document: Document model instance

    Returns:
        str: Extracted text content
    """
    from apps.documents.models import Document

    file_path = document.file.path
    file_type = document.file_type

    if file_type == Document.FileType.PDF:
        return _extract_pdf_text(file_path)
    elif file_type == Document.FileType.DOCX:
        return _extract_docx_text(file_path)
    elif file_type == Document.FileType.TXT:
        return _extract_txt_text(file_path)
    elif file_type == Document.FileType.MD:
        return _extract_txt_text(file_path)  # MD is plain text
    else:
        raise ValueError(f"Unsupported file type: {file_type}")


def _extract_pdf_text(file_path: str) -> str:
    """Extract text from PDF file."""
    from pypdf import PdfReader

    reader = PdfReader(file_path)
    text_parts = []

    for page in reader.pages:
        text = page.extract_text()
        if text:
            text_parts.append(text)

    return '\n\n'.join(text_parts)


def _extract_docx_text(file_path: str) -> str:
    """Extract text from DOCX file."""
    from docx import Document as DocxDocument

    doc = DocxDocument(file_path)
    text_parts = []

    for paragraph in doc.paragraphs:
        if paragraph.text.strip():
            text_parts.append(paragraph.text)

    return '\n\n'.join(text_parts)


def _extract_txt_text(file_path: str) -> str:
    """Extract text from TXT/MD file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def chunk_document_text(text: str, document, chunk_size: int = 1000, overlap: int = 200) -> list:
    """
    Split document text into overlapping chunks.

    Args:
        text: Full document text
        document: Document model instance
        chunk_size: Maximum chunk size in characters
        overlap: Overlap between chunks

    Returns:
        list: List of chunk dictionaries
    """
    from apps.documents.models import DocumentChunk

    # Clean existing chunks
    DocumentChunk.objects.filter(document=document).delete()

    chunks = []
    start = 0
    chunk_index = 0

    while start < len(text):
        # Find end position
        end = start + chunk_size

        # Try to break at a sentence boundary
        if end < len(text):
            # Look for sentence endings
            for sep in ['. ', '.\n', '? ', '?\n', '! ', '!\n']:
                last_sep = text[start:end].rfind(sep)
                if last_sep > chunk_size // 2:
                    end = start + last_sep + len(sep)
                    break

        chunk_text = text[start:end].strip()

        if chunk_text:
            chunk = DocumentChunk.objects.create(
                document=document,
                chunk_index=chunk_index,
                content=chunk_text,
                token_count=len(chunk_text.split()),  # Rough token estimate
            )
            chunks.append({
                'id': str(chunk.id),
                'index': chunk_index,
                'content': chunk_text,
            })
            chunk_index += 1

        # Move start position with overlap
        start = end - overlap if end < len(text) else len(text)

    return chunks


def create_document_embeddings(document, chunks: list):
    """
    Create vector embeddings for document chunks.

    Args:
        document: Document model instance
        chunks: List of chunk dictionaries
    """
    from django.conf import settings
    from apps.documents.models import DocumentChunk

    # This is a placeholder for actual embedding creation
    # In production, this would call the RAG service

    try:
        from apps.rag.services import RAGService
        rag_service = RAGService()

        for chunk_data in chunks:
            chunk = DocumentChunk.objects.get(id=chunk_data['id'])

            # Create embedding and store in vector DB
            vector_id = rag_service.add_document_chunk(
                chunk_id=str(chunk.id),
                content=chunk.content,
                metadata={
                    'document_id': str(document.id),
                    'document_title': document.title,
                    'chunk_index': chunk.chunk_index,
                }
            )

            # Update chunk with vector ID
            chunk.vector_id = vector_id
            chunk.save(update_fields=['vector_id'])

    except ImportError:
        logger.warning("RAG service not available, skipping embedding creation")
    except Exception as e:
        logger.error(f"Error creating embeddings: {e}")
        # Don't fail the whole process for embedding errors
        pass


@shared_task(name='apps.documents.tasks.cleanup_failed_documents')
def cleanup_failed_documents(days_old: int = 30):
    """
    Clean up old failed documents.
    Runs daily via Celery Beat.

    Args:
        days_old: Delete failed documents older than this many days
    """
    from apps.documents.models import Document

    cutoff_date = timezone.now() - timedelta(days=days_old)

    deleted_count, _ = Document.objects.filter(
        status=Document.Status.FAILED,
        created_at__lt=cutoff_date
    ).delete()

    logger.info(f"Cleaned up {deleted_count} failed documents older than {days_old} days")

    return {'deleted_count': deleted_count}


@shared_task(name='apps.documents.tasks.update_document_statistics')
def update_document_statistics():
    """
    Update document statistics cache.
    Runs hourly via Celery Beat.
    """
    from django.core.cache import cache
    from apps.documents.models import Document

    stats = {
        'total_documents': Document.objects.count(),
        'pending_documents': Document.objects.filter(status=Document.Status.PENDING).count(),
        'processing_documents': Document.objects.filter(status=Document.Status.PROCESSING).count(),
        'completed_documents': Document.objects.filter(status=Document.Status.COMPLETED).count(),
        'failed_documents': Document.objects.filter(status=Document.Status.FAILED).count(),
        'updated_at': timezone.now().isoformat(),
    }

    cache.set('document_statistics', stats, timeout=7200)  # 2 hours

    logger.info(f"Updated document statistics: {stats}")

    return stats


@shared_task(
    bind=True,
    name='apps.documents.tasks.reprocess_document',
    max_retries=1,
)
def reprocess_document(self, document_id: str) -> dict:
    """
    Reprocess a failed document.

    Args:
        document_id: UUID of the document to reprocess

    Returns:
        dict: Reprocessing result
    """
    from apps.documents.models import Document

    try:
        document = Document.objects.get(id=document_id)

        if document.status not in [Document.Status.FAILED, Document.Status.PENDING]:
            return {
                'status': 'skipped',
                'message': f'Document is {document.status}, not eligible for reprocessing'
            }

        # Reset status and trigger processing
        document.status = Document.Status.PENDING
        document.error_message = ''
        document.processing_progress = 0
        document.save()

        # Trigger processing
        process_document.delay(document_id)

        return {
            'status': 'queued',
            'document_id': str(document_id),
        }

    except Document.DoesNotExist:
        return {'status': 'error', 'message': 'Document not found'}
