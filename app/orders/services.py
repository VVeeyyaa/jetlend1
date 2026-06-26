from decimal import Decimal
from django.db import transaction
from rest_framework.exceptions import ValidationError
from .models import Order, OrderItem, PromoCode


class OrderService:
    @staticmethod
    @transaction.atomic
    def create_order(user, goods, promo_code=None):
        if promo_code:
            promo_code = PromoCode.objects.select_for_update().get(pk=promo_code.pk)
            if Order.objects.filter(promo_code=promo_code).count() >= promo_code.max_uses:
                raise ValidationError({"promo_code": ["Promo code usage limit reached."]})

        discount_rate = promo_code.discount_percent / 100 if promo_code else Decimal("0")

        order_items_data = []
        total_price = Decimal("0")
        total_discount = Decimal("0")

        for item in goods:
            product = item["good_id"]
            quantity = item["quantity"]
            line_price = product.price * quantity

            is_eligible = bool(
                promo_code
                and not product.excluded_from_discounts
                and promo_code.applicable_category_id in (None, product.category_id)
            )

            line_discount = (
                (line_price * discount_rate).quantize(Decimal("0.01")) 
                if is_eligible else Decimal("0")
            )

            order_items_data.append({
                "product": product,
                "quantity": quantity,
                "price": product.price,
                "discount": discount_rate if is_eligible else Decimal("0"),
                "total": line_price - line_discount,
            })

            total_price += line_price
            total_discount += line_discount

        overall_discount = (
            (total_discount / total_price).quantize(Decimal("0.01"))
            if total_price else Decimal("0")
        )

        order = Order.objects.create(
            user=user,
            promo_code=promo_code,
            price=total_price,
            discount=overall_discount,
            total=total_price - total_discount,
        )

        OrderItem.objects.bulk_create([
            OrderItem(order=order, **data) for data in order_items_data
        ])

        return order
