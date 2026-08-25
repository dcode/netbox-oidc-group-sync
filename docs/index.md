# netbox-oidc-group-sync

A [python-social-auth](https://github.com/python-social-auth/social-core) pipeline step that syncs NetBox
Django groups and `is_superuser`/`is_staff` status from an OIDC `groups` claim.

## The gap

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
exclusively by the header-based backend, which OIDC logins never touch.

NetBox Labs' Enterprise product solves this with a proprietary pipeline step
(`nbc_auth_extensions.azure_authentication.azuread_map_groups`), documented as
[Entra ID-specific and Enterprise-only](https://netboxlabs.com/docs/enterprise/nbe-oidc-sso/#microsoft-entra-id-group-mapping).

## The fix

`sync_groups` closes that gap for Community: dropped into `SOCIAL_AUTH_PIPELINE` in place of
`user_default_groups_handler`, it re-implements `configure_groups()`'s logic against the OIDC `response`
instead of an HTTP header, reusing the exact same `REMOTE_AUTH_*` settings NetBox already defines. No new
configuration surface, no fork of NetBox itself.

See [Installation](installation.md) to get it running, and [Configuration](configuration.md) for the settings
it reads.
