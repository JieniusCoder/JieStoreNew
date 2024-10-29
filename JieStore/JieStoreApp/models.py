from django.db import models

# Create your models here.
class User(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50)
    email = models.EmailField(max_length=50, unique=True) 
    password = models.CharField(max_length=128)

    @staticmethod
    def get_all_users():
        return User.objects.all()
    
class Category(models.Model):
    name = models.CharField(max_length=50)

    @staticmethod
    def get_all_categories():
        return Category.objects.all()

class Item(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50)
    description = models.CharField(max_length=500)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='itemImages/', default='images/default.png')

    @staticmethod
    def get_all_items():
        return Item.objects.all()



class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    payment_status = models.CharField(max_length=20, default='pending')  
    stripe_payment_id = models.CharField(max_length=255, blank=True, null=True) 

    @staticmethod
    def get_orders_by_customer(user):
        return Order.objects.filter(user=user)

class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
