"""A NetBox social-auth pipeline step for dynamic OIDC group/superuser sync."""

from netbox_oidc_group_sync.__version__ import __version__
from netbox_oidc_group_sync.pipeline import sync_groups

__all__ = ["__version__", "sync_groups"]
