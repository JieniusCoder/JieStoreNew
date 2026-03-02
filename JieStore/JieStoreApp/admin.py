from django.contrib import admin
from .models import User, Item, Category, Order, Cart, CartItem, UserCart, UserCartItem

admin.site.register(User)
admin.site.register(Item)
admin.site.register(Category)
admin.site.register(Order)
admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(UserCart)
admin.site.register(UserCartItem)