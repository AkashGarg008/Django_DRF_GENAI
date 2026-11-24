import io
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token

from .models import Document, QueryLog, UserSession
from .serializers import RegisterSerializer, DocumentSerializer, QueryLogSerializer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user(username='alice', password='pass1234'):
    user = User.objects.create_user(username=username, password=password, email=f'{username}@test.com')
    token, _ = Token.objects.get_or_create(user=user)
    return user, token


def auth_client(token):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
    return client


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

class DocumentModelTest(TestCase):
    def setUp(self):
        self.user, _ = make_user()

    def test_str_returns_title(self):
        doc = Document.objects.create(title='My Doc', content='hello', owner=self.user)
        self.assertEqual(str(doc), 'My Doc')

    def test_default_ordering_newest_first(self):
        doc1 = Document.objects.create(title='First', content='', owner=self.user)
        doc2 = Document.objects.create(title='Second', content='', owner=self.user)
        docs = list(Document.objects.all())
        self.assertEqual(docs[0], doc2)
        self.assertEqual(docs[1], doc1)

    def test_uploaded_at_auto_set(self):
        doc = Document.objects.create(title='T', content='', owner=self.user)
        self.assertIsNotNone(doc.uploaded_at)


class QueryLogModelTest(TestCase):
    def setUp(self):
        self.user, _ = make_user()

    def test_str_truncates_long_text(self):
        long_text = 'x' * 100
        log = QueryLog.objects.create(query_text=long_text, user=self.user)
        self.assertEqual(str(log), 'x' * 50)

    def test_created_at_auto_set(self):
        log = QueryLog.objects.create(query_text='test', user=self.user)
        self.assertIsNotNone(log.created_at)

    def test_default_ordering_newest_first(self):
        log1 = QueryLog.objects.create(query_text='first', user=self.user)
        log2 = QueryLog.objects.create(query_text='second', user=self.user)
        logs = list(QueryLog.objects.all())
        self.assertEqual(logs[0], log2)


class UserSessionModelTest(TestCase):
    def setUp(self):
        self.user, _ = make_user()

    def test_str(self):
        session = UserSession.objects.create(
            user=self.user,
            token='abc123',
            expires_at=timezone.now() + timedelta(hours=1),
        )
        self.assertIn(self.user.username, str(session))


# ---------------------------------------------------------------------------
# Serializer tests
# ---------------------------------------------------------------------------

class RegisterSerializerTest(TestCase):
    def test_valid_data_creates_user(self):
        s = RegisterSerializer(data={'username': 'bob', 'password': 'secret99', 'email': 'bob@test.com'})
        self.assertTrue(s.is_valid())
        user = s.save()
        self.assertTrue(user.check_password('secret99'))

    def test_password_write_only(self):
        s = RegisterSerializer(data={'username': 'bob', 'password': 'secret99'})
        s.is_valid()
        s.save()
        self.assertNotIn('password', s.data)

    def test_short_password_invalid(self):
        s = RegisterSerializer(data={'username': 'bob', 'password': '123'})
        self.assertFalse(s.is_valid())
        self.assertIn('password', s.errors)

    def test_duplicate_username_invalid(self):
        User.objects.create_user(username='bob', password='pass1234')
        s = RegisterSerializer(data={'username': 'bob', 'password': 'pass1234'})
        self.assertFalse(s.is_valid())


class DocumentSerializerTest(TestCase):
    def setUp(self):
        self.user, _ = make_user()

    def test_serializes_owner_as_username(self):
        doc = Document.objects.create(title='T', content='C', owner=self.user)
        data = DocumentSerializer(doc).data
        self.assertEqual(data['owner'], self.user.username)

    def test_read_only_fields_ignored_on_input(self):
        other_user, _ = make_user('bob')
        s = DocumentSerializer(data={'title': 'T', 'content': 'C', 'owner': other_user.username, 'id': 999})
        self.assertTrue(s.is_valid())

    def test_title_required(self):
        s = DocumentSerializer(data={'content': 'no title'})
        self.assertFalse(s.is_valid())
        self.assertIn('title', s.errors)


