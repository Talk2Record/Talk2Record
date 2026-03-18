from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from talk2record.users.serializers import UserSerializer


class CurrentUserView(APIView):
    def get(self, request):
        serializer = UserSerializer(request.user, context={"request": request})
        return Response(status=status.HTTP_200_OK, data=serializer.data)
