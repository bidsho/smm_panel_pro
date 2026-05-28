import requests
from django.conf import settings

BASE_URL = "https://5sim.net/v1"
USER_URL = "https://5sim.net/v1/user"

HEADERS = {
    "Authorization": f"Bearer {settings.FIVESIM_API_KEY}",
    "Accept": "application/json",
}

PROFIT_PERCENT = 30  # Your profit percentage
USD_TO_NGN = 1600   # Exchange rate


def get_balance():
    response = requests.get(f"{USER_URL}/profile", headers=HEADERS)
    return response.json()


def get_countries():
    response = requests.get(f"{BASE_URL}/guest/countries", headers=HEADERS)
    return response.json()


def get_products(country, service):
    url = f"{BASE_URL}/guest/products/{country}/any"
    response = requests.get(url, headers=HEADERS)
    return response.json()


def calculate_price(usd_price):
    """Convert USD to NGN and add profit margin"""
    ngn_price = float(usd_price) * USD_TO_NGN
    final_price = ngn_price * (1 + PROFIT_PERCENT / 100)
    return round(final_price, 2)


def buy_number(country, service):
    url = f"{USER_URL}/buy/activation/{country}/any/{service}"
    response = requests.get(url, headers=HEADERS)
    return response.json()


def check_order(order_id):
    response = requests.get(f"{USER_URL}/check/{order_id}", headers=HEADERS)
    return response.json()


def finish_order(order_id):
    response = requests.get(f"{USER_URL}/finish/{order_id}", headers=HEADERS)
    return response.json()


def cancel_order(order_id):
    response = requests.get(f"{USER_URL}/cancel/{order_id}", headers=HEADERS)
    return response.json()