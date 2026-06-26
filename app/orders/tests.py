import pytest
import json
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth.models import User
from django.db.models import Max
from .models import Category, Product, PromoCode, Order


@pytest.fixture
def user():
    return User.objects.create_user(username="testuser", password="testpass")


@pytest.fixture
def category():
    return Category.objects.create(name="Electronics")


@pytest.fixture
def category2():
    return Category.objects.create(name="Clothing")


@pytest.fixture
def product(category):
    return Product.objects.create(name="Laptop", price=Decimal("100.00"), category=category)


@pytest.fixture
def product_excluded(category):
    return Product.objects.create(
        name="Gift Card", price=Decimal("50.00"), category=category, excluded_from_discounts=True
    )


@pytest.fixture
def product_other(category2):
    return Product.objects.create(name="T-Shirt", price=Decimal("30.00"), category=category2)


@pytest.fixture
def promo_code(category):
    now = timezone.now()
    return PromoCode.objects.create(
        code="SUMMER2025",
        discount_percent=Decimal("10.00"),
        valid_from=now - timedelta(days=1),
        valid_until=now + timedelta(days=7),
        max_uses=10,
        applicable_category=category,
    )


@pytest.mark.django_db
class TestOrderCreateAPI:
    def test_success(self, client, user, product):
        payload = {
            "user_id": user.id,
            "goods": [{"good_id": product.id, "quantity": 2}],
        }
        response = client.post("/api/orders/", json.dumps(payload), content_type="application/json")
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["user_id"] == user.id
        assert Decimal(data["price"]) == Decimal("200.00")
        assert Decimal(data["total"]) == Decimal("200.00")
        assert Decimal(data["discount"]) == Decimal("0.00")
        assert len(data["goods"]) == 1
        assert Decimal(data["goods"][0]["price"]) == Decimal("100.00")

    def test_with_promo(self, client, user, product, promo_code):
        payload = {
            "user_id": user.id,
            "goods": [{"good_id": product.id, "quantity": 2}],
            "promo_code": "SUMMER2025",
        }
        response = client.post("/api/orders/", json.dumps(payload), content_type="application/json")
        
        assert response.status_code == 201
        data = response.json()
        
        assert Decimal(data["discount"]) == Decimal("0.10")
        assert Decimal(data["total"]) == Decimal("180.00")
        assert Decimal(data["goods"][0]["discount"]) == Decimal("0.10")
        assert Decimal(data["goods"][0]["total"]) == Decimal("180.00")
        assert Order.objects.filter(user=user, promo_code=promo_code).exists()

    def test_with_excluded_product(self, client, user, product, product_excluded, promo_code):
        payload = {
            "user_id": user.id,
            "goods": [
                {"good_id": product.id, "quantity": 1},
                {"good_id": product_excluded.id, "quantity": 1},
            ],
            "promo_code": "SUMMER2025",
        }
        response = client.post("/api/orders/", json.dumps(payload), content_type="application/json")
        
        assert response.status_code == 201
        data = response.json()
        
        assert Decimal(data["price"]) == Decimal("150.00")
        assert Decimal(data["total"]) == Decimal("140.00")
        
        items = {item["good_id"]: item for item in data["goods"]}
        assert Decimal(items[product.id]["discount"]) == Decimal("0.10")
        assert Decimal(items[product_excluded.id]["discount"]) == Decimal("0.00")

    def test_wrong_category(self, client, user, product_other, promo_code):
        payload = {
            "user_id": user.id,
            "goods": [{"good_id": product_other.id, "quantity": 1}],
            "promo_code": "SUMMER2025",
        }
        response = client.post("/api/orders/", json.dumps(payload), content_type="application/json")
        
        assert response.status_code == 201
        assert Decimal(response.json()["discount"]) == Decimal("0.00")

    def test_promo_not_found(self, client, user, product):
        payload = {
            "user_id": user.id,
            "goods": [{"good_id": product.id, "quantity": 1}],
            "promo_code": "INVALID",
        }
        response = client.post("/api/orders/", json.dumps(payload), content_type="application/json")
        
        assert response.status_code == 400
        assert "promo_code" in response.json()

    def test_promo_expired(self, client, user, product):
        now = timezone.now()
        PromoCode.objects.create(
            code="OLD",
            discount_percent=Decimal("10.00"),
            valid_from=now - timedelta(days=10),
            valid_until=now - timedelta(days=1),
            max_uses=10,
        )
        
        payload = {
            "user_id": user.id,
            "goods": [{"good_id": product.id, "quantity": 1}],
            "promo_code": "OLD",
        }
        response = client.post("/api/orders/", json.dumps(payload), content_type="application/json")
        
        assert response.status_code == 400
        assert "promo_code" in response.json()

    def test_promo_limit_reached(self, client, user, product, promo_code):
        for i in range(promo_code.max_uses):
            u = User.objects.create_user(username=f"user_{i}", password="test")
            payload = {
                "user_id": u.id,
                "goods": [{"good_id": product.id, "quantity": 1}],
                "promo_code": "SUMMER2025",
            }
            response = client.post("/api/orders/", json.dumps(payload), content_type="application/json")
            assert response.status_code == 201

        payload = {
            "user_id": user.id,
            "goods": [{"good_id": product.id, "quantity": 1}],
            "promo_code": "SUMMER2025",
        }
        response = client.post("/api/orders/", json.dumps(payload), content_type="application/json")
        
        assert response.status_code == 400
        assert "promo_code" in response.json()

    def test_promo_already_used(self, client, user, product, promo_code):
        payload = {
            "user_id": user.id,
            "goods": [{"good_id": product.id, "quantity": 1}],
            "promo_code": "SUMMER2025",
        }
        
        response = client.post("/api/orders/", json.dumps(payload), content_type="application/json")
        assert response.status_code == 201
        
        response = client.post("/api/orders/", json.dumps(payload), content_type="application/json")
        assert response.status_code == 400
        assert "promo_code" in response.json()

    def test_user_not_found(self, client, product):
        max_id = User.objects.aggregate(Max("id"))["id__max"] or 0
        nonexistent_user_id = max_id + 1000
        
        payload = {
            "user_id": nonexistent_user_id,
            "goods": [{"good_id": product.id, "quantity": 1}],
        }
        response = client.post("/api/orders/", json.dumps(payload), content_type="application/json")
        
        assert response.status_code == 400
        assert "user_id" in response.json()

    def test_product_not_found(self, client, user):
        max_id = Product.objects.aggregate(Max("id"))["id__max"] or 0
        nonexistent_good_id = max_id + 1000
        
        payload = {
            "user_id": user.id,
            "goods": [{"good_id": nonexistent_good_id, "quantity": 1}],
        }
        response = client.post("/api/orders/", json.dumps(payload), content_type="application/json")
        
        assert response.status_code == 400
        errors = response.json()
        assert "goods" in errors or "good_id" in errors

    def test_duplicate_products(self, client, user, product):
        payload = {
            "user_id": user.id,
            "goods": [
                {"good_id": product.id, "quantity": 1},
                {"good_id": product.id, "quantity": 2},
            ],
        }
        response = client.post("/api/orders/", json.dumps(payload), content_type="application/json")
        
        assert response.status_code == 400
