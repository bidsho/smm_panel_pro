from django.contrib import admin
from django.db.models import Sum
from django.contrib.auth import get_user_model
from .models import Service, Order
from .utils import get_jap_balance

# Get the User model dynamically
User = get_user_model()

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'service', 'total_price', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'id', 'api_order_id')

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        
        # Pull data for the dashboard
        extra_context['jap_balance'] = get_jap_balance()
        extra_context['total_sales'] = Order.objects.filter(status='Completed').aggregate(Sum('total_price'))['total_price__sum'] or 0
        extra_context['total_users'] = User.objects.count() 
        
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('provider_service_id', 'name', 'category', 'cost_per_1k_usd', 'is_active')
    list_editable = ('is_active',)
    list_filter = ('is_active', 'category')
    search_fields = ('name', 'category', 'provider_service_id')

    # ADDED THIS: Now the balance will also show when you look at the Services list
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        
        extra_context['jap_balance'] = get_jap_balance()
        extra_context['total_sales'] = Order.objects.filter(status='Completed').aggregate(Sum('total_price'))['total_price__sum'] or 0
        extra_context['total_users'] = User.objects.count()
        
        return super().changelist_view(request, extra_context=extra_context)