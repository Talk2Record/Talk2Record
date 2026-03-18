from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from talk2record.users.serializers import LogoutSerializer


class LogoutView(APIView):
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
