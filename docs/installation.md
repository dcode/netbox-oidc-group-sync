# Installation

## 1. Get the package onto NetBox's Python path

The stock `netboxcommunity/netbox` image doesn't include this package, so it needs a derivative image:

```dockerfile
FROM netboxcommunity/netbox:v4.6.7

RUN pip install --no-cache-dir netbox-oidc-group-sync
```

Build and push it under your own registry, then point your NetBox deployment's `image` at it instead of the
upstream tag.

## 2. Override `SOCIAL_AUTH_PIPELINE`

NetBox's `netbox/settings.py` hardcodes `SOCIAL_AUTH_PIPELINE`, but reloads every `SOCIAL_AUTH_*`-prefixed
attribute from `configuration.py` afterward -- so setting `SOCIAL_AUTH_PIPELINE` in your own configuration
overrides the built-in tuple. Swap `netbox_oidc_group_sync.sync_groups` in for
`netbox.authentication.user_default_groups_handler`, keeping every other step as-is:

```python
SOCIAL_AUTH_PIPELINE = (
    "social_core.pipeline.social_auth.social_details",
    "social_core.pipeline.social_auth.social_uid",
    "social_core.pipeline.social_auth.social_user",
    "social_core.pipeline.user.get_username",
    "social_core.pipeline.user.create_user",
    "social_core.pipeline.social_auth.associate_user",
    "netbox_oidc_group_sync.sync_groups",
    "social_core.pipeline.social_auth.load_extra_data",
    "social_core.pipeline.user.user_details",
)
```

If you're deploying via the [netbox-chart](https://github.com/netbox-community/netbox-chart) Helm chart,
this goes in an `extraConfig` block (Terraform example):

```hcl
extraConfig = [
  {
    values = {
      SOCIAL_AUTH_PIPELINE = [
        "social_core.pipeline.social_auth.social_details",
        "social_core.pipeline.social_auth.social_uid",
        "social_core.pipeline.social_auth.social_user",
        "social_core.pipeline.user.get_username",
        "social_core.pipeline.user.create_user",
        "social_core.pipeline.social_auth.associate_user",
        "netbox_oidc_group_sync.sync_groups",
        "social_core.pipeline.social_auth.load_extra_data",
        "social_core.pipeline.user.user_details",
      ]
    }
  }
]
```

## 3. Configure your OIDC provider to emit a `groups` claim

The IdP needs to include a `groups` claim (or whatever key you point `REMOTE_AUTH_GROUP_HEADER` at) in the
ID token or userinfo response, listing the group names NetBox should map to. See
[Configuration](configuration.md) for how those names map to Django groups and superuser status.
