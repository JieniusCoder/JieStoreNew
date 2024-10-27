from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('items/', views.item_list, name='item_list'),
    path('items/<int:item_id>/', views.item_detail, name='item_detail'),
    # path('cart/', views.cart_view, name='cart_view'),
    path('checkout/', views.checkout, name='checkout'), 
]