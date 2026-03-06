from django.contrib.auth import get_user_model
from dj_rest_auth.registration.serializers import RegisterSerializer
from dj_rest_auth.serializers import LoginSerializer, UserDetailsSerializer

User = get_user_model()


class CustomRegisterSerializer(RegisterSerializer):
    username = None  # Remove username field

    def get_cleaned_data(self):
        return {
            "email": self.validated_data.get("email", ""),
            "password1": self.validated_data.get("password1", ""),
        }


class CustomLoginSerializer(LoginSerializer):
    username = None  # Email-only login


class CustomUserDetailsSerializer(UserDetailsSerializer):
    class Meta(UserDetailsSerializer.Meta):
        model = User
        fields = ("pk", "email", "date_joined", "is_active")
        read_only_fields = ("pk", "date_joined", "is_active")
