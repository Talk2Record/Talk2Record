from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from talk2record.users.serializers import RegisterUserSerializer
from talk2record.users.serializers import UserSerializer


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterUserSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        user_serializer = UserSerializer(user, context={"request": request})
        return Response({"user": user_serializer.data}, status=status.HTTP_201_CREATED)
