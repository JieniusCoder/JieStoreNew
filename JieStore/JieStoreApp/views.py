from django.shortcuts import render, get_object_or_404, redirect
from .models import Item, Cart, Order
from django.http import HttpResponse

# Create your views here.




def home(request):
    return render(request, 'home.html')

def item_list(request):
    items = Item.objects.all() 
    return render(request, 'item_list.html', {'items': items})  


def item_detail(request, item_id):
    item = get_object_or_404(Item, id=item_id)  
    return render(request, 'item_detail.html', {'item': item})  


def add_to_cart(request, item_id):
    item = get_object_or_404(Item, id=item_id) 
   
    cart, created = Cart.objects.get_or_create(user=request.user)
    
    # Add the item to the cart (you'll need to implement CartItem model for this)
    cart.items.add(item)  # Assuming a ManyToMany relationship between Cart and Item
    return redirect('item_list')  # Redirect to the item list page

# View for checkout process
def checkout(request):
    cart = get_object_or_404(Cart, user=request.user)  # Get the user's cart
    
    if request.method == 'POST':
        # Here you would integrate with Stripe to process the payment
        # For example:
        # stripe.api_key = "your_api_key"
        # charge = stripe.Charge.create(
        #     amount=calculate_total(cart),  # Total amount from cart
        #     currency='usd',
        #     description='Charge for order',
        #     source=request.POST['stripeToken'],  # Get token from Stripe.js
        # )
        
        # Create an order after successful payment
        order = Order(user=request.user)
        order.save()  # Save the order
        for item in cart.items.all():  # Assuming items are related to Cart
            order.item.add(item)  # Add items to the order
        
        cart.items.clear()  # Clear the cart after checkout
        return redirect('item_list')  # Redirect to the item list after successful checkout
    
    return render(request, 'checkout.html', {'cart': cart})  # Render checkout template