from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import (
    BooleanField,
    Case,
    Count,
    F,
    PositiveIntegerField,
    Q,
    Sum,
    Value,
    When,
)
from django.shortcuts import get_object_or_404, redirect, render

from .forms import OrganizationSettingsForm, ProductForm, SignupForm
from .models import Organization, Product


def annotate_stock_status(products, organization):
    return products.annotate(
        effective_threshold=Case(
            When(
                low_stock_threshold__isnull=True,
                then=Value(organization.default_low_stock_threshold),
            ),
            default=F("low_stock_threshold"),
            output_field=PositiveIntegerField(),
        )
    ).annotate(
        is_low_stock=Case(
            When(
                quantity_on_hand__lte=F("effective_threshold"),
                then=Value(True),
            ),
            default=Value(False),
            output_field=BooleanField(),
        )
    )


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
    organization = request.user.organization
    products = Product.objects.filter(organization=organization)
    totals = products.aggregate(
        product_count=Count("pk"),
        total_quantity=Sum("quantity_on_hand"),
    )
    low_stock_products = list(
        annotate_stock_status(products, organization)
        .filter(is_low_stock=True)
        .order_by("name")
    )
    return render(
        request,
        "inventory/dashboard.html",
        {
            "organization": organization,
            "product_count": totals["product_count"],
            "total_quantity": totals["total_quantity"] or 0,
            "low_stock_count": len(low_stock_products),
            "low_stock_products": low_stock_products,
            "active_page": "dashboard",
        },
    )


@login_required(login_url="login")
def product_list(request):
    organization = request.user.organization
    search_query = request.GET.get("q", "").strip()
    products = Product.objects.filter(organization=organization)
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) | Q(sku__icontains=search_query)
        )
    products = annotate_stock_status(products, organization)
    return render(
        request,
        "inventory/product_list.html",
        {
            "organization": organization,
            "products": products,
            "search_query": search_query,
            "active_page": "products",
        },
    )


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
        {
            "form": form,
            "page_title": "Add product",
            "submit_label": "Save product",
            "organization": organization,
            "active_page": "add_product",
        },
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
            "organization": organization,
            "active_page": "products",
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
        {
            "product": product,
            "organization": request.user.organization,
            "active_page": "products",
        },
    )


@login_required(login_url="login")
def organization_settings(request):
    organization = request.user.organization
    if request.method == "POST":
        form = OrganizationSettingsForm(request.POST, instance=organization)
        if form.is_valid():
            form.save()
            messages.success(request, "Organization settings saved.")
            return redirect("organization_settings")
    else:
        form = OrganizationSettingsForm(instance=organization)

    return render(
        request,
        "inventory/organization_settings.html",
        {
            "form": form,
            "organization": organization,
            "active_page": "settings",
        },
    )
