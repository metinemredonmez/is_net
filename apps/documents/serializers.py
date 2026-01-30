"""
Documents Serializers
"""
from rest_framework import serializers
from .models import Document, DocumentCategory, DocumentChunk


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

    class Meta:
        model = Document
        fields = [
            'id', 'title', 'description', 'file', 'file_type', 'file_size',
            'category', 'category_id', 'tags', 'status', 'chunk_count',
            'is_public', 'uploaded_by_name', 'created_at', 'processed_at', 'chunks'
        ]
        read_only_fields = ['id', 'file_type', 'file_size', 'status', 'chunk_count', 'created_at', 'processed_at']
