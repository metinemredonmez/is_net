"""
IOSP - Document File Validators
Security-focused file validation for document uploads
"""
import os
import re
import logging
import magic
from typing import Optional, Tuple
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)

# ===========================================
# File Type Configuration
# ===========================================

# Allowed file types with their MIME types and extensions
ALLOWED_FILE_TYPES = {
    'pdf': {
        'mime_types': ['application/pdf'],
        'extensions': ['.pdf'],
        'max_size': 50 * 1024 * 1024,  # 50MB
    },
    'docx': {
        'mime_types': [
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        ],
        'extensions': ['.docx'],
        'max_size': 50 * 1024 * 1024,  # 50MB
    },
    'txt': {
        'mime_types': ['text/plain'],
        'extensions': ['.txt'],
        'max_size': 10 * 1024 * 1024,  # 10MB
    },
    'md': {
        'mime_types': ['text/plain', 'text/markdown', 'text/x-markdown'],
        'extensions': ['.md', '.markdown'],
        'max_size': 10 * 1024 * 1024,  # 10MB
    },
}

# Default maximum file size (50MB)
MAX_FILE_SIZE = 50 * 1024 * 1024

# Dangerous patterns in filenames
DANGEROUS_FILENAME_PATTERNS = [
    r'\.\./',           # Path traversal
    r'\.\.\\',          # Path traversal (Windows)
    r'[<>:"|?*]',       # Invalid filename characters
    r'\x00',            # Null byte
    r'^\.htaccess$',    # Apache config
    r'^web\.config$',   # IIS config
    r'\.php$',          # PHP files
    r'\.asp$',          # ASP files
    r'\.aspx$',         # ASPX files
    r'\.jsp$',          # JSP files
    r'\.exe$',          # Executables
    r'\.dll$',          # DLL files
    r'\.bat$',          # Batch files
    r'\.cmd$',          # Command files
    r'\.sh$',           # Shell scripts
    r'\.ps1$',          # PowerShell scripts
]


# ===========================================
# Validation Functions
# ===========================================

def validate_file_upload(file) -> Tuple[bool, Optional[str]]:
    """
    Comprehensive file validation.

    Args:
        file: Django UploadedFile instance

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Validate filename
    is_valid, error = validate_filename(file.name)
    if not is_valid:
        return False, error

    # Validate file size
    is_valid, error = validate_file_size(file)
    if not is_valid:
        return False, error

    # Validate MIME type
    is_valid, error = validate_mime_type(file)
    if not is_valid:
        return False, error

    # Validate file extension matches content
    is_valid, error = validate_extension_matches_content(file)
    if not is_valid:
        return False, error

    return True, None


def validate_filename(filename: str) -> Tuple[bool, Optional[str]]:
    """
    Validate filename for security issues.

    Args:
        filename: Original filename

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not filename:
        return False, _('Dosya adı boş olamaz.')

    # Check for dangerous patterns
    for pattern in DANGEROUS_FILENAME_PATTERNS:
        if re.search(pattern, filename, re.IGNORECASE):
            logger.warning(f"Dangerous filename pattern detected: {filename}")
            return False, _('Geçersiz dosya adı.')

    # Check filename length
    if len(filename) > 255:
        return False, _('Dosya adı çok uzun (max 255 karakter).')

    # Check for allowed extension
    ext = os.path.splitext(filename)[1].lower()
    allowed_extensions = []
    for file_type_info in ALLOWED_FILE_TYPES.values():
        allowed_extensions.extend(file_type_info['extensions'])

    if ext not in allowed_extensions:
        return False, _(f'Desteklenmeyen dosya uzantısı. İzin verilen: {", ".join(allowed_extensions)}')

    return True, None


def validate_file_size(file, max_size: int = None) -> Tuple[bool, Optional[str]]:
    """
    Validate file size.

    Args:
        file: Django UploadedFile instance
        max_size: Maximum allowed size in bytes

    Returns:
        Tuple of (is_valid, error_message)
    """
    if max_size is None:
        max_size = MAX_FILE_SIZE

    file_size = file.size

    if file_size <= 0:
        return False, _('Dosya boş olamaz.')

    if file_size > max_size:
        max_mb = max_size / (1024 * 1024)
        file_mb = file_size / (1024 * 1024)
        return False, _(f'Dosya boyutu çok büyük ({file_mb:.1f}MB). Maksimum: {max_mb:.0f}MB')

    return True, None


