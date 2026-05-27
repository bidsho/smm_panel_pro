from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from decimal import Decimal
from .models import Service, Order
from wallets.models import Wallet, Transaction

import requests
from django.db import transaction
from wallets.models import Wallet, Transaction as WalletTransaction

def place_jap_order(order):
    api_key = "0cd24c736491d4f55d2cdfdff0563481"
    api_url = "https://justanotherpanel.com/api/v2"
    
    payload = {
        'key': api_key,
        'action': 'add',
        'service': order.service.provider_service_id,
        'link': order.link,
        'quantity': order.quantity
    }
    
    try:
        response = requests.post(api_url, data=payload)
        res_data = response.json()
        
        if 'order' in res_data:
            order.api_order_id = res_data['order']
            order.status = 'Pending'
            order.save()
            return True
        return False
    except:
        return False

@login_required
@transaction.atomic # Move atomic to the top for safety
def new_order(request):
    services = Service.objects.filter(is_active=True)
    
    if request.method == 'POST':
        service_id = request.POST.get('service')
        quantity = int(request.POST.get('quantity'))
        link = request.POST.get('link')
        
        service = Service.objects.get(id=service_id)
        total_price = service.get_naira_price() * (Decimal(quantity) / Decimal('1000'))
        
        # Use select_for_update() to make sure we have the latest balance from DB
        from wallets.models import Wallet
        wallet = Wallet.objects.select_for_update().get(user=request.user)
        
        if wallet.balance >= total_price:
            # 1. Deduct Money
            wallet.balance -= total_price
            wallet.save()
            
            # 2. Create Order
            order = Order.objects.create(
                user=request.user,
                service=service,
                link=link,
                quantity=quantity,
                total_price=total_price,
                status='Pending'
            )
            
            # 3. Send to JAP
            success = place_jap_order(order)
            
            if success:
                messages.success(request, f"Order successful! ₦{total_price} deducted.")
                return redirect('dashboard')
            else:
                # API FAILED: Refund
                wallet.balance += total_price
                wallet.save()
                order.status = 'Cancelled'
                order.save()
                messages.error(request, "JAP API error. Money has been refunded to your wallet.")
                return redirect('new_order')
        else:
            messages.error(request, "Insufficient balance in your wallet!")
            
    return render(request, 'orders/new_order.html', {'services': services})


@login_required
def order_history(request):
    # Get only the orders belonging to the logged-in user
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'orders/order_history.html', {'orders': orders})    