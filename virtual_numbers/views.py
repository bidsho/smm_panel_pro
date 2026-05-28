from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Country, NumberService, PurchasedNumber
from . import fivesim


@login_required
def number_list(request):
    countries = Country.objects.filter(active=True)
    selected_country = request.GET.get('country')
    services = []

    if selected_country:
        services = NumberService.objects.filter(
            country__code=selected_country,
            active=True
        )

    return render(request, 'virtual_numbers/number_list.html', {
        'countries': countries,
        'services': services,
        'selected_country': selected_country,
    })


@login_required
def buy_number(request, service_id):
    service = get_object_or_404(NumberService, pk=service_id, active=True)
    wallet = request.user.wallet

    if request.method == 'POST':
        if wallet.balance < service.price:
            messages.error(request, 'Insufficient wallet balance.')
            return redirect('virtual_numbers:number_list')

        result = fivesim.buy_number(
            country=service.country.code,
            service=service.service
        )

        if 'id' not in result:
            messages.error(request, f'Failed: {result.get("message", "Unknown error")}')
            return redirect('virtual_numbers:number_list')

        wallet.balance -= service.price
        wallet.save()

        purchased = PurchasedNumber.objects.create(
            user=request.user,
            country=service.country,
            service=service.service,
            phone_number=result['phone'],
            provider=service.provider,
            provider_order_id=str(result['id']),
            price=service.price,
            status='pending'
        )

        messages.success(request, f'Number {result["phone"]} assigned!')
        return redirect('virtual_numbers:number_detail', pk=purchased.pk)

    return render(request, 'virtual_numbers/buy_number.html', {
        'service': service,
        'wallet': wallet,
    })


@login_required
def number_detail(request, pk):
    number = get_object_or_404(PurchasedNumber, pk=pk, user=request.user)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'check':
            result = fivesim.check_order(number.provider_order_id)
            sms_list = result.get('sms', [])
            if sms_list:
                number.otp_code = sms_list[0]['code']
                number.status = 'received'
                number.save()
                messages.success(request, f'OTP received: {number.otp_code}')
            else:
                messages.info(request, 'No SMS yet. Please wait and try again.')

        elif action == 'finish':
            fivesim.finish_order(number.provider_order_id)
            number.status = 'completed'
            number.save()
            messages.success(request, 'Order completed.')

        elif action == 'cancel':
            fivesim.cancel_order(number.provider_order_id)
            number.status = 'cancelled'
            number.save()
            wallet = request.user.wallet
            wallet.balance += number.price
            wallet.save()
            messages.success(request, 'Order cancelled and refunded.')

        return redirect('virtual_numbers:number_detail', pk=pk)

    return render(request, 'virtual_numbers/number_detail.html', {'number': number})


@login_required
def my_numbers(request):
    numbers = PurchasedNumber.objects.filter(user=request.user)
    return render(request, 'virtual_numbers/my_numbers.html', {'numbers': numbers})