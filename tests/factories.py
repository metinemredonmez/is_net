"""
IOSP - Factory Boy Factories for Testing
"""
import factory
from factory.django import DjangoModelFactory
from faker import Faker

from apps.accounts.models import User, Department, UserActivity
from apps.documents.models import Document, DocumentCategory, DocumentChunk
from apps.chat.models import Conversation, Message

fake = Faker('tr_TR')


# ===========================================
# Account Factories
# ===========================================

class DepartmentFactory(DjangoModelFactory):
    """Factory for Department model."""

    class Meta:
        model = Department

    name = factory.LazyAttribute(lambda _: fake.company())
    code = factory.Sequence(lambda n: f'DEPT{n:03d}')
    description = factory.LazyAttribute(lambda _: fake.paragraph())


class UserFactory(DjangoModelFactory):
    """Factory for User model."""

    class Meta:
        model = User
        skip_postgeneration_save = True

    email = factory.LazyAttribute(lambda _: fake.unique.email())
    full_name = factory.LazyAttribute(lambda _: fake.name())
    phone = factory.LazyAttribute(lambda _: fake.phone_number())
    role = 'viewer'
    is_active = True
    is_staff = False
    department = factory.SubFactory(DepartmentFactory)

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        password = extracted or 'testpass123'
        self.set_password(password)
        if create:
            self.save()

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Override create to handle password properly."""
        password = kwargs.pop('password', 'testpass123')
        user = super()._create(model_class, *args, **kwargs)
        user.set_password(password)
        user.save()
        return user


class UserActivityFactory(DjangoModelFactory):
    """Factory for UserActivity model."""

    class Meta:
        model = UserActivity

    user = factory.SubFactory(UserFactory)
    activity_type = 'login'
    description = factory.LazyAttribute(lambda _: fake.sentence())
    ip_address = factory.LazyAttribute(lambda _: fake.ipv4())
    user_agent = factory.LazyAttribute(lambda _: fake.user_agent())


# ===========================================
# Document Factories
# ===========================================

class DocumentCategoryFactory(DjangoModelFactory):
    """Factory for DocumentCategory model."""

    class Meta:
        model = DocumentCategory

    name = factory.LazyAttribute(lambda _: fake.word().title())
    slug = factory.Sequence(lambda n: f'category-{n}')
    description = factory.LazyAttribute(lambda _: fake.paragraph())
    icon = 'fa-folder'
    color = factory.LazyAttribute(lambda _: fake.hex_color())


class DocumentFactory(DjangoModelFactory):
    """Factory for Document model."""

    class Meta:
        model = Document

    title = factory.LazyAttribute(lambda _: fake.sentence(nb_words=5))
    description = factory.LazyAttribute(lambda _: fake.paragraph())
    file_type = 'pdf'
    file_size = factory.LazyAttribute(lambda _: fake.random_int(min=1000, max=10000000))
    status = 'pending'
    chunk_count = 0
    is_public = False
    uploaded_by = factory.SubFactory(UserFactory, role='analyst')
    category = factory.SubFactory(DocumentCategoryFactory)

    @factory.lazy_attribute
    def file(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        return SimpleUploadedFile(
            name='test_doc.pdf',
            content=b'%PDF-1.4 test content',
            content_type='application/pdf'
        )


class DocumentChunkFactory(DjangoModelFactory):
    """Factory for DocumentChunk model."""

    class Meta:
        model = DocumentChunk

    document = factory.SubFactory(DocumentFactory)
    chunk_index = factory.Sequence(lambda n: n)
    content = factory.LazyAttribute(lambda _: fake.paragraph(nb_sentences=5))
    token_count = factory.LazyAttribute(lambda _: fake.random_int(min=100, max=500))
    vector_id = factory.LazyAttribute(lambda _: fake.uuid4())
    page_number = factory.LazyAttribute(lambda _: fake.random_int(min=1, max=50))


# ===========================================
# Chat Factories
# ===========================================

class ConversationFactory(DjangoModelFactory):
    """Factory for Conversation model."""

    class Meta:
        model = Conversation

    user = factory.SubFactory(UserFactory)
    title = factory.LazyAttribute(lambda _: fake.sentence(nb_words=4))
    is_active = True


class MessageFactory(DjangoModelFactory):
    """Factory for Message model."""

    class Meta:
        model = Message

    conversation = factory.SubFactory(ConversationFactory)
    role = 'user'
    content = factory.LazyAttribute(lambda _: fake.paragraph())
    confidence = factory.LazyAttribute(lambda _: fake.pyfloat(min_value=0, max_value=1, right_digits=2))
    is_helpful = None
    tokens_used = factory.LazyAttribute(lambda _: fake.random_int(min=10, max=500))
    response_time_ms = factory.LazyAttribute(lambda _: fake.random_int(min=100, max=5000))

    @factory.lazy_attribute
    def sources(self):
        return [
            {'content': fake.paragraph(), 'relevance': 0.85},
            {'content': fake.paragraph(), 'relevance': 0.72},
        ]