# ---------------------------------------------------------------------------
# Auth endpoint tests
# ---------------------------------------------------------------------------

class RegisterViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_register_success(self):
        r = self.client.post('/register', {'username': 'alice', 'password': 'pass1234'}, format='json')
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertIn('token', r.data)
        self.assertEqual(r.data['username'], 'alice')

    def test_register_missing_password(self):
        r = self.client.post('/register', {'username': 'alice'}, format='json')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_duplicate_username(self):
        self.client.post('/register', {'username': 'alice', 'password': 'pass1234'}, format='json')
        r = self.client.post('/register', {'username': 'alice', 'password': 'pass5678'}, format='json')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_no_auth_required(self):
        r = self.client.post('/register', {'username': 'newuser', 'password': 'pass1234'}, format='json')
        self.assertNotEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)


class LoginViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        make_user('alice', 'pass1234')

    def test_login_success(self):
        r = self.client.post('/login', {'username': 'alice', 'password': 'pass1234'}, format='json')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIn('token', r.data)

    def test_login_wrong_password(self):
        r = self.client.post('/login', {'username': 'alice', 'password': 'wrong'}, format='json')
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_nonexistent_user(self):
        r = self.client.post('/login', {'username': 'nobody', 'password': 'pass1234'}, format='json')
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_returns_same_token_as_register(self):
        user = User.objects.get(username='alice')
        token = Token.objects.get(user=user)
        r = self.client.post('/login', {'username': 'alice', 'password': 'pass1234'}, format='json')
        self.assertEqual(r.data['token'], token.key)


# ---------------------------------------------------------------------------
# Document endpoint tests
# ---------------------------------------------------------------------------

class DocumentCreateTest(TestCase):
    def setUp(self):
        self.user, self.token = make_user()
        self.client = auth_client(self.token)

    def test_create_document_json(self):
        r = self.client.post('/documents', {'title': 'Doc1', 'content': 'Hello'}, format='json')
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data['title'], 'Doc1')
        self.assertEqual(r.data['owner'], self.user.username)

    def test_create_document_missing_title(self):
        r = self.client.post('/documents', {'content': 'no title'}, format='json')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_document_unauthenticated(self):
        r = APIClient().post('/documents', {'title': 'T', 'content': 'C'}, format='json')
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_document_file_upload(self):
        f = io.BytesIO(b'File content here')
        f.name = 'test.txt'
        r = self.client.post('/documents', {'file': f, 'title': 'Uploaded'}, format='multipart')
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data['title'], 'Uploaded')

    def test_create_document_file_uses_filename_as_title(self):
        f = io.BytesIO(b'content')
        f.name = 'myfile.txt'
        r = self.client.post('/documents', {'file': f}, format='multipart')
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data['title'], 'myfile.txt')

    def test_create_document_file_too_large(self):
        big = io.BytesIO(b'x' * (6 * 1024 * 1024))  # 6 MB > 5 MB limit
        big.name = 'big.txt'
        r = self.client.post('/documents', {'file': big}, format='multipart')
        self.assertEqual(r.status_code, status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)

    def test_owner_set_from_token_not_body(self):
        other, _ = make_user('bob')
        r = self.client.post('/documents', {'title': 'T', 'content': 'C', 'owner': 'bob'}, format='json')
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data['owner'], self.user.username)


class DocumentListTest(TestCase):
    def setUp(self):
        self.user, self.token = make_user()
        self.client = auth_client(self.token)
        self.other_user, self.other_token = make_user('bob')

    def test_list_returns_paginated_response(self):
        Document.objects.create(title='D1', content='', owner=self.user)
        r = self.client.get('/documents')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIn('count', r.data)
        self.assertIn('results', r.data)
        self.assertIn('next', r.data)
        self.assertIn('previous', r.data)

    def test_list_only_own_documents(self):
        Document.objects.create(title='Mine', content='', owner=self.user)
        Document.objects.create(title='Theirs', content='', owner=self.other_user)
        r = self.client.get('/documents')
        titles = [d['title'] for d in r.data['results']]
        self.assertIn('Mine', titles)
        self.assertNotIn('Theirs', titles)

    def test_list_unauthenticated(self):
        r = APIClient().get('/documents')
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_pagination_page_size(self):
        for i in range(15):
            Document.objects.create(title=f'Doc{i}', content='', owner=self.user)
        r = self.client.get('/documents?page_size=5')
        self.assertEqual(len(r.data['results']), 5)
        self.assertEqual(r.data['count'], 15)

    def test_list_default_page_size_10(self):
        for i in range(12):
            Document.objects.create(title=f'Doc{i}', content='', owner=self.user)
        r = self.client.get('/documents')
        self.assertEqual(len(r.data['results']), 10)