def validate_mime_type(file) -> Tuple[bool, Optional[str]]:
    """
    Validate file MIME type using python-magic.

    Args:
        file: Django UploadedFile instance

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Read first 2048 bytes for magic number detection
    file.seek(0)
    file_header = file.read(2048)
    file.seek(0)  # Reset file pointer

    try:
        detected_mime = magic.from_buffer(file_header, mime=True)
    except Exception as e:
        logger.error(f"MIME detection failed: {e}")
        return False, _('Dosya tipi belirlenemedi.')

    # Check if detected MIME type is in allowed list
    allowed_mimes = []
    for file_type_info in ALLOWED_FILE_TYPES.values():
        allowed_mimes.extend(file_type_info['mime_types'])

    if detected_mime not in allowed_mimes:
        logger.warning(f"Disallowed MIME type detected: {detected_mime}")
        return False, _(f'Desteklenmeyen dosya tipi: {detected_mime}')

    return True, None


def validate_extension_matches_content(file) -> Tuple[bool, Optional[str]]:
    """
    Validate that file extension matches its actual content.
    Prevents extension spoofing attacks.

    Args:
        file: Django UploadedFile instance

    Returns:
        Tuple of (is_valid, error_message)
    """
    filename = file.name
    ext = os.path.splitext(filename)[1].lower()

    # Read file header for MIME detection
    file.seek(0)
    file_header = file.read(2048)
    file.seek(0)

    try:
        detected_mime = magic.from_buffer(file_header, mime=True)
    except Exception:
        return False, _('Dosya içeriği doğrulanamadı.')

    # Find expected MIME types for the extension
    expected_mimes = None
    for file_type, file_type_info in ALLOWED_FILE_TYPES.items():
        if ext in file_type_info['extensions']:
            expected_mimes = file_type_info['mime_types']
            break

    if expected_mimes is None:
        return False, _('Desteklenmeyen dosya uzantısı.')

    if detected_mime not in expected_mimes:
        logger.warning(
            f"Extension mismatch: filename={filename}, "
            f"extension={ext}, detected_mime={detected_mime}"
        )
        return False, _('Dosya içeriği uzantısıyla eşleşmiyor.')

    return True, None


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent security issues.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    import uuid

    # Get extension
    name, ext = os.path.splitext(filename)

    # Remove dangerous characters
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', name)

    # Replace spaces with underscores
    name = name.replace(' ', '_')

    # Limit length
    max_name_length = 200
    if len(name) > max_name_length:
        name = name[:max_name_length]

    # If name is empty after sanitization, use UUID
    if not name:
        name = uuid.uuid4().hex[:8]

    # Ensure extension is lowercase
    ext = ext.lower()

    return f"{name}{ext}"


def get_file_type(file) -> Optional[str]:
    """
    Determine file type from uploaded file.

    Args:
        file: Django UploadedFile instance

    Returns:
        File type string (pdf, docx, txt, md) or None
    """
    filename = file.name
    ext = os.path.splitext(filename)[1].lower()

    for file_type, file_type_info in ALLOWED_FILE_TYPES.items():
        if ext in file_type_info['extensions']:
            return file_type

    return None


# ===========================================
# Django Validator Classes
# ===========================================

class FileValidator:
    """
    Django form/serializer validator for file uploads.

    Usage:
        file = serializers.FileField(validators=[FileValidator()])
    """

    def __init__(self, max_size: int = None, allowed_types: list = None):
        self.max_size = max_size or MAX_FILE_SIZE
        self.allowed_types = allowed_types or list(ALLOWED_FILE_TYPES.keys())

    def __call__(self, file):
        is_valid, error = validate_file_upload(file)
        if not is_valid:
            raise ValidationError(error)


class FileSizeValidator:
    """
    Validator for file size only.

    Usage:
        file = serializers.FileField(validators=[FileSizeValidator(max_size=10*1024*1024)])
    """

    def __init__(self, max_size: int):
        self.max_size = max_size

    def __call__(self, file):
        is_valid, error = validate_file_size(file, self.max_size)
        if not is_valid:
            raise ValidationError(error)


class MimeTypeValidator:
    """
    Validator for MIME type only.

    Usage:
        file = serializers.FileField(validators=[MimeTypeValidator()])
    """

    def __call__(self, file):
        is_valid, error = validate_mime_type(file)
        if not is_valid:
            raise ValidationError(error)
