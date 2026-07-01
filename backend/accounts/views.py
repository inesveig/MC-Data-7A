"""Inscription et profil utilisateur. Le login/refresh = JWT (simplejwt)."""
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import RegisterSerializer


def _first_error(errors: dict) -> str:
    for messages in errors.values():
        if messages:
            return str(messages[0])
    return "Champs invalides."


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request: Request):
        username = (request.data.get("username") or "").strip()
        if username and User.objects.filter(username=username).exists():
            return Response(
                {"detail": "Cet utilisateur existe déjà."},
                status=status.HTTP_409_CONFLICT,
            )

        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"detail": _first_error(serializer.errors)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = serializer.save()
        return Response(
            {"id": user.id, "username": user.username, "email": user.email},
            status=status.HTTP_201_CREATED,
        )


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request):
        u = request.user
        return Response({"id": u.id, "username": u.username, "email": u.email})
