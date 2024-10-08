from .models import (
    Target,
    Project,
    Risk,
    Vulnerability,
    Risks,
    Tenant
)
from .models import Scan
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from rest_framework import serializers
from .models import Tenant, UserProfile, UserOtp, TenantUser, UserCustom
from django.contrib.auth import authenticate
from django.contrib.auth.models import User, Group, Permission
from django.db import IntegrityError
from django.shortcuts import get_object_or_404

class RegisterUserSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(min_length=8, write_only=True)
    username = serializers.CharField(required=False)
    class Meta:
        model = User
        fields = ('email', 'password', 'username')
    def validate_email(self, value):
        """
        Check if the email is already in use.
        """
        if User.objects.filter(email=value, is_active=True).exists():
            raise serializers.ValidationError("User with this email already exists")
        return value
        
    def create(self, validated_data):
        """
        Create and return a new user instance.
        """
        email = validated_data['email']
        username = validated_data.get('username')
        password = validated_data['password']
        if not username:
            username = email.split("@")[0]  # Extract username from email if not provided
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                is_active=False  # Set is_active to False initially
            )
        except IntegrityError as e:
            if 'auth_user.username' in str(e):  # Check if the error is due to duplicate username
                user = User.objects.get(username=username)  # Fetch the existing user
                user.email = email  # Update the email
                user.set_password(password)  # Update the password
                user.is_active = False  # Set is_active to False initially
                user.save()
            else:
                raise e  # Raise the error if it's not related to duplicate username
        
        # Create Tenant object if not already created
        if not Tenant.objects.filter(useruuid_id=user.id).exists():
            try:
                tenant = Tenant.objects.create(
                    name=f"{email}_tenant", useruuid_id=user.id
                )
            except Exception as e:
                # Handle any exceptions that may occur during Tenant creation
                # This could include validation errors, database errors, etc.
                # You can adjust this handling according to your needs
                tenant = None
                # Log the exception or handle it accordingly
                
            # If tenant creation was successful, you can return the tenant data
            if tenant:
                tenant_data = {
                    "type": "success",
                    "message": "Tenant created successfully",
                    "tenant_id": tenant.id,
                }
            else:
                tenant_data = {}
        else:
            tenant_data = {}

        return user, tenant_data


class UserLoginSerializer(serializers.Serializer):
    """
    Serializer for user login.

    This serializer validates email and password provided for user login. It checks
    if the credentials are correct by authenticating the user with the provided email
    and password using Django's authentication system. If authentication fails, it raises
    a validation error with the message "Incorrect email or password".

    Attributes:
    - email (EmailField): Field for user email.
    - password (CharField): Field for user password.

    Methods:
    - validate(data): Method to validate email and password and authenticate the user.
      Raises a validation error if authentication fails.
    """

    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, data):
        email = data.get("email")
        password = data.get("password")

        user = authenticate(email=email, password=password)

        if not user:
            raise serializers.ValidationError("Incorrect email or password")

        data["user"] = user

        return data

class VerifiedOtpSerializer(serializers.Serializer):
    otp = serializers.CharField(min_length=6, write_only=True)
    user_id = serializers.IntegerField(required=False)
    is_active = serializers.BooleanField(default=True)
    def validate_otp(self, value):
        """
        Validate the OTP provided by the user and generate an access token if the OTP is valid.

        Args:
            value (str): The OTP provided by the user.

        Returns:
            dict: Access token if the OTP is valid.

        Raises:
            serializers.ValidationError: If the OTP is invalid or expired.
        """
        otp = value
        user_id = self.context.get('user_id')  # Assuming user_id is passed through context
        # return user_id
        user = get_object_or_404(User, pk=user_id)
        user.is_active = True
        user.save()
        user_otp = UserOtp.objects.filter(
            useruuid=user, otp=otp, is_active=True
        ).first()

        if user_otp:
            user_otp.is_active = False
            user_otp.save()
            return True 
        else:
            raise serializers.ValidationError("Invalid OTP or Expired OTP")

    # def verify_otp(self):
    #     """
    #     Verify the provided OTP.

    #     Returns:
    #     - Response: An HTTP response indicating the result of OTP verification.
    #     """
    #     otp = self.validated_data.get("otp")
    #     user_id = self.validated_data.get("user_id")
    #     user = get_object_or_404(User, pk=user_id)
    #     user.is_active = True
    #     user.save()
    #     user_otp = UserOtp.objects.filter(
    #         useruuid=user, otp=otp, is_active=True
    #     ).first()

    #     if user_otp:
    #         user_otp.is_active = False
    #         user_otp.save()
    #         access_token = generate_tokens(user.id)
    #         if access_token.data["type"] == "success":
    #             return access_token
    #     else:
    #         raise serializers.ValidationError("Invalid OTP or Expired OTP")


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)


class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = ("id","name", "useruuid_id")


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ("email", "password", "tenant", "is_verified", "mfa_code")


class UserOtpSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserOtp
        fields = ["otp", "is_active", "useruuid"]



