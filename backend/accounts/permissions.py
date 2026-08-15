from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAdminRole(BasePermission):
    """Only system administrators."""

    message = "Only a system administrator can perform this action."

    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and request.user.is_admin_role
        )


class CanManageRecords(BasePermission):
    """Registrars and admins may write; every authenticated user may read.

    Guards need read access to every student and device record to do their job
    at the gate, but they must never be able to edit ownership. Only staff hold
    accounts at all - students never sign in.
    """

    message = "Only a registration officer or administrator can change this record."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return request.user.can_manage_records
