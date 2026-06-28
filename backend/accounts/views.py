"""Inscription et profil utilisateur. Le login/refresh = JWT (simplejwt)."""
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request: Request):
        username = (request.data.get("username") or "").strip()
        password = request.data.get("password") or ""
        email = (request.data.get("email") or "").strip()

        if not username or not password:
            return Response(
                {"detail": "username et password sont requis."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if User.objects.filter(username=username).exists():
            return Response(
                {"detail": "Cet utilisateur existe déjà."},
                status=status.HTTP_409_CONFLICT,
            )

        user = User.objects.create_user(
            username=username, password=password, email=email
        )
        return Response(
            {"id": user.id, "username": user.username, "email": user.email},
            status=status.HTTP_201_CREATED,
        )


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request):
        u = request.user
        return Response({"id": u.id, "username": u.username, "email": u.email})
