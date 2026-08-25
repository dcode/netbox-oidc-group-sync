# Configuration

`sync_groups` reuses NetBox's own `REMOTE_AUTH_*` settings -- the same ones a `RemoteUserBackend` deployment
would set -- so there's nothing new to learn if you've configured NetBox's remote auth before.

| Setting | Type | Effect |
|---|---|---|
| `REMOTE_AUTH_GROUP_SYNC_ENABLED` | `bool` | Master on/off switch. `sync_groups` no-ops entirely when falsy -- no group changes, no superuser changes. |
| `REMOTE_AUTH_GROUP_HEADER` | `str` | The key to look up in the OIDC claims/userinfo `response` dict for the user's group list. Named for its original HTTP-header use case in `RemoteUserBackend`; repurposed here as a claim key. This doesn't conflict with anything, since the setting has no effect on social-auth logins upstream. |
| `REMOTE_AUTH_AUTO_CREATE_GROUPS` | `bool` | When `true`, a claimed group name that doesn't exist yet is created. When `false`, it's skipped with a logged error and the user isn't added to it. |
| `REMOTE_AUTH_SUPERUSER_GROUPS` | `list[str]` | Group names that grant `is_superuser` and `is_staff` when present among the user's synced claim groups. |
| `REMOTE_AUTH_SUPERUSERS` | `list[str]` | Usernames that are always superusers, regardless of group membership. |

## Semantics

Group membership is a **full sync**, not additive. On every login, a user's Django groups are set to exactly
what the claim says -- matching `RemoteUserBackend.configure_groups()`'s own behavior:

- If the claim lists groups, the user's group set is replaced with those groups (creating missing ones if
  `REMOTE_AUTH_AUTO_CREATE_GROUPS` is set).
- If the claim is empty or the claim key is missing from the response entirely, **all** of the user's groups
  are cleared.
- Superuser/staff status is re-evaluated on every login from the *resulting* group set plus the static
  `REMOTE_AUTH_SUPERUSERS` allowlist -- so removing someone from the superuser group in your IdP revokes
  `is_superuser` on their next login, not just grants it.

## Example

Authentik OIDC provider with a scope mapping that emits `groups: ["netbox-admins"]` for a member of that
Authentik group, and NetBox configuration:

```python
REMOTE_AUTH_GROUP_SYNC_ENABLED = True
REMOTE_AUTH_GROUP_HEADER = "groups"
REMOTE_AUTH_AUTO_CREATE_GROUPS = True
REMOTE_AUTH_SUPERUSER_GROUPS = ["netbox-admins"]
```

A user in Authentik's `netbox-admins` group logs in, `sync_groups` runs as part of
[the pipeline](installation.md), NetBox creates a Django `netbox-admins` group if it doesn't already exist,
adds the user to it, and sets `is_superuser = True` / `is_staff = True`. A user removed from that group in
Authentik loses superuser status the next time they log in.
