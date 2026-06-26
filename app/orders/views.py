from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED
from .serializers import OrderCreateSerializer, OrderSerializer
from .services import OrderService


class OrderCreateView(APIView):
    def post(self, request):
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order = OrderService.create_order(
            user=serializer.validated_data["user_id"],
            goods=serializer.validated_data["goods"],
            promo_code=serializer.validated_data.get("_promo_code"),
        )

        return Response(
            OrderSerializer(order).data,
            status=HTTP_201_CREATED
        )
