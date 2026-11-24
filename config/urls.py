"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

from inventory.forms import EmailAuthenticationForm
from inventory import views

urlpatterns = [
    path('', views.dashboard, name='home'),
    path('admin/', admin.site.urls),
    path('signup/', views.signup, name='signup'),
    path(
        'login/',
        LoginView.as_view(
            authentication_form=EmailAuthenticationForm,
            next_page='dashboard',
            template_name='registration/login.html',
        ),
        name='login',
    ),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('products/', views.product_list, name='product_list'),
    path('products/new/', views.product_create, name='product_create'),
    path(
        'settings/',
        views.organization_settings,
        name='organization_settings',
    ),
    path(
        'products/<int:product_id>/edit/',
        views.product_edit,
        name='product_edit',
    ),
    path(
        'products/<int:product_id>/delete/',
        views.product_delete,
        name='product_delete',
    ),
]
