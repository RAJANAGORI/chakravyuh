"""Access control and RBAC management."""
from typing import List, Set, Dict, Optional
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

from chakravyuh.core.logging import logger


class Permission(str, Enum):
    """Permissions for resources."""
    READ_DOCUMENTS = "read_documents"
    WRITE_DOCUMENTS = "write_documents"
    DELETE_DOCUMENTS = "delete_documents"
    READ_THREAT_MODELS = "read_threat_models"
    WRITE_THREAT_MODELS = "write_threat_models"
    ADMIN = "admin"


@dataclass
class Role:
    """User role with permissions."""
    name: str
    permissions: Set[Permission] = field(default_factory=set)
    description: str = ""


class AccessControlManager:
    """Manages access control and RBAC."""

    # Predefined roles
    ADMIN_ROLE = Role(
        name="admin",
        permissions={p for p in Permission},
        description="Full system access",
    )

    SECURITY_ANALYST_ROLE = Role(
        name="security_analyst",
        permissions={
            Permission.READ_DOCUMENTS,
            Permission.READ_THREAT_MODELS,
            Permission.WRITE_THREAT_MODELS,
        },
        description="Can read documents and create threat models",
    )

    READER_ROLE = Role(
        name="reader",
        permissions={Permission.READ_DOCUMENTS, Permission.READ_THREAT_MODELS},
        description="Read-only access",
    )


    def assign_role(self, user_id: str, role_name: str) -> bool:
        """
        Assign a role to a user.

        Args:
            user_id: User identifier
            role_name: Role name

        Returns:
            True if successful
        """
        if role_name not in self.roles:
            logger.error(f"Unknown role: {role_name}")
            return False

        if user_id not in self.user_roles:
            self.user_roles[user_id] = set()

        self.user_roles[user_id].add(role_name)
        logger.info(f"Assigned role {role_name} to user {user_id}")
        return True

    def revoke_role(self, user_id: str, role_name: str) -> bool:
        """
        Revoke a role from a user.

        Args:
            user_id: User identifier
            role_name: Role name

        Returns:
            True if successful
        """
        if user_id in self.user_roles:
            self.user_roles[user_id].discard(role_name)
            logger.info(f"Revoked role {role_name} from user {user_id}")
            return True

        return False

    def __init__(self, auto_assign_reader: bool = False):
        """
        Initialize access control manager.
        
        Args:
            auto_assign_reader: If True, automatically assign reader role to users without roles.
                               Default is False for security (deny by default).
        """
        self.roles: Dict[str, Role] = {
            "admin": self.ADMIN_ROLE,
            "security_analyst": self.SECURITY_ANALYST_ROLE,
            "reader": self.READER_ROLE,
        }
        self.user_roles: Dict[str, Set[str]] = {}  # user_id -> {role_names}
        self.resource_permissions: Dict[str, Set[str]] = {}  # resource_id -> {user_ids}
        self.auto_assign_reader = auto_assign_reader

    def has_permission(self, user_id: str, permission: Permission) -> bool:
        """
        Check if user has a specific permission.

        Args:
            user_id: User identifier
            permission: Permission to check

        Returns:
            True if user has permission
        """
        user_roles = self.user_roles.get(user_id, set())
        
        # Only auto-assign if explicitly enabled in configuration
        if not user_roles and self.auto_assign_reader:
            # Auto-assign reader role for first-time users (if enabled)
            logger.debug(f"Auto-assigning reader role to user {user_id} (first access)")
            self.assign_role(user_id, "reader")
            user_roles = self.user_roles.get(user_id, set())
        elif not user_roles:
            # Deny by default - user has no roles assigned
            logger.warning(f"User {user_id} has no roles assigned and auto-assignment is disabled")
            return False

        for role_name in user_roles:
            role = self.roles.get(role_name)
            if role and permission in role.permissions:
                logger.debug(f"User {user_id} has permission {permission.value} via role {role_name}")
                return True

        logger.warning(f"User {user_id} does not have permission {permission.value} (roles: {user_roles})")
        return False

    def check_access(self, user_id: str, resource_id: str, permission: Permission) -> bool:
        """
        Check if user has access to a resource.

        Args:
            user_id: User identifier
            resource_id: Resource identifier
            permission: Required permission

        Returns:
            True if access granted
        """
        # Check role-based permissions
        if self.has_permission(user_id, permission):
            return True

        # Check resource-specific permissions
        resource_users = self.resource_permissions.get(resource_id, set())
        if user_id in resource_users:
            return True

        logger.warning(f"Access denied: user {user_id} lacks {permission} for {resource_id}")
        return False

    def grant_resource_access(self, user_id: str, resource_id: str) -> None:
        """
        Grant user access to a specific resource.

        Args:
            user_id: User identifier
            resource_id: Resource identifier
        """
        if resource_id not in self.resource_permissions:
            self.resource_permissions[resource_id] = set()

        self.resource_permissions[resource_id].add(user_id)
        logger.info(f"Granted access to resource {resource_id} for user {user_id}")

    def revoke_resource_access(self, user_id: str, resource_id: str) -> None:
        """
        Revoke user access to a specific resource.

        Args:
            user_id: User identifier
            resource_id: Resource identifier
        """
        if resource_id in self.resource_permissions:
            self.resource_permissions[resource_id].discard(user_id)
            logger.info(f"Revoked access to resource {resource_id} for user {user_id}")
