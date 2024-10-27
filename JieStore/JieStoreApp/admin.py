from django.contrib import admin
from .models import User, Item, Category, Order, Cart, CartItem

admin.site.register(User)
admin.site.register(Item)
admin.site.register(Category)
admin.site.register(Order)
admin.site.register(Cart)
admin.site.register(CartItem)