from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Document, QueryLog


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class DocumentSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')

    class Meta:
        model = Document
        fields = ['id', 'title', 'content', 'uploaded_at', 'owner']
        read_only_fields = ['id', 'uploaded_at', 'owner']


class QueryLogSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')

    class Meta:
        model = QueryLog
        fields = ['id', 'query_text', 'result_summary', 'created_at', 'user']
        read_only_fields = ['id', 'result_summary', 'created_at', 'user']