class DocumentDetailTest(TestCase):
    def setUp(self):
        self.user, self.token = make_user()
        self.client = auth_client(self.token)
        self.other_user, self.other_token = make_user('bob')
        self.doc = Document.objects.create(title='My Doc', content='hello', owner=self.user)

    def test_get_own_document(self):
        r = self.client.get(f'/documents/{self.doc.id}')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['title'], 'My Doc')

    def test_get_nonexistent_document_404(self):
        r = self.client.get('/documents/9999')
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_other_users_document_404(self):
        other_doc = Document.objects.create(title='Theirs', content='', owner=self.other_user)
        r = self.client.get(f'/documents/{other_doc.id}')
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_own_document(self):
        r = self.client.delete(f'/documents/{self.doc.id}')
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Document.objects.filter(id=self.doc.id).exists())

    def test_delete_other_users_document_403(self):
        other_doc = Document.objects.create(title='Theirs', content='', owner=self.other_user)
        r = self.client.delete(f'/documents/{other_doc.id}')
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_nonexistent_document_404(self):
        r = self.client.delete('/documents/9999')
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_detail_unauthenticated(self):
        r = APIClient().get(f'/documents/{self.doc.id}')
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)


# ---------------------------------------------------------------------------
# Query endpoint tests
# ---------------------------------------------------------------------------

class QueryCreateTest(TestCase):
    def setUp(self):
        self.user, self.token = make_user()
        self.client = auth_client(self.token)

    def test_create_query_log(self):
        r = self.client.post('/query', {'query_text': 'what is AI?'}, format='json')
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data['query_text'], 'what is AI?')
        self.assertEqual(r.data['user'], self.user.username)

    def test_create_query_missing_text(self):
        r = self.client.post('/query', {}, format='json')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_query_whitespace_only(self):
        r = self.client.post('/query', {'query_text': '   '}, format='json')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_query_unauthenticated(self):
        r = APIClient().post('/query', {'query_text': 'test'}, format='json')
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_query_result_summary_empty(self):
        r = self.client.post('/query', {'query_text': 'test'}, format='json')
        self.assertEqual(r.data['result_summary'], '')

    def test_query_saved_to_database(self):
        self.client.post('/query', {'query_text': 'save me'}, format='json')
        self.assertTrue(QueryLog.objects.filter(query_text='save me', user=self.user).exists())


class QueryListTest(TestCase):
    def setUp(self):
        self.user, self.token = make_user()
        self.client = auth_client(self.token)
        self.other_user, self.other_token = make_user('bob')

    def test_list_own_queries(self):
        QueryLog.objects.create(query_text='mine', user=self.user)
        QueryLog.objects.create(query_text='theirs', user=self.other_user)
        r = self.client.get('/queries')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        texts = [q['query_text'] for q in r.data['results']]
        self.assertIn('mine', texts)
        self.assertNotIn('theirs', texts)

    def test_list_paginated(self):
        for i in range(12):
            QueryLog.objects.create(query_text=f'q{i}', user=self.user)
        r = self.client.get('/queries')
        self.assertEqual(len(r.data['results']), 10)
        self.assertEqual(r.data['count'], 12)

    def test_list_unauthenticated(self):
        r = APIClient().get('/queries')
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_empty(self):
        r = self.client.get('/queries')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['count'], 0)
        self.assertEqual(r.data['results'], [])
