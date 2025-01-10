import pytest
from superdesk.core.privileges import PrivilegesRegistry, Privilege


@pytest.fixture(scope="function")
def registry():
    reg = PrivilegesRegistry()
    yield reg

    print("*" * 100)
    reg = None


def test_add_privilege_before_lock(registry):
    privilege = Privilege(name="edit_article")

    registry.add(privilege)

    assert "edit_article" in registry
    assert registry.get_all() == [privilege]


def test_add_multiple_privileges(registry):
    privilege1 = Privilege(name="edit_article")
    privilege2 = Privilege(name="delete_article")

    registry.add(privilege1)
    registry.add(privilege2)

    assert "edit_article" in registry
    assert "delete_article" in registry
    assert len(registry.get_all()) == 2


def test_lock_registry(registry):
    privilege = Privilege(name="edit_article")

    registry.add(privilege)
    registry.lock()

    assert registry.is_locked
    assert "edit_article" in registry


def test_cannot_add_after_lock(registry):
    privilege = Privilege(name="edit_article")

    registry.add(privilege)
    registry.lock()

    with pytest.raises(RuntimeError):
        registry.add(Privilege(name="new_privilege"))


def test_lock_prevents_further_additions(registry):
    privilege = Privilege(name="edit_article")

    registry.add(privilege)
    registry.lock()

    with pytest.raises(RuntimeError, match="Cannot add privileges after the app has started."):
        registry.add(Privilege(name="new_privilege"))

    assert len(registry.get_all()) == 1
    assert registry.is_locked
