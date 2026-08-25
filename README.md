# netbox-oidc-group-sync

A [python-social-auth](https://github.com/python-social-auth/social-core) pipeline step that syncs NetBox
Django groups and `is_superuser` status from an OIDC `groups` claim.

## Why this exists

NetBox Community ships two independent group-sync code paths under `netbox.authentication`:

- `RemoteUserBackend.configure_groups()` implements dynamic, claim-based group sync (with optional
  auto-create) plus superuser evaluation from `REMOTE_AUTH_SUPERUSER_GROUPS` -- but it's only ever invoked
  from `RemoteUserBackend.authenticate()`, Django's HTTP-header remote-auth path (a `REMOTE_USER` header set
  by an upstream reverse proxy). It is **never reached by a social-auth/OIDC login**.
- `user_default_groups_handler`, the step actually wired into `SOCIAL_AUTH_PIPELINE` for social-auth backends
  (including OIDC), only assigns a *static* `REMOTE_AUTH_DEFAULT_GROUPS` list. It never reads a claim and
  never touches `is_superuser`.

So if you're using `social_core.backends.open_id_connect.OpenIdConnectAuth` (or another social-auth OIDC
backend) as your NetBox login method, setting `REMOTE_AUTH_GROUP_SYNC_ENABLED` / `AUTO_CREATE_GROUPS` /
`SUPERUSER_GROUPS` in your NetBox configuration has **no effect whatsoever** -- those settings are consumed
exclusively by the header-based backend. NetBox Labs' Enterprise product solves this with a proprietary
pipeline step (`nbc_auth_extensions.azure_authentication.azuread_map_groups`, [Enterprise-only, Entra
ID-specific](https://netboxlabs.com/docs/enterprise/nbe-oidc-sso/#microsoft-entra-id-group-mapping)).

`sync_groups` closes that gap for Community: dropped into `SOCIAL_AUTH_PIPELINE` in place of
`user_default_groups_handler`, it re-implements `configure_groups()`'s logic against the OIDC response
instead of an HTTP header, reusing the exact same `REMOTE_AUTH_*` settings NetBox already defines -- no new
configuration surface.

## Installation

```sh
pip install netbox-oidc-group-sync
```

Then, in your NetBox `configuration.py` (or an `extraConfig` block if you're deploying via the
[netbox-chart](https://github.com/netbox-community/netbox-chart) Helm chart):

```python
SOCIAL_AUTH_PIPELINE = (
    "social_core.pipeline.social_auth.social_details",
    "social_core.pipeline.social_auth.social_uid",
    "social_core.pipeline.social_auth.social_user",
    "social_core.pipeline.user.get_username",
    "social_core.pipeline.user.create_user",
    "social_core.pipeline.social_auth.associate_user",
    "netbox_oidc_group_sync.sync_groups",  # replaces netbox.authentication.user_default_groups_handler
    "social_core.pipeline.social_auth.load_extra_data",
    "social_core.pipeline.user.user_details",
)
```

The package itself needs to be on the NetBox pod's Python path -- if you're running the stock
`netboxcommunity/netbox` image, that means building a derivative image that `pip install`s it (see
[`docs/installation.md`](docs/installation.md) for a working Dockerfile example).

## Configuration

Reuses NetBox's own settings -- nothing new to configure beyond what a `RemoteUserBackend` deployment would
already set:

| Setting | Effect |
|---|---|
| `REMOTE_AUTH_GROUP_SYNC_ENABLED` | Master on/off switch. `sync_groups` no-ops entirely when falsy. |
| `REMOTE_AUTH_GROUP_HEADER` | The key to look up in the OIDC claims/userinfo `response` dict for the user's group list. Named for its original HTTP-header use case; repurposed here as a claim key, which doesn't conflict with anything since it has no effect on social-auth logins upstream. |
| `REMOTE_AUTH_AUTO_CREATE_GROUPS` | Create a Django `Group` for a claimed group name that doesn't exist yet, instead of skipping it with a logged error. |
| `REMOTE_AUTH_SUPERUSER_GROUPS` | Group names that grant `is_superuser` when present in the user's synced claim groups. |
| `REMOTE_AUTH_SUPERUSERS` | Usernames that are always superusers, regardless of group membership. |

Group membership is a **full sync**, not additive: a user's Django groups are set to exactly what the claim
says on every login (matching `configure_groups()`'s own semantics), including clearing all groups -- and
revoking superuser status -- if the claim comes back empty or absent.

## Development

```sh
uv sync
uv run pre-commit install
uv run pytest --cov=src --cov-report=term-missing
```

Docs are built with [Zensical](https://github.com/squidfunk/zensical):

```sh
uvx zensical serve
```
