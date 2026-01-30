"""
Accounts Serializers
"""
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
