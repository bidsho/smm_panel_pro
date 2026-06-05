import requests  # 💡 Added missing import required for the JAP API call
from django.contrib import admin, messages
from django.conf import settings
from django.db.models import Sum
from django.contrib.auth import get_user_model
from .models import Service, Order, SocialAccount, AccountOrder
from .utils import get_jap_balance

# Get the User model dynamically
User = get_user_model()


def get_dashboard_metrics():
    """
    Helper function to calculate common dashboard metrics consistently 
    across all custom admin panels.
    """
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
    raw_id_fields = ('user', 'service')  # Prevents performance bottleneck over thousands of rows

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context.update(get_dashboard_metrics())
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('provider_service_id', 'name', 'category', 'cost_per_1k_usd', 'is_active')
    list_editable = ('is_active',)
    list_filter = ('is_active', 'category')
    search_fields = ('name', 'category', 'provider_service_id')
    actions = ['sync_from_jap_api']

    def sync_from_jap_api(self, request, queryset):
        # Fetch key securely from settings (hydrated by .env)
        api_key = getattr(settings, 'JAP_API_KEY', None)
        
        if not api_key:
            self.message_user(
                request, 
                "Sync failed: JAP_API_KEY is missing from your .env file or settings.", 
                level=messages.ERROR
            )
            return

        # Perform the remote request safely
        try:
            response = requests.post(
                'https://justanotherpanel.com/api/v2', 
                data={'key': api_key, 'action': 'services'},
                timeout=15
            )
            response.raise_for_status()
            services = response.json()
        except requests.exceptions.RequestException as e:
            self.message_user(request, f"Network or API Error: {e}", level=messages.ERROR)
            return
        except ValueError:
            self.message_user(request, "Failed to decode JSON data from provider.", level=messages.ERROR)
            return

        # Check if API returned an explicit error object (e.g., {"error": "Bad API Key"})
        if isinstance(services, dict) and 'error' in services:
            self.message_user(request, f"API Error Code: {services['error']}", level=messages.ERROR)
            return

        created, updated = 0, 0

        # Run loop to update local items or insert new ones
        for svc in services:
            if not isinstance(svc, dict) or 'service' not in svc:
                continue  # Skip unexpected lines safely
                
            obj, was_created = Service.objects.update_or_create(
                provider_service_id=svc['service'],
                defaults={
                    'name': svc.get('name', ''),
                    'category': svc.get('category', ''),
                    'cost_per_1k_usd': svc.get('rate', 0.00),
                    # Note: 'is_active' is left out so syncing does not reset local updates
                }
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.message_user(
            request, 
            f"Sync complete! {created} new services loaded, {updated} updated.", 
            level=messages.SUCCESS
        )

    sync_from_jap_api.short_description = "🔄 Sync all available services from JAP API"

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context.update(get_dashboard_metrics())
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(SocialAccount)
class SocialAccountAdmin(admin.ModelAdmin):
    list_display = ('id', 'platform', 'username', 'price', 'status', 'created_at')
    list_filter = ('platform', 'status', 'created_at')
    search_fields = ('username', 'email', 'description')
    list_editable = ('status',)
    raw_id_fields = ('uploaded_by', 'bought_by')

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context.update(get_dashboard_metrics())
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(AccountOrder)
class AccountOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'account', 'amount_paid', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'account__username', 'id')
    raw_id_fields = ('user', 'account')

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context.update(get_dashboard_metrics())
        return super().changelist_view(request, extra_context=extra_context)