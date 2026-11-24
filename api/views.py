from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.authtoken.models import Token

from .models import Document, QueryLog
from .serializers import RegisterSerializer, DocumentSerializer, QueryLogSerializer
from .pagination import StandardPagination


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response({'token': token.key, 'username': user.username}, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    from django.contrib.auth import authenticate
    username = request.data.get('username')
    password = request.data.get('password')
    user = authenticate(username=username, password=password)
    if user is None:
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
    token, _ = Token.objects.get_or_create(user=user)
    return Response({'token': token.key, 'username': user.username})


@api_view(['POST', 'GET'])
@permission_classes([IsAuthenticated])
def documents(request):
    if request.method == 'POST':
        return _create_document(request)
    return _list_documents(request)


def _create_document(request):
    # Handle file upload
    if request.FILES.get('file'):
        f = request.FILES['file']
        max_size = getattr(settings, 'MAX_UPLOAD_SIZE', 5 * 1024 * 1024)
        if f.size > max_size:
            return Response({'error': 'File too large'}, status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
        allowed = getattr(settings, 'ALLOWED_FILE_TYPES', [])
        if allowed and f.content_type not in allowed:
            return Response({'error': 'File type not allowed'}, status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)
        content = f.read().decode('utf-8', errors='replace')
        title = request.data.get('title', f.name)
        doc = Document.objects.create(title=title, content=content, owner=request.user)
        return Response(DocumentSerializer(doc).data, status=status.HTTP_201_CREATED)

    # Handle JSON body
    serializer = DocumentSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(owner=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def _list_documents(request):
    qs = Document.objects.filter(owner=request.user)
    paginator = StandardPagination()
    page = paginator.paginate_queryset(qs, request)
    serializer = DocumentSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


@api_view(['GET', 'DELETE'])
@permission_classes([IsAuthenticated])
def document_detail(request, pk):
    try:
        doc = Document.objects.get(pk=pk)
    except Document.DoesNotExist:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        if doc.owner != request.user:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(DocumentSerializer(doc).data)

    if request.method == 'DELETE':
        if doc.owner != request.user:
            return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        doc.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def query(request):
    query_text = request.data.get('query_text', '').strip()
    if not query_text:
        return Response({'error': 'query_text is required'}, status=status.HTTP_400_BAD_REQUEST)
    log = QueryLog.objects.create(
        query_text=query_text,
        result_summary='',
        user=request.user,
    )
    return Response(QueryLogSerializer(log).data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def queries(request):
    qs = QueryLog.objects.filter(user=request.user)
    paginator = StandardPagination()
    page = paginator.paginate_queryset(qs, request)
    serializer = QueryLogSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)
