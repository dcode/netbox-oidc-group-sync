"""A python-social-auth pipeline step for dynamic OIDC group/superuser sync in NetBox.

NetBox Community ships two independent group-sync code paths under
`netbox.authentication`:

- `RemoteUserBackend.configure_groups()` implements dynamic, claim-based group
  sync (with optional auto-create) plus superuser evaluation -- but it is only
  ever invoked from `RemoteUserBackend.authenticate()`, Django's HTTP-header
  remote-auth path (`REMOTE_USER` via middleware). It is never reached by a
  social-auth/OIDC login.
- `user_default_groups_handler`, the pipeline step actually wired into
  `SOCIAL_AUTH_PIPELINE` for social-auth backends (including OIDC), only ever
  assigns a *static* `REMOTE_AUTH_DEFAULT_GROUPS` list. It never reads a claim
  and never touches `is_superuser`.

`sync_groups` below closes that gap: dropped into `SOCIAL_AUTH_PIPELINE` in
place of `user_default_groups_handler`, it re-implements
`configure_groups()`'s logic against the OIDC response instead of an HTTP
header, reusing the same `REMOTE_AUTH_*` settings NetBox already exposes (and
that this project's Helm/Terraform config already sets) so no new
configuration surface is needed.

Note: `REMOTE_AUTH_GROUP_HEADER` is named for its original HTTP-header use
case, but is repurposed here as the OIDC claim key to look up in the
social-auth `response` dict -- it has no effect on social-auth logins
upstream, so this repurposing doesn't conflict with anything.
"""

from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.contrib.auth.models import Group

logger = logging.getLogger("netbox_oidc_group_sync.pipeline")


def sync_groups(
    backend: Any,
    user: Any,
    response: dict[str, Any],
    *args: Any,
    **kwargs: Any,
) -> None:
    """Sync a user's Django groups and superuser status from an OIDC claim.

    No-ops entirely when `settings.REMOTE_AUTH_GROUP_SYNC_ENABLED` is falsy,
    or when there's no persisted user yet (e.g. authentication failed
    upstream in the pipeline) -- mirroring `RemoteUserBackend.authenticate()`'s
    own guard before calling `configure_groups()`.

    Args:
        backend: The social-auth backend instance (unused; part of the
            pipeline step signature social-auth calls with).
        user: The Django user being authenticated. Must already be persisted
            (i.e. a prior pipeline step such as `social_core.pipeline.
            social_auth.associate_user` has already run).
        response: The raw claims/userinfo dict from the OIDC provider.
        *args: Unused; accepted for pipeline signature compatibility.
        **kwargs: Unused; accepted for pipeline signature compatibility.
    """
    if not getattr(settings, "REMOTE_AUTH_GROUP_SYNC_ENABLED", False):
        return
    if user is None or not getattr(user, "pk", None):
        return

    claim_key = getattr(settings, "REMOTE_AUTH_GROUP_HEADER", "groups")
    auto_create = getattr(settings, "REMOTE_AUTH_AUTO_CREATE_GROUPS", False)
    superuser_groups = set(getattr(settings, "REMOTE_AUTH_SUPERUSER_GROUPS", []))
    superusers = set(getattr(settings, "REMOTE_AUTH_SUPERUSERS", []))

    remote_groups = response.get(claim_key) or []
    if isinstance(remote_groups, str):
        remote_groups = [remote_groups]

    group_list = []
    for name in remote_groups:
        try:
            group_list.append(Group.objects.get(name=name))
        except Group.DoesNotExist:
            if auto_create:
                group_list.append(Group.objects.create(name=name))
            else:
                logger.error(
                    "Could not assign group %s to remotely-authenticated user %s: group not found",
                    name,
                    user,
                )

    if group_list:
        user.groups.set(group_list)
        logger.debug("Assigned groups to remotely-authenticated user %s: %s", user, group_list)
    else:
        user.groups.clear()
        logger.debug("Stripping user %s of groups (no valid claim groups resolved)", user)

    user.is_superuser = user.username in superusers or bool(
        {group.name for group in group_list} & superuser_groups
    )
    user.is_staff = user.is_superuser
    user.save()
