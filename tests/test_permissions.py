from types import SimpleNamespace

from game_commands import can_manage_games


def fake_interaction(*, owner_id=1, user_id=2, admin=False, role_ids=()):
    user = SimpleNamespace(
        id=user_id,
        guild_permissions=SimpleNamespace(administrator=admin),
        roles=[SimpleNamespace(id=r) for r in role_ids],
    )
    guild = SimpleNamespace(owner_id=owner_id)
    return SimpleNamespace(user=user, guild=guild)


def test_server_owner_can_manage():
    assert can_manage_games(fake_interaction(user_id=1), 999)


def test_administrator_can_manage():
    assert can_manage_games(fake_interaction(admin=True), 999)


def test_configured_role_can_manage():
    assert can_manage_games(fake_interaction(role_ids=(999,)), 999)


def test_ordinary_member_cannot_manage():
    assert not can_manage_games(fake_interaction(), 999)
