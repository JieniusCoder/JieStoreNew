from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('items/', views.item_list, name='storefront'),
    # path('cart/', views.cart_view, name='cart_view'),
    path('checkout/', views.checkout, name='checkout'), 
]

# handling images
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)