from decimal import Decimal
from django.db import models
from django.conf import settings

# orders/models.py

class Service(models.Model):
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=255)
    # The raw price JAP charges you in USD (e.g., 0.8500)
    cost_per_1k_usd = models.DecimalField(max_digits=10, decimal_places=4) 
    min_qty = models.IntegerField()
    max_qty = models.IntegerField()
    is_active = models.BooleanField(default=True)
    
    # This is the Service ID from JAP's API (e.g., 102)
    provider_service_id = models.IntegerField(unique=True, null=True, blank=True)
    
    def __str__(self):
        return f"{self.name} (ID: {self.provider_service_id})"

    def get_naira_price(self):
        """
        Calculates the price you show to your users in Naira.
        Adjust the exchange_rate and profit_multiplier as needed.
        """
        exchange_rate = Decimal('1550') # Current rate
        profit_multiplier = Decimal('1.2') # 50% profit margin
        return (self.cost_per_1k_usd * exchange_rate * profit_multiplier).quantize(Decimal('0.01'))

class Order(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Processing', 'Processing'),
        ('InProgress', 'In Progress'),
        ('Completed', 'Completed'),
        ('Partial', 'Partial'),
        ('Cancelled', 'Cancelled'),
        ('Refunded', 'Refunded'),
    )
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    link = models.URLField(max_length=500) # Increased length for long social links
    quantity = models.IntegerField()
    total_price = models.DecimalField(max_digits=12, decimal_places=2) # What user paid in Naira
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    
    # The reference ID returned by JAP after a successful API call
    api_order_id = models.CharField(max_length=100, null=True, blank=True)
    
    # Optional: track how many items are left to deliver
    remains = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.id} - {self.service.name} for {self.user.username}"