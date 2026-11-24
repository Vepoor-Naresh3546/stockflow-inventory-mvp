from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import Product


class SignupForm(forms.Form):
    email = forms.EmailField(max_length=254)
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(
        label="Confirm password", widget=forms.PasswordInput
    )
    organization_name = forms.CharField(max_length=150)

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if len(email) > User._meta.get_field("username").max_length:
            raise forms.ValidationError("Email must be 150 characters or fewer.")
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        if User.objects.filter(username__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data["password2"]
        if password1 and password1 != password2:
            raise forms.ValidationError("The passwords do not match.")
        return password2

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password1")
        email = cleaned_data.get("email")
        if password and email:
            user = User(username=email, email=email)
            try:
                validate_password(password, user)
            except ValidationError as error:
                self.add_error("password1", error)
        return cleaned_data


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label="Email",
        widget=forms.TextInput(attrs={"autofocus": True}),
    )

    def clean_username(self):
        return self.cleaned_data["username"].strip().lower()


class ProductForm(forms.ModelForm):
    def __init__(self, *args, organization, **kwargs):
        self.organization = organization
        super().__init__(*args, **kwargs)

    class Meta:
        model = Product
        fields = [
            "name",
            "sku",
            "description",
            "quantity_on_hand",
            "cost_price",
            "selling_price",
            "low_stock_threshold",
        ]

    def clean_sku(self):
        sku = self.cleaned_data["sku"]
        products = Product.objects.filter(organization=self.organization, sku=sku)
        if self.instance.pk:
            products = products.exclude(pk=self.instance.pk)
        if products.exists():
            raise forms.ValidationError(
                "A product with this SKU already exists in your organization."
            )
        return sku
