from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from .models import Organization, Product


class SignupTests(TestCase):
    def test_signup_creates_user_and_organization_and_logs_user_in(self):
        response = self.client.post(
            reverse("signup"),
            {
                "email": "  OWNER@EXAMPLE.COM ",
                "password1": "A-strong-password-42",
                "password2": "A-strong-password-42",
                "organization_name": "Example Org",
            },
        )

        self.assertRedirects(response, reverse("dashboard"))
        user = User.objects.get(username="owner@example.com")
        self.assertEqual(user.email, "owner@example.com")
        self.assertEqual(user.organization.name, "Example Org")
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_signup_rejects_an_email_that_is_already_registered(self):
        User.objects.create_user(
            username="owner@example.com",
            email="owner@example.com",
            password="A-strong-password-42",
        )

        response = self.client.post(
            reverse("signup"),
            {
                "email": "OWNER@example.com",
                "password1": "A-strong-password-42",
                "password2": "A-strong-password-42",
                "organization_name": "Example Org",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), 1)
        self.assertContains(response, "already exists")

    def test_signup_requires_matching_passwords(self):
        response = self.client.post(
            reverse("signup"),
            {
                "email": "owner@example.com",
                "password1": "A-strong-password-42",
                "password2": "A-different-password-42",
                "organization_name": "Example Org",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.exists())
        self.assertIn("password2", response.context["form"].errors)


class AuthenticationFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="owner@example.com",
            email="owner@example.com",
            password="A-strong-password-42",
        )

    def test_login_accepts_email_and_redirects_to_dashboard(self):
        response = self.client.post(
            reverse("login"),
            {"username": "OWNER@EXAMPLE.COM", "password": "A-strong-password-42"},
        )

        self.assertRedirects(response, reverse("dashboard"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)

    def test_dashboard_requires_login_and_logout_uses_post(self):
        response = self.client.get(reverse("dashboard"))
        self.assertRedirects(
            response, f"{reverse('login')}?next={reverse('dashboard')}"
        )

        self.client.force_login(self.user)
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse("logout"))
        self.assertEqual(response.status_code, 405)

        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, reverse("login"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_authentication_forms_render_csrf_tokens(self):
        for route in ("signup", "login"):
            with self.subTest(route=route):
                response = self.client.get(reverse(route))
                self.assertContains(response, 'name="csrfmiddlewaretoken"')

    def test_authentication_posts_require_csrf_tokens(self):
        csrf_client = Client(enforce_csrf_checks=True)
        response = csrf_client.post(
            reverse("signup"),
            {
                "email": "owner@example.com",
                "password1": "A-strong-password-42",
                "password2": "A-strong-password-42",
                "organization_name": "Example Org",
            },
        )
        self.assertEqual(response.status_code, 403)

        response = csrf_client.post(
            reverse("login"),
            {"username": "owner@example.com", "password": "A-strong-password-42"},
        )
        self.assertEqual(response.status_code, 403)


class ProductPageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="owner@example.com",
            email="owner@example.com",
            password="A-strong-password-42",
        )
        self.organization = Organization.objects.create(
            owner=self.user, name="Owner Org"
        )
        other_user = User.objects.create_user(
            username="other@example.com",
            email="other@example.com",
            password="A-strong-password-42",
        )
        self.other_organization = Organization.objects.create(
            owner=other_user, name="Other Org"
        )
        self.client.force_login(self.user)

    def test_product_list_only_shows_current_organizations_products(self):
        Product.objects.create(
            organization=self.organization, name="My product", sku="MY-1"
        )
        Product.objects.create(
            organization=self.other_organization,
            name="Other product",
            sku="OTHER-1",
        )

        response = self.client.get(reverse("product_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "My product")
        self.assertNotContains(response, "Other product")

    def test_product_create_assigns_users_organization_and_ignores_submitted_id(self):
        response = self.client.post(
            reverse("product_create"),
            {
                "name": "New product",
                "sku": "NEW-1",
                "description": "A test product",
                "quantity_on_hand": "4",
                "cost_price": "1.25",
                "selling_price": "2.50",
                "low_stock_threshold": "",
                "organization": str(self.other_organization.pk),
            },
        )

        self.assertRedirects(response, reverse("product_list"))
        product = Product.objects.get(sku="NEW-1")
        self.assertEqual(product.organization, self.organization)
        self.assertIsNone(product.low_stock_threshold)

    def test_product_create_shows_clear_duplicate_sku_error(self):
        Product.objects.create(
            organization=self.organization, name="Existing", sku="DUP-1"
        )

        response = self.client.post(
            reverse("product_create"),
            {
                "name": "Duplicate",
                "sku": "DUP-1",
                "description": "",
                "quantity_on_hand": "0",
                "cost_price": "",
                "selling_price": "",
                "low_stock_threshold": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Product.objects.filter(organization=self.organization).count(), 1)
        self.assertContains(
            response,
            "A product with this SKU already exists in your organization.",
        )

    def test_product_pages_require_login_and_include_csrf(self):
        self.client.logout()
        for route in ("product_list", "product_create"):
            with self.subTest(route=route):
                response = self.client.get(reverse(route))
                self.assertRedirects(
                    response,
                    f"{reverse('login')}?next={reverse(route)}",
                )

        self.client.force_login(self.user)
        response = self.client.get(reverse("product_create"))
        self.assertContains(response, 'name="csrfmiddlewaretoken"')
