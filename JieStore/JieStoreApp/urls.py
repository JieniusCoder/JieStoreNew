from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('items/', views.item_list, name='storefront'),
    path('items/cart/', views.cart_view, name='cart_view'),
    path('items/<int:item_id>/start-add/', views.start_add_to_cart, name='start_add_to_cart'),
    path('items/<int:item_id>/add/', views.add_to_cart, name='add_to_cart'),
    path('items/<int:item_id>/remove/', views.remove_from_cart, name='remove_from_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('checkout/stripe/create-session/', views.stripe_create_checkout_session, name='stripe_create_checkout_session'),
    path('checkout/stripe/webhook/', views.stripe_webhook, name='stripe_webhook'),
    path('checkout/paypal/create-order/', views.paypal_create_order, name='paypal_create_order'),
    path('checkout/paypal/capture-order/', views.paypal_capture_order, name='paypal_capture_order'),
    path('checkout/paypal/redirect/', views.paypal_redirect_checkout, name='paypal_redirect_checkout'),
    path('checkout/paypal/return/', views.paypal_return, name='paypal_return'),
    path('checkout/success/', views.checkout_success, name='checkout_success'),
    path('checkout/cancel/', views.checkout_cancel, name='checkout_cancel'),
    path('login/', views.login, name='login'),
]

# handling images
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)