class TenantUserSerializer(serializers.ModelSerializer):
    """
    Serializer for tenant user data.

    This serializer is used to serialize and validate data for tenant users.
    It includes fields for the tenant ID, name, organization name, and active status.

    Attributes:
    - id (ReadOnlyField): Field for the unique identifier of the tenant user.
    - tenant_id (PrimaryKeyRelatedField): Field for the ID of the associated tenant.
    - name (CharField): Field fraise serializers.ValidationError("Incorrect email or password")or the name of the tenant user.
    - organization_name (CharField): Field for the organization name of the tenant user.
    - is_active (BooleanField): Field for the active status of the tenant user.

    Methods:
    - validate_name(value): Method to validate the name field. Raises a validation error
      if the name is empty.
    - validate_organization_name(value): Method to validate the organization name field.
      Raises a validation error if the organization name is empty.
    - validate_is_active(value): Method to validate the is_active field. Raises a validation
      error if the value is not a boolean.
    """

    class Meta:
        model = TenantUser
        fields = ["id", "tenant_id", "name", "organization_name", "is_active"]

    def validate_name(self, value):
        if not value:
            raise serializers.ValidationError("Name cannot be empty")
        return value

    def validate_organization_name(self, value):
        if not value:
            raise serializers.ValidationError("Organization name cannot be empty")
        return value

    def validate_is_active(self, value):
        if not isinstance(value, bool):
            raise serializers.ValidationError("is_active must be a boolean value")
        return value


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for user data.

    This serializer is used to serialize and validate user data, including email
    and full name fields.

    Attributes:
    - email (EmailField): Field for the user's email address.
    - full_name (CharField): Field for the user's full name.

    Methods:
    - validate_email(value): Method to validate the email field. It checks if the email
      address is valid and if it's already in use by another user.
    - validate_full_name(value): Method to validate the full name field. It checks if the
      full name contains both first name and last name.
    """

    email = serializers.EmailField(required=True)
    full_name = serializers.CharField(max_length=100, required=True)

    class Meta:
        model = User
        fields = ("email", "full_name")

    def validate_email(self, value):
        try:
            validate_email(value)
        except ValidationError as e:
            raise serializers.ValidationError(str(e))

        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email address already exists")

        return value

    def validate_full_name(self, value):
        name_parts = value.split()
        if len(name_parts) < 2:
            raise serializers.ValidationError(
                "Full name should contain both first name and last name"
            )

        return value


class GroupSerializer(serializers.ModelSerializer):
    """
    Serializer for group data.

    This serializer is used to serialize and update group data, including
    the group's name and associated permissions.

    Attributes:
    - id (ReadOnlyField): Field for the unique identifier of the group.
    - name (CharField): Field for the name of the group.
    - permission_names (SerializerMethodField): Method field to retrieve the names
      of permissions associated with the group.

    Methods:
    - get_permission_names(group): Method to retrieve the names of permissions associated
      with the group.
    - update(instance, validated_data): Method to update the group instance with the
      provided validated data, including the name and associated permissions.
    - assign_roles(group, permission_names): Method to assign permissions to the group.
    """

    permission_names = serializers.SerializerMethodField()

    def get_permission_names(self, group):
        return list(group.permissions.values_list("name", flat=True))

    class Meta:
        model = Group
        fields = ["id", "name", "permission_names"]

    def update(self, instance, validated_data):
        instance.name = validated_data.get("name", instance.name)
        instance.save()

        permission_names = validated_data.get("permission_names", [])
        self.assign_roles(instance, permission_names)

        return instance

    def assign_roles(self, group, permission_names):
        group.permissions.clear()

        for permission_name in permission_names:
            try:
                permission = Permission.objects.get(name=permission_name)
                group.permissions.add(permission)
            except Permission.DoesNotExist:
                pass


class UserCustomSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserCustom
        fields = ["id", "username", "email", "tenant", "is_active"]

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["tenant"] = TenantSerializer(instance.tenant).data
        return representation


class TargetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Target
        fields = "__all__"


class ProjectSerializer(serializers.ModelSerializer):
    targets = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Target.objects.all()
    )

    class Meta:
        model = Project
        fields = "__all__"

    def create(self, validated_data):
        """
        Create a new project instance.
        """
        targets_data = validated_data.pop("targets")
        project = Project.objects.create(**validated_data)
        project.targets.set(targets_data)
        return project

    def to_representation(self, instance):
        """
        Convert model instance to a Python dictionary for serialization.
        """
        representation = super().to_representation(instance)
        representation["targets"] = TargetSerializer(
            instance.targets.all(), many=True
        ).data
        return representation


class RiskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Risk
        fields = ["id", "project", "description"]


class VulnerabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Vulnerability
        fields = ["id", "project", "description"]


class ScanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scan
        fields = "__all__"


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ("id", "name", "codename", "content_type")


class RisksSerializer(serializers.ModelSerializer):
    class Meta:
        model = Risks
        fields = "__all__"
