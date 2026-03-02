import unittest
from unittest.mock import AsyncMock, patch

import bot


class BotUtilityTests(unittest.TestCase):
    def test_resolve_target_chat_id_uses_only_alert_chat(self) -> None:
        with patch.object(bot, "ALERT_CHAT_ID", 0), patch.object(bot, "last_authorized_chat_id", 999):
            self.assertEqual(bot.resolve_target_chat_id(), 0)

        with patch.object(bot, "ALERT_CHAT_ID", -100123456):
            self.assertEqual(bot.resolve_target_chat_id(), -100123456)

    def test_format_responsible(self) -> None:
        self.assertEqual(bot.format_responsible(None), "-")
        self.assertEqual(bot.format_responsible("-"), "-")
        self.assertEqual(bot.format_responsible("manager"), "@manager")


class MonitorJobTests(unittest.IsolatedAsyncioTestCase):
    async def test_monitor_job_sends_alert_and_handles_empty_responsible(self) -> None:
        row = {
            "id": 1,
            "username": "ahmet",
            "department_threshold_minutes": 10,
            "responsible_username": None,
            "department_name": "satis",
            "department_weekly_off_day": None,
            "day_off_date": None,
            "exempt_until": None,
            "department_id": None,
        }

        async def passthrough(func, *args, **kwargs):
            return func(*args, **kwargs)

        context = type("Ctx", (), {})()
        context.bot = type("DummyBot", (), {"send_message": AsyncMock()})()

        with (
            patch.object(bot, "db_call", new=passthrough),
            patch.object(bot, "is_within_monitor_hours", return_value=True),
            patch.object(bot, "resolve_target_chat_id", return_value=-100987654321),
            patch.object(bot, "resolve_last_seen_minutes", new=AsyncMock(return_value=(15, "15 dakika"))),
            patch.object(bot.database, "list_personnel", return_value=[row]),
            patch.object(bot.database, "get_watch_state", return_value=None),
            patch.object(bot.database, "get_department_responsibles", return_value=[]),
            patch.object(bot.database, "add_violation_event") as add_violation_event,
            patch.object(bot.database, "set_watch_state") as set_watch_state,
        ):
            await bot.monitor_job(context)

        context.bot.send_message.assert_awaited_once()
        sent_text = context.bot.send_message.await_args.kwargs["text"]
        self.assertIn("Sorumlu : -", sent_text)
        add_violation_event.assert_called_once()
        set_watch_state.assert_called_once()


if __name__ == "__main__":
    unittest.main()
