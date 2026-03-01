from django.core.exceptions import PermissionDenied
from functools import wraps
from django.shortcuts import redirect, render


# Admin only
def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        raise PermissionDenied
    return wrapper


# Staff OR Admin
def staff_or_admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and (
            request.user.is_staff or request.user.is_superuser
        ):
            return view_func(request, *args, **kwargs)
        raise PermissionDenied
    return wrapper


# Get role permissions
def get_role_permissions(user):
    user_profile = getattr(user, 'userprofile', None)
    role = getattr(user_profile, 'role', None)
    permissions = role.permissions.all() if role else []
    permissions_list = list(permissions.values_list('name', flat=True))
    return role, permissions, permissions_list


def role_permission_required(permission_name):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # 🔥 Superadmin: NO CHECK AT ALL
            if request.user.is_authenticated and request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            # Not logged in
            if not request.user.is_authenticated:
                return redirect('login')
            user_profile = getattr(request.user, 'userprofile', None)
            role = getattr(user_profile, 'role', None)
            if not role:
                return render(request, '403.html', status=403)
            permissions = role.permissions.values_list('name', flat=True)
            if permission_name in permissions:
                return view_func(request, *args, **kwargs)
            return render(request, '403.html', status=403)
        return wrapper
    return decorator
