from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import redirect, render

from .forms import ProductForm, SignupForm
from .models import Organization, Product


def signup(request):
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                user = User.objects.create_user(
                    username=form.cleaned_data["email"],
                    email=form.cleaned_data["email"],
                    password=form.cleaned_data["password1"],
                )
                Organization.objects.create(
                    owner=user,
                    name=form.cleaned_data["organization_name"],
                )
            login(request, user)
            return redirect("dashboard")
    else:
        form = SignupForm()

    return render(request, "registration/signup.html", {"form": form})


@login_required(login_url="login")
def dashboard(request):
    return render(request, "inventory/dashboard.html")


@login_required(login_url="login")
def product_list(request):
    products = Product.objects.filter(organization=request.user.organization)
    return render(request, "inventory/product_list.html", {"products": products})


@login_required(login_url="login")
def product_create(request):
    organization = request.user.organization
    if request.method == "POST":
        form = ProductForm(request.POST, organization=organization)
        if form.is_valid():
            product = form.save(commit=False)
            product.organization = organization
            product.save()
            return redirect("product_list")
    else:
        form = ProductForm(organization=organization)

    return render(request, "inventory/product_form.html", {"form": form})
