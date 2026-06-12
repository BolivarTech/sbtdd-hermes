"""Tests for sbtdd_hermes.plugin registration."""

from unittest.mock import MagicMock

from sbtdd_hermes import register


def test_register_commands():
    ctx = MagicMock()
    register(ctx)
    
    # Check commands registered
    calls = ctx.register_command.call_args_list
    names = [c[0][0] for c in calls]
    assert "sbtdd" in names
    assert "sbtdd-init" in names
    assert "sbtdd-check" in names


def test_register_tools():
    ctx = MagicMock()
    register(ctx)
    
    calls = ctx.register_tool.call_args_list
    names = [c.kwargs.get("name", c[0][0]) for c in calls]
    assert "sbtdd_status" in names
    assert "sbtdd_update_state" in names


def test_register_hooks():
    ctx = MagicMock()
    register(ctx)
    
    calls = ctx.register_hook.call_args_list
    names = [c[0][0] for c in calls]
    assert "pre_tool_call" in names
    assert "on_session_start" in names
