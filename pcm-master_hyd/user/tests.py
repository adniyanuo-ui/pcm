from django.contrib.auth.models import User
from django.test import TestCase
from django.test import override_settings
from rest_framework.test import APIRequestFactory

from tools.auth import TokenAuthentication
from user.cms.views import LoginView, RegisterView
from user.models import UserProfile


class LoginProfileTests(TestCase):
    def test_first_login_creates_profile_and_token_can_authenticate(self):
        user = User.objects.create_user(username="local_doctor", password="test-only-password")
        self.assertFalse(UserProfile.objects.filter(user=user).exists())

        factory = APIRequestFactory()
        request = factory.post(
            "/api/cms/user/login/",
            {"username": "local_doctor", "password": "test-only-password"},
            format="json",
        )
        response = LoginView.as_view({"post": "create"})(request)
        self.assertEqual(response.status_code, 200)
        issued_token = response.data["data"]["token"]
        self.assertEqual(UserProfile.objects.get(user=user).token, issued_token)

        authenticated_request = factory.get(
            "/api/cms/llm/rag/search/",
            HTTP_AUTHORIZATION=f"Token {issued_token}",
        )
        authenticated_user, _ = TokenAuthentication().authenticate(authenticated_request)
        self.assertEqual(authenticated_user.id, user.id)

    @override_settings(CMS_REGISTRATION_ENABLED=False)
    def test_registration_is_disabled_in_pilot(self):
        request = APIRequestFactory().post(
            "/api/cms/user/register/",
            {"username": "uninvited", "password": "not-used"},
            format="json",
        )

        response = RegisterView.as_view({"post": "create"})(request)

        self.assertEqual(response.status_code, 403)
        self.assertFalse(User.objects.filter(username="uninvited").exists())
