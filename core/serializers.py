from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User, Business, Role
from .models import AuditLog

class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['id', 'name', 'description']

class BusinessSerializer(serializers.ModelSerializer):
    city_display = serializers.CharField(source='get_city_display', read_only=True)
    
    class Meta:
        model = Business
        fields = ['id', 'name', 'registration_number', 'city', 'city_display', 
                  'phone', 'email', 'address', 'postal_code', 'created_at']

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    
    class Meta:
        model = User
        fields = ['email', 'username', 'password', 'phone', 'business', 'role']
    
    def validate_password(self, value):
        if not any(c.isupper() for c in value):
            raise serializers.ValidationError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in value):
            raise serializers.ValidationError("Password must contain at least one number")
        return value
    
    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            username=validated_data['username'],
            password=validated_data['password'],
            phone=validated_data.get('phone', ''),
            business=validated_data.get('business'),
            role=validated_data.get('role')
        )
        return user

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, data):
        user = authenticate(email=data['email'], password=data['password'])
        if not user:
            raise serializers.ValidationError("Invalid email or password")
        if not user.is_active:
            raise serializers.ValidationError("This account is disabled")
        return {'user': user}

class UserSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(source='role.get_name_display', read_only=True)
    business_name = serializers.CharField(source='business.name', read_only=True)
    business_city = serializers.CharField(source='business.get_city_display', read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'phone', 'role', 'role_name', 
                  'business', 'business_name', 'business_city', 'is_active', 
                  'last_login', 'created_at']
        



class AuditLogSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    module_display = serializers.CharField(source='get_module_display', read_only=True)
    
    class Meta:
        model = AuditLog
        fields = ['id', 'user', 'user_email', 'action', 'action_display', 
                  'module', 'module_display', 'description', 'details', 
                  'ip_address', 'created_at']
        read_only_fields = ['id', 'created_at']