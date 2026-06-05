from django.contrib import admin
from django.db.models import Sum
from django.contrib.auth import get_user_model
from .models import Service, Order, SocialAccount, AccountOrder
from .utils import get_jap_balance

# Get the User model dynamically
User = get_user_model()

def get_dashboard_metrics():
    """Helper function to calculate common dashboard metrics consistently across tables."""
    return {
        'jap_balance': get_jap_balance(),
        'total_sales': Order.objects.filter(status='Completed').aggregate(Sum('total_price'))['total_price__sum'] or 0,
        'total_users': User.objects.count()
    }


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'service', 'quantity', 'total_price', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'id', 'api_order_id')
    raw_id_fields = ('user', 'service')  # Prevents long dropdown load times if you get thousands of rows

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context.update(get_dashboard_metrics())
        return super().changelist_view(request, extra_context=extra_context)


# In your ServiceAdmin, add a custom action:

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('provider_service_id', 'name', 'category', 'cost_per_1k_usd', 'is_active')
    list_editable = ('is_active',)
    list_filter = ('is_active', 'category')
    search_fields = ('name', 'category', 'provider_service_id')
    actions = ['sync_from_jap_api']

    def sync_from_jap_api(self, request, queryset):
        import requests
        from django.conf import settings

        response = requests.post('https://justanotherpanel.com/api/v2', data={
            'key': settings.JAP_API_KEY,
            'action': 'services'
        })
        services = response.json()

        created, updated = 0, 0
        for svc in services:
            obj, was_created = Service.objects.update_or_create(
                provider_service_id=svc['service'],
                defaults={
                    'name': svc['name'],
                    'category': svc['category'],
                    'cost_per_1k_usd': svc['rate'],
                    'is_active': False,  # admin manually activates
                }
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.message_user(request, f"Synced: {created} created, {updated} updated.")

    sync_from_jap_api.short_description = "Sync services from JAP API"

@admin.register(SocialAccount)
class SocialAccountAdmin(admin.ModelAdmin):
    list_display = ('id', 'platform', 'username', 'price', 'status', 'created_at')
    list_filter = ('platform', 'status', 'created_at')
    search_fields = ('username', 'email', 'description')
    list_editable = ('status',)
    raw_id_fields = ('uploaded_by', 'bought_by')


@admin.register(AccountOrder)
class AccountOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'account', 'amount_paid', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'account__username', 'id')
    raw_id_fields = ('user', 'account')