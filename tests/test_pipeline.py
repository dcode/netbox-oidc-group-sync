import pytest
from django.contrib.auth.models import Group, User

from netbox_oidc_group_sync.pipeline import sync_groups


@pytest.fixture
def user(db) -> User:
    return User.objects.create(username="dcode")


@pytest.mark.django_db
def test_noop_when_sync_disabled(settings, user):
    settings.REMOTE_AUTH_GROUP_SYNC_ENABLED = False
    sync_groups(backend=None, user=user, response={"groups": ["netbox-admins"]})

    user.refresh_from_db()
    assert list(user.groups.all()) == []
    assert user.is_superuser is False


@pytest.mark.django_db
def test_noop_when_user_is_none():
    # Must not raise even though there's nothing to act on.
    sync_groups(backend=None, user=None, response={"groups": ["netbox-admins"]})


@pytest.mark.django_db
def test_noop_when_user_unpersisted():
    unsaved = User(username="ghost")
    sync_groups(backend=None, user=unsaved, response={"groups": ["netbox-admins"]})
    assert unsaved.pk is None


@pytest.mark.django_db
def test_assigns_existing_groups(user):
    Group.objects.create(name="netbox-users")
    sync_groups(backend=None, user=user, response={"groups": ["netbox-users"]})

    user.refresh_from_db()
    assert [g.name for g in user.groups.all()] == ["netbox-users"]
    assert user.is_superuser is False
    assert user.is_staff is False


@pytest.mark.django_db
def test_auto_creates_missing_group_when_enabled(settings, user):
    settings.REMOTE_AUTH_AUTO_CREATE_GROUPS = True
    assert not Group.objects.filter(name="netbox-viewers").exists()

    sync_groups(backend=None, user=user, response={"groups": ["netbox-viewers"]})

    user.refresh_from_db()
    assert Group.objects.filter(name="netbox-viewers").exists()
    assert [g.name for g in user.groups.all()] == ["netbox-viewers"]


@pytest.mark.django_db
def test_skips_missing_group_when_auto_create_disabled(settings, user):
    settings.REMOTE_AUTH_AUTO_CREATE_GROUPS = False

    sync_groups(backend=None, user=user, response={"groups": ["does-not-exist"]})

    user.refresh_from_db()
    assert list(user.groups.all()) == []
    assert not Group.objects.filter(name="does-not-exist").exists()


@pytest.mark.django_db
def test_grants_superuser_for_matching_group(settings, user):
    Group.objects.create(name="netbox-admins")
    settings.REMOTE_AUTH_SUPERUSER_GROUPS = ["netbox-admins"]

    sync_groups(backend=None, user=user, response={"groups": ["netbox-admins"]})

    user.refresh_from_db()
    assert user.is_superuser is True
    assert user.is_staff is True


@pytest.mark.django_db
def test_grants_superuser_for_username_allowlist(settings, user):
    settings.REMOTE_AUTH_SUPERUSER_GROUPS = []
    settings.REMOTE_AUTH_SUPERUSERS = ["dcode"]

    sync_groups(backend=None, user=user, response={"groups": []})

    user.refresh_from_db()
    assert user.is_superuser is True


@pytest.mark.django_db
def test_revokes_superuser_when_no_longer_in_group(settings, user):
    user.is_superuser = True
    user.is_staff = True
    user.save()
    settings.REMOTE_AUTH_SUPERUSER_GROUPS = ["netbox-admins"]

    sync_groups(backend=None, user=user, response={"groups": []})

    user.refresh_from_db()
    assert user.is_superuser is False
    assert user.is_staff is False


@pytest.mark.django_db
def test_clears_groups_when_claim_absent(user):
    group = Group.objects.create(name="netbox-users")
    user.groups.add(group)

    sync_groups(backend=None, user=user, response={})

    user.refresh_from_db()
    assert list(user.groups.all()) == []


@pytest.mark.django_db
def test_normalizes_single_string_claim_to_list(user):
    Group.objects.create(name="netbox-users")

    sync_groups(backend=None, user=user, response={"groups": "netbox-users"})

    user.refresh_from_db()
    assert [g.name for g in user.groups.all()] == ["netbox-users"]


@pytest.mark.django_db
def test_uses_configured_claim_key(settings, user):
    settings.REMOTE_AUTH_GROUP_HEADER = "roles"
    Group.objects.create(name="netbox-users")

    sync_groups(
        backend=None, user=user, response={"roles": ["netbox-users"], "groups": ["ignored"]}
    )

    user.refresh_from_db()
    assert [g.name for g in user.groups.all()] == ["netbox-users"]
