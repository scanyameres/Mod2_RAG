"""Tests of the admin role (auth.is_admin()) and the app settings saved by the admin (app_settings.py). Offline."""

import pytest
import yaml
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from scanya_ae_afa_updated0209_2_5 import agent, app_settings, auth, settings
from scanya_ae_afa_updated0209_2_5.workspace import Workspace


@pytest.fixture(autouse=True)
def temporary_files(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "APP_SETTINGS_FILE", tmp_path / "app_settings.json")
    monkeypatch.setattr(settings, "AUTH_CONFIG_FILE", tmp_path / "config.yaml")
    users = {"boss": {"roles": [settings.ADMIN_ROLE]}, "visitor": {"roles": None}}
    settings.AUTH_CONFIG_FILE.write_text(yaml.safe_dump({"credentials": {"usernames": users}}), encoding="utf-8")


@pytest.mark.parametrize(("username", "expected"), [("boss", True), ("visitor", False), (None, False), ("unknown", False)])
def test_only_a_user_with_the_admin_role_is_admin(monkeypatch, username, expected):
    monkeypatch.setattr(auth, "current_user", lambda: username)
    assert auth.is_admin() is expected


def test_the_real_config_has_exactly_one_admin():
    users = yaml.safe_load((settings.PROJECT_ROOT / "config.yaml").read_text(encoding="utf-8"))["credentials"]["usernames"]
    admins = [name for name, user in users.items() if settings.ADMIN_ROLE in (user.get("roles") or [])]
    assert admins == ["sergi"]


def test_without_a_saved_file_the_settings_come_from_settings_py():
    values = app_settings.load()
    assert values["top_k"] == settings.TOP_K and values["model_name"] == settings.CHAT_MODELS[0]
    assert values["guard_enabled"] is True and values["spending_limit_usd"] == settings.SPENDING_LIMIT_USD


def test_saved_settings_are_loaded_back():
    values = {**app_settings.load(), "top_k": 3, "model_name": settings.CHAT_MODELS[1], "spending_limit_usd": 2.5}
    app_settings.save(values)
    assert app_settings.load() == values


def test_invalid_saved_values_fall_back_or_are_clamped():
    settings.APP_SETTINGS_FILE.write_text(
        '{"top_k": 999, "max_searches": 0, "model_name": "gone/model", "active_categories": ["housing", "gone"],'
        ' "spending_limit_usd": -1}',
        encoding="utf-8",
    )
    values = app_settings.load()
    assert values["top_k"] == settings.TOP_K_MAX and values["max_searches"] == 1
    assert values["model_name"] == settings.CHAT_MODELS[0]
    assert values["active_categories"] == ["housing"] and values["spending_limit_usd"] == 0.0


def test_guard_switched_off_is_not_called():
    class FailingGuard:
        def with_structured_output(self, *args, **kwargs):
            raise AssertionError("The guard must not be called when it is switched off.")

    class FakeModel(GenericFakeChatModel):
        def bind_tools(self, tools, **kwargs):
            return self

    events = list(
        agent.answer_question(
            "Frage", [], Workspace(), [], use_guard=False,
            chat_model=FakeModel(messages=iter([AIMessage(content="Antwort")])), guard_model=FailingGuard(),
        )
    )
    assert [event.kind for event in events] == ["answer"]
