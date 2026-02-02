"""
Accounts Serializers
"""
import re
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from .models import User, Department


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['id', 'name', 'code']


class UserSerializer(serializers.ModelSerializer):
    department = DepartmentSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'full_name', 'phone', 'role',
            'department', 'is_active', 'last_login', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'last_login']


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Kullanıcı kayıt serializer'ı.
    Email benzersizlik kontrolü ve güvenli parola validasyonu içerir.
    """
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={'input_type': 'password'},
        help_text='En az 8 karakter, büyük/küçük harf ve rakam içermeli'
    )
    password_confirm = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        help_text='Parolayı tekrar girin'
    )

    class Meta:
        model = User
        fields = [
            'email',
            'full_name',
            'phone',
            'password',
            'password_confirm',
        ]

    def validate_email(self, value):
        """Email benzersizlik kontrolü."""
        email = value.lower().strip()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError(
                'Bu e-posta adresi zaten kayıtlı.'
            )
        return email

    def validate_password(self, value):
        """Güvenli parola validasyonu."""
        # Django'nun built-in password validators
        try:
            validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))

        # Ek güvenlik kontrolleri
        if not re.search(r'[A-Z]', value):
            raise serializers.ValidationError(
                'Parola en az bir büyük harf içermelidir.'
            )
        if not re.search(r'[a-z]', value):
            raise serializers.ValidationError(
                'Parola en az bir küçük harf içermelidir.'
            )
        if not re.search(r'\d', value):
            raise serializers.ValidationError(
                'Parola en az bir rakam içermelidir.'
            )

        return value

    def validate(self, attrs):
        """Parola eşleşme kontrolü."""
        password = attrs.get('password')
        password_confirm = attrs.get('password_confirm')

        if password != password_confirm:
            raise serializers.ValidationError({
                'password_confirm': 'Parolalar eşleşmiyor.'
            })

        return attrs

    def create(self, validated_data):
        """Yeni kullanıcı oluştur."""
        # password_confirm'i kaldır
        validated_data.pop('password_confirm')

        # Kullanıcıyı oluştur (varsayılan rol: viewer)
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            full_name=validated_data['full_name'],
            phone=validated_data.get('phone', ''),
            role='viewer',  # Yeni kullanıcılar varsayılan olarak viewer
            is_active=True,  # Email doğrulama eklenmediği için direkt aktif
        )
        return user


class PasswordChangeSerializer(serializers.Serializer):
    """Parola değiştirme serializer'ı."""
    old_password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )

    def validate_old_password(self, value):
        """Mevcut parola kontrolü."""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Mevcut parola yanlış.')
        return value

    def validate_new_password(self, value):
        """Yeni parola validasyonu."""
        try:
            validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))

        if not re.search(r'[A-Z]', value):
            raise serializers.ValidationError(
                'Parola en az bir büyük harf içermelidir.'
            )
        if not re.search(r'[a-z]', value):
            raise serializers.ValidationError(
                'Parola en az bir küçük harf içermelidir.'
            )
        if not re.search(r'\d', value):
            raise serializers.ValidationError(
                'Parola en az bir rakam içermelidir.'
            )
        return value

    def validate(self, attrs):
        """Parola eşleşme ve farklılık kontrolü."""
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': 'Parolalar eşleşmiyor.'
            })

        if attrs['old_password'] == attrs['new_password']:
            raise serializers.ValidationError({
                'new_password': 'Yeni parola eski parola ile aynı olamaz.'
            })

        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    """Parola sıfırlama isteği serializer'ı."""
    email = serializers.EmailField()

    def validate_email(self, value):
        """Email'in kayıtlı olup olmadığını kontrol et."""
        email = value.lower().strip()
        # Güvenlik: Email var mı yok mu bilgisini verme
        # Sadece valid email formatı kontrolü
        return email


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Parola sıfırlama onay serializer'ı."""
    token = serializers.CharField()
    new_password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )

    def validate_new_password(self, value):
        """Yeni parola validasyonu."""
        try:
            validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))

        if not re.search(r'[A-Z]', value):
            raise serializers.ValidationError(
                'Parola en az bir büyük harf içermelidir.'
            )
        if not re.search(r'[a-z]', value):
            raise serializers.ValidationError(
                'Parola en az bir küçük harf içermelidir.'
            )
        if not re.search(r'\d', value):
            raise serializers.ValidationError(
                'Parola en az bir rakam içermelidir.'
            )
        return value

    def validate(self, attrs):
        """Parola eşleşme kontrolü."""
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': 'Parolalar eşleşmiyor.'
            })
        return attrs
