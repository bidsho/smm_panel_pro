from django.urls import path
from . import views

urlpatterns = [
    path('new/', views.new_order, name='new_order'),
    # We will add order_logs here later
    path('history/', views.order_history, name='order_history'), # Add this
]