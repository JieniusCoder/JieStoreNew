from django.shortcuts import render, get_object_or_404, redirect
from .models import Item, Cart, Order, CartItem
from django.http import HttpResponse, JsonResponse

# Create your views here.
def home(request):
    return render(request, 'home.html')

def item_list(request):
    items = Item.objects.all() 
    return render(request, 'item_list.html', {'items': items})  

def cart_view(request):
    cart_item = Cart.objects.all()
    return render(request, 'cart.html', {'cart': cart_item})

def add_to_cart(request, item_id):
    if request.method == 'POST':
        item = request.POST.get('item_id')
        cart = Cart.objects.get(user=request.user)

        cart, created = Cart.objects.get_or_create(user=request.user)

        cart_item = CartItem.objects.create(cart=cart, item=item)
        cart_item.save()

        return JsonResponse({'status': 'success'})


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