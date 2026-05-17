#!/usr/bin/env python
"""Run with: python manage.py shell < test_rate_limit.py"""

import requests
import time
from django.core.cache import cache

BASE_URL = "http://127.0.0.1:8000"

print("=" * 50)
print("RATE LIMITING TEST")
print("=" * 50)

# ==================== ENTER YOUR CREDENTIALS HERE ====================
EMAIL = "admin@bizsmart.com"      # <-- CHANGE THIS
PASSWORD = "123456"         # <-- CHANGE THIS
# ====================================================================

# Clear cache
cache.delete_pattern('*throttle*')
print("✅ Cache cleared")

# ==================== TEST 1: Authenticated User ====================
print("\n1. Testing authenticated rate limit (200/minute)...")

# Login to get token
login_resp = requests.post(f"{BASE_URL}/api/v1/auth/login/", json={
    'email': EMAIL,
    'password': PASSWORD
})

if login_resp.status_code != 200:
    print(f"❌ Login failed: {login_resp.status_code}")
    print(f"Response: {login_resp.text}")
    print("\nMake sure you have a user with this email and password!")
    exit()

token = login_resp.json()['access']
headers = {'Authorization': f'Bearer {token}'}
print(f"✅ Authenticated as: {EMAIL}")

# Make requests until rate limited
success = 0
rate_limited_at = None

for i in range(1, 250):
    resp = requests.get(f"{BASE_URL}/api/v1/auth/profile/", headers=headers)
    
    if resp.status_code == 200:
        success += 1
    elif resp.status_code == 429:
        rate_limited_at = i
        print(f"\n❗ Rate limited at request {i}")
        print(f"   Message: {resp.json().get('detail', 'Too many requests')}")
        break
    
    if i % 50 == 0:
        print(f"   Made {i} requests, {success} successful")

if rate_limited_at:
    print(f"\n📊 Authenticated Results: {success} successful, rate limited at request {rate_limited_at}")
else:
    print(f"\n📊 Authenticated Results: {success} successful, never rate limited")

# ==================== TEST 2: Anonymous User ====================
print("\n2. Testing anonymous rate limit (20/minute)...")

# Clear cache for fresh test
cache.delete_pattern('*throttle*')

success = 0
rate_limited_at = None

for i in range(1, 50):
    resp = requests.get(f"{BASE_URL}/api/v1/auth/login/")  # Public endpoint
    
    if resp.status_code == 200:
        success += 1
    elif resp.status_code == 429:
        rate_limited_at = i
        print(f"\n❗ Rate limited at request {i}")
        print(f"   Message: {resp.json().get('detail', 'Too many requests')}")
        break
    
    if i % 10 == 0:
        print(f"   Made {i} requests, {success} successful")

if rate_limited_at:
    print(f"\n📊 Anonymous Results: {success} successful, rate limited at request {rate_limited_at}")
else:
    print(f"\n📊 Anonymous Results: {success} successful, never rate limited")

# ==================== TEST 3: Login Rate Limit ====================
print("\n3. Testing login rate limit (5/hour)...")

# Clear cache
cache.delete_pattern('*throttle*')

for i in range(1, 10):
    resp = requests.post(f"{BASE_URL}/api/v1/auth/login/", json={
        'email': 'wrong@email.com',
        'password': 'wrongpassword'
    })
    
    if resp.status_code == 401:
        print(f"   Attempt {i}: 401 (Invalid credentials - expected)")
    elif resp.status_code == 429:
        print(f"\n❗ Attempt {i}: RATE LIMITED! - {resp.json().get('detail', 'Too many requests')}")
        break
    else:
        print(f"   Attempt {i}: {resp.status_code} (Unexpected)")

print("\n" + "=" * 50)
print("✅ RATE LIMITING TEST COMPLETE")
print("=" * 50)