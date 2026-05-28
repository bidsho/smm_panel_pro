import requests
from django.conf import settings

BASE_URL = "https://5sim.net/v1"
USER_URL = "https://5sim.net/v1/user"

HEADERS = {
    "Authorization": f"Bearer {settings.FIVESIM_API_KEY}",
    "Accept": "application/json",
}

PROFIT_PERCENT = 30  # Your profit percentage
USD_TO_NGN = 1600    # Exchange rate


def get_balance():
    try:
        response = requests.get(f"{USER_URL}/profile", headers=HEADERS)
        if not response.text:
            return {'error': 'Empty response'}
        return response.json()
    except Exception as e:
        return {'error': str(e)}


def get_countries():
    try:
        response = requests.get(f"{BASE_URL}/guest/countries", headers=HEADERS)
        if not response.text:
            return {}
        return response.json()
    except Exception as e:
        return {}


def get_products(country, service):
    try:
        url = f"{BASE_URL}/guest/products/{country}/any"
        response = requests.get(url, headers=HEADERS)
        if not response.text:
            return {}
        return response.json()
    except Exception as e:
        return {}


def calculate_price(usd_price):
    ngn_price = float(usd_price) * USD_TO_NGN
    final_price = ngn_price * (1 + PROFIT_PERCENT / 100)
    return round(final_price, 2)


def buy_number(country, service):
    try:
        url = f"{USER_URL}/buy/activation/{country}/any/{service}"
        response = requests.get(url, headers=HEADERS)
        if not response.text:
            return {'error': 'Empty response from 5sim API'}
        return response.json()
    except Exception as e:
        return {'error': str(e)}


def check_order(order_id):
    try:
        response = requests.get(f"{USER_URL}/check/{order_id}", headers=HEADERS)
        if not response.text:
            return {'error': 'Empty response'}
        return response.json()
    except Exception as e:
        return {'error': str(e)}


def finish_order(order_id):
    try:
        response = requests.get(f"{USER_URL}/finish/{order_id}", headers=HEADERS)
        if not response.text:
            return {'error': 'Empty response'}
        return response.json()
    except Exception as e:
        return {'error': str(e)}


def cancel_order(order_id):
    try:
        response = requests.get(f"{USER_URL}/cancel/{order_id}", headers=HEADERS)
        if not response.text:
            return {'error': 'Empty response'}
        return response.json()
    except Exception as e:
        return {'error': str(e)}