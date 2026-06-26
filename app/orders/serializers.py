from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Order, OrderItem, Product, PromoCode


class OrderItemCreateSerializer(serializers.Serializer):
    good_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all()
    )
    quantity = serializers.IntegerField(min_value=1)


class OrderCreateSerializer(serializers.Serializer):
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all()
    )
    goods = OrderItemCreateSerializer(many=True)
    promo_code = serializers.CharField(
        max_length=50, required=False, allow_blank=True
    )


    def validate(self, data):
        self._validate_goods(data.get("goods", []))
        data["_promo_code"] = self._validate_promo_code(data.get("promo_code"), data["user_id"])

        return data
    
    def _validate_goods(self, goods):
        good_ids = [item["good_id"].id for item in goods]
        if len(good_ids) != len(set(good_ids)):
            raise serializers.ValidationError({
                "goods": ["Duplicate products are not allowed."]
            })

    def _validate_promo_code(self, promo_code, user):
        if not promo_code:
            return

        try:
            promo_code = PromoCode.objects.get(code__iexact=promo_code)
        except PromoCode.DoesNotExist:
            raise serializers.ValidationError({"promo_code": "Promo code not found."})

        if not promo_code.is_active:
            raise serializers.ValidationError({"promo_code": "Promo code has expired."})

        if Order.objects.filter(user=user, promo_code=promo_code).exists():
            raise serializers.ValidationError({"promo_code": "You have already used this promo code."})

        return promo_code


class OrderItemSerializer(serializers.ModelSerializer):
    good_id = serializers.IntegerField(source="product.id", read_only=True)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    discount = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ["good_id", "quantity", "price", "discount", "total"]


class OrderSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    order_id = serializers.IntegerField(source="id", read_only=True)
    goods = OrderItemSerializer(source="items", many=True, read_only=True)
    price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    discount = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    created_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Order
        fields = ["user_id", "order_id", "goods", "price", "discount", "total", "created_at"]
