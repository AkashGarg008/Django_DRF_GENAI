from django.db import models
from django.contrib.auth.models import User


class Document(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.title


class QueryLog(models.Model):
    query_text = models.TextField()
    result_summary = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='query_logs')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.query_text[:50]


class UserSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    token = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def __str__(self):
        return f"{self.user.username} session"
