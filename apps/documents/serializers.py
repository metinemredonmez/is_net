"""
Documents Serializers
"""
import logging
from rest_framework import serializers
from .models import Document, DocumentCategory, DocumentChunk
from .validators import (
    validate_file_upload,
    sanitize_filename,
    get_file_type,
    FileValidator,
)

logger = logging.getLogger(__name__)


class DocumentCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentCategory
        fields = ['id', 'name', 'slug', 'description', 'icon', 'color']


class DocumentChunkSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentChunk
        fields = ['id', 'chunk_index', 'content', 'token_count', 'page_number', 'section']


class DocumentSerializer(serializers.ModelSerializer):
    category = DocumentCategorySerializer(read_only=True)
    category_id = serializers.UUIDField(write_only=True, required=False)
    chunks = DocumentChunkSerializer(many=True, read_only=True)
    uploaded_by_name = serializers.CharField(source='uploaded_by.full_name', read_only=True)
    file = serializers.FileField(validators=[FileValidator()])

    class Meta:
        model = Document
        fields = [
            'id', 'title', 'description', 'file', 'file_type', 'file_size',
            'category', 'category_id', 'tags', 'status', 'processing_progress',
            'chunk_count', 'is_public', 'uploaded_by_name', 'created_at',
            'processed_at', 'task_id', 'chunks'
        ]
        read_only_fields = [
            'id', 'file_type', 'file_size', 'status', 'processing_progress',
            'chunk_count', 'created_at', 'processed_at', 'task_id'
        ]

    def validate_file(self, value):
        """Additional file validation."""
        # File validator already called, but we can do additional checks
        is_valid, error = validate_file_upload(value)
        if not is_valid:
            raise serializers.ValidationError(error)

        # Sanitize filename
        value.name = sanitize_filename(value.name)

        return value

    def create(self, validated_data):
        """Create document and trigger async processing."""
        file = validated_data.get('file')

        # Auto-detect file type
        if file:
            file_type = get_file_type(file)
            if file_type:
                validated_data['file_type'] = file_type

        document = super().create(validated_data)

        # Trigger async processing
        try:
            from .tasks import process_document
            task = process_document.delay(str(document.id))
            document.task_id = task.id
            document.save(update_fields=['task_id'])
            logger.info(f"Document processing queued: {document.id}, task: {task.id}")
        except Exception as e:
            logger.error(f"Failed to queue document processing: {e}")
            # Don't fail the upload, just leave status as pending

        return document


class DocumentStatusSerializer(serializers.ModelSerializer):
    """Serializer for document processing status."""

    class Meta:
        model = Document
        fields = [
            'id', 'title', 'status', 'processing_progress',
            'chunk_count', 'error_message', 'task_id',
            'created_at', 'processed_at'
        ]
        read_only_fields = fields


class DocumentUploadSerializer(serializers.Serializer):
    """Simple serializer for file upload response."""
    id = serializers.UUIDField(read_only=True)
    title = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    task_id = serializers.CharField(read_only=True)
    message = serializers.CharField(read_only=True)
