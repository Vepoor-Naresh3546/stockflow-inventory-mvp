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
        Organization.objects.create(owner=self.user, name="Owner Org")

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

    def test_dashboard_shows_organization_totals_and_low_stock_thresholds(self):
        self.organization.default_low_stock_threshold = 5
        self.organization.save(update_fields=["default_low_stock_threshold"])
        Product.objects.create(
            organization=self.organization,
            name="Default threshold low",
            sku="DEFAULT-LOW",
            quantity_on_hand=5,
        )
        Product.objects.create(
            organization=self.organization,
            name="Own threshold low",
            sku="OWN-LOW",
            quantity_on_hand=2,
            low_stock_threshold=2,
        )
        Product.objects.create(
            organization=self.organization,
            name="Above own threshold",
            sku="OWN-OK",
            quantity_on_hand=3,
            low_stock_threshold=2,
        )
        Product.objects.create(
            organization=self.other_organization,
            name="Other organization product",
            sku="OTHER-DASH",
            quantity_on_hand=100,
        )

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["product_count"], 3)
        self.assertEqual(response.context["total_quantity"], 10)
        self.assertContains(response, "Default threshold low")
        self.assertContains(response, "Own threshold low")
        self.assertNotContains(response, "Above own threshold")
        self.assertNotContains(response, "Other organization product")
        low_stock = list(response.context["low_stock_products"])
        self.assertEqual(
            [(product.sku, product.effective_threshold) for product in low_stock],
            [("DEFAULT-LOW", 5), ("OWN-LOW", 2)],
        )
        self.assertContains(response, reverse("product_list"))

    def test_dashboard_shows_zero_totals_and_helpful_empty_state(self):
        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["product_count"], 0)
        self.assertEqual(response.context["total_quantity"], 0)
        self.assertContains(response, "You don’t have any products yet.")
        self.assertContains(response, reverse("product_list"))

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
        self.assertContains(response, reverse("product_edit", args=[Product.objects.get(sku="MY-1").pk]))
        self.assertContains(response, reverse("product_delete", args=[Product.objects.get(sku="MY-1").pk]))

    def test_product_list_displays_low_stock_using_item_or_organization_threshold(self):
        self.organization.default_low_stock_threshold = 5
        self.organization.save(update_fields=["default_low_stock_threshold"])
        Product.objects.create(
            organization=self.organization,
            name="Default threshold boundary",
            sku="DEFAULT-BOUNDARY",
            quantity_on_hand=5,
        )
        Product.objects.create(
            organization=self.organization,
            name="Own threshold boundary",
            sku="OWN-BOUNDARY",
            quantity_on_hand=3,
            low_stock_threshold=3,
        )
        Product.objects.create(
            organization=self.organization,
            name="Above own threshold",
            sku="OWN-ABOVE",
            quantity_on_hand=4,
            low_stock_threshold=3,
        )

        response = self.client.get(reverse("product_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<table")
        self.assertContains(response, "Default threshold boundary")
        self.assertContains(response, "Own threshold boundary")
        self.assertContains(response, "Above own threshold")
        self.assertEqual(
            response.context["products"].get(sku="DEFAULT-BOUNDARY").is_low_stock,
            True,
        )
        self.assertEqual(
            response.context["products"].get(sku="OWN-BOUNDARY").is_low_stock,
            True,
        )
        self.assertEqual(
            response.context["products"].get(sku="OWN-ABOVE").is_low_stock,
            False,
        )

    def test_product_list_search_matches_name_or_sku_and_stays_organization_scoped(self):
        Product.objects.create(
            organization=self.organization, name="Green apple", sku="FRUIT-1"
        )
        Product.objects.create(
            organization=self.organization, name="Desk lamp", sku="GREEN-2"
        )
        Product.objects.create(
            organization=self.other_organization,
            name="Green item",
            sku="GREEN-3",
        )

        name_response = self.client.get(
            reverse("product_list"), {"q": "green apple"}
        )
        sku_response = self.client.get(reverse("product_list"), {"q": "GREEN-2"})

        self.assertContains(name_response, "Green apple")
        self.assertNotContains(name_response, "Desk lamp")
        self.assertNotContains(name_response, "Green item")
        self.assertContains(sku_response, "Desk lamp")
        self.assertNotContains(sku_response, "Green apple")
        self.assertNotContains(sku_response, "Green item")

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
        product = Product.objects.create(
            organization=self.organization, name="Protected", sku="PROTECTED-1"
        )
        protected_urls = [
            reverse("product_list"),
            reverse("product_create"),
            reverse("product_edit", args=[product.pk]),
            reverse("product_delete", args=[product.pk]),
        ]
        for url in protected_urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertRedirects(
                    response,
                    f"{reverse('login')}?next={url}",
                )

        self.client.force_login(self.user)
        response = self.client.get(reverse("product_create"))
        self.assertContains(response, 'name="csrfmiddlewaretoken"')

    def test_product_edit_updates_only_the_current_organizations_product(self):
        product = Product.objects.create(
            organization=self.organization, name="Old name", sku="EDIT-1"
        )

        response = self.client.post(
            reverse("product_edit", args=[product.pk]),
            {
                "name": "Updated name",
                "sku": "EDIT-1",
                "description": "Updated",
                "quantity_on_hand": "3",
                "cost_price": "",
                "selling_price": "",
                "low_stock_threshold": "",
                "organization": str(self.other_organization.pk),
            },
        )

        self.assertRedirects(response, reverse("product_list"))
        product.refresh_from_db()
        self.assertEqual(product.name, "Updated name")
        self.assertEqual(product.organization, self.organization)

    def test_edit_and_delete_cannot_access_another_organizations_product(self):
        product = Product.objects.create(
            organization=self.other_organization,
            name="Other product",
            sku="OTHER-2",
        )

        edit_response = self.client.get(
            reverse("product_edit", args=[product.pk])
        )
        delete_response = self.client.get(
            reverse("product_delete", args=[product.pk])
        )
        delete_post_response = self.client.post(
            reverse("product_delete", args=[product.pk])
        )

        self.assertEqual(edit_response.status_code, 404)
        self.assertEqual(delete_response.status_code, 404)
        self.assertEqual(delete_post_response.status_code, 404)
        self.assertTrue(Product.objects.filter(pk=product.pk).exists())

    def test_delete_requires_confirmation_and_post(self):
        product = Product.objects.create(
            organization=self.organization, name="To delete", sku="DELETE-1"
        )
        delete_url = reverse("product_delete", args=[product.pk])

        response = self.client.get(delete_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Are you sure")
        self.assertContains(response, 'name="csrfmiddlewaretoken"')
        self.assertTrue(Product.objects.filter(pk=product.pk).exists())

        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        response = csrf_client.post(delete_url)
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Product.objects.filter(pk=product.pk).exists())

        response = self.client.post(delete_url)
        self.assertRedirects(response, reverse("product_list"))
        self.assertFalse(Product.objects.filter(pk=product.pk).exists())
