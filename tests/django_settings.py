SECRET_KEY = "test-secret-key"

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

USE_TZ = True

# Defaults exercised by tests; individual tests override via the `settings` fixture.
REMOTE_AUTH_GROUP_SYNC_ENABLED = True
REMOTE_AUTH_GROUP_HEADER = "groups"
REMOTE_AUTH_AUTO_CREATE_GROUPS = True
REMOTE_AUTH_SUPERUSER_GROUPS: list[str] = ["netbox-admins"]
REMOTE_AUTH_SUPERUSERS: list[str] = []
