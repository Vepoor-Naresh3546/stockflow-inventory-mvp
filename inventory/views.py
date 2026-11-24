from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

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

    return render(
        request,
        "inventory/product_form.html",
        {"form": form, "page_title": "Add product", "submit_label": "Save product"},
    )


@login_required(login_url="login")
def product_edit(request, product_id):
    organization = request.user.organization
    product = get_object_or_404(
        Product, pk=product_id, organization=organization
    )
    if request.method == "POST":
        form = ProductForm(
            request.POST, instance=product, organization=organization
        )
        if form.is_valid():
            form.save()
            return redirect("product_list")
    else:
        form = ProductForm(instance=product, organization=organization)

    return render(
        request,
        "inventory/product_form.html",
        {
            "form": form,
            "page_title": "Edit product",
            "submit_label": "Save changes",
            "product": product,
        },
    )


@login_required(login_url="login")
def product_delete(request, product_id):
    product = get_object_or_404(
        Product, pk=product_id, organization=request.user.organization
    )
    if request.method == "POST":
        product.delete()
        return redirect("product_list")

    return render(
        request,
        "inventory/product_confirm_delete.html",
        {"product": product},
    )
