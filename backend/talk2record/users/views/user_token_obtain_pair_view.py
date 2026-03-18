from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView

from talk2record.users.serializers import UserTokenObtainPairSerializer


class UserTokenObtainPairView(TokenObtainPairView):
    permission_classes = (AllowAny,)
    serializer_class = UserTokenObtainPairSerializer
