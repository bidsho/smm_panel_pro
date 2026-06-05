import requests  
from django.contrib import admin, messages
from django.conf import settings
from django.db.models import Sum
from django.contrib.auth import get_user_model
from django.shortcuts import redirect
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
    raw_id_fields = ('user', 'service')

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
    
    actions = ['bulk_activate_services', 'bulk_deactivate_services']
    change_list_template = "admin/service_changelist.html"

    def bulk_activate_services(self, request, queryset):
        """Action to instantly set selected services to Active."""
        updated_count = queryset.update(is_active=True)
        self.message_user(request, f"🟢 Successfully activated {updated_count} services for your users!", level=messages.SUCCESS)
    bulk_activate_services.short_description = "🟢 Mark selected services as ACTIVE"

    def bulk_deactivate_services(self, request, queryset):
        """Action to instantly set selected services to Inactive."""
        updated_count = queryset.update(is_active=False)
        self.message_user(request, f"🔴 Successfully hid {updated_count} services from the user end.", level=messages.SUCCESS)
    bulk_deactivate_services.short_description = "🔴 Mark selected services as INACTIVE"

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('sync-all/', self.admin_site.admin_view(self.sync_all_from_jap_api), name='service_sync_all'),
        ]
        return custom_urls + urls

    def sync_all_from_jap_api(self, request):
        api_key = getattr(settings, 'JAP_API_KEY', None)
        
        if not api_key:
            self.message_user(
                request, 
                "Sync failed: JAP_API_KEY is missing from your .env file or settings.", 
                level=messages.ERROR
            )
            return redirect("..")

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
            return redirect("..")
        except ValueError:
            self.message_user(request, "Failed to decode JSON data from provider.", level=messages.ERROR)
            return redirect("..")

        if isinstance(services, dict) and 'error' in services:
            self.message_user(request, f"API Error Code: {services['error']}", level=messages.ERROR)
            return redirect("..")

        created, updated = 0, 0

        # 💡 Helper function moved to the top of the processing block to protect all logic down-stream
        def safe_int(val):
            try:
                return int(float(val))
            except (ValueError, TypeError):
                return 0

        for svc in services:
            if not isinstance(svc, dict) or 'service' not in svc:
                continue  
                
            # 💡 FIX: Cast the lookup ID to an integer immediately BEFORE running the database query!
            target_id = safe_int(svc.get('service'))
            if target_id == 0:
                continue

            existing_service = Service.objects.filter(provider_service_id=target_id).first()
            
            defaults_dict = {
                'name': svc.get('name', ''),
                'category': svc.get('category', ''),
                'cost_per_1k_usd': svc.get('rate', 0.00),
                'min_qty': safe_int(svc.get('min', 0)),  
                'max_qty': safe_int(svc.get('max', 0)),  
            }
            
            # If it's a completely brand new service, keep it hidden by default
            if not existing_service:
                defaults_dict['is_active'] = False

            obj, was_created = Service.objects.update_or_create(
                provider_service_id=target_id,
                defaults=defaults_dict
            )
            
            if was_created:
                created += 1
            else:
                updated += 1

        self.message_user(
            request, 
            f"Sync complete! Processed all social networks. New services added: {created}. Existing services updated: {updated}.", 
            level=messages.SUCCESS
        )
        return redirect("..")

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