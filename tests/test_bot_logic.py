import unittest
from unittest.mock import AsyncMock, patch
from datetime import datetime
from zoneinfo import ZoneInfo

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

    def test_should_skip_for_break_window(self) -> None:
        now_local = datetime(2026, 3, 2, 14, 30, tzinfo=ZoneInfo("Europe/Istanbul"))
        self.assertTrue(bot.should_skip_for_break_window(now_local, "14:00", "15:00"))

        after_resume = datetime(2026, 3, 2, 15, 10, tzinfo=ZoneInfo("Europe/Istanbul"))
        self.assertFalse(bot.should_skip_for_break_window(after_resume, "14:00", "15:00"))

    def test_should_skip_for_department_weekly_off(self) -> None:
        self.assertTrue(
            bot.should_skip_for_department_weekly_off("satis", "çarşamba", "çarşamba")
        )
        self.assertFalse(
            bot.should_skip_for_department_weekly_off("satis", "çarşamba", "salı")
        )
        self.assertFalse(
            bot.should_skip_for_department_weekly_off(None, "çarşamba", "çarşamba")
        )


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
            patch.object(bot.database, "get_break_window", return_value=(None, None)),
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

    async def test_monitor_job_skips_during_break_window(self) -> None:
        context = type("Ctx", (), {})()
        context.bot = type("DummyBot", (), {"send_message": AsyncMock()})()

        async def passthrough(func, *args, **kwargs):
            return func(*args, **kwargs)

        now_local = datetime(2026, 3, 2, 14, 30, tzinfo=ZoneInfo("Europe/Istanbul"))

        with (
            patch.object(bot, "db_call", new=passthrough),
            patch.object(bot, "is_within_monitor_hours", return_value=True),
            patch.object(bot, "get_now_local", return_value=now_local),
            patch.object(bot.database, "get_break_window", return_value=("14:00", "15:00")),
            patch.object(bot.database, "list_personnel") as list_personnel,
        ):
            await bot.monitor_job(context)

        context.bot.send_message.assert_not_awaited()
        list_personnel.assert_not_called()


class DailySummarySchedulerTests(unittest.IsolatedAsyncioTestCase):
    async def test_daily_summary_scheduler_sends_once_after_time(self) -> None:
        async def passthrough(func, *args, **kwargs):
            return func(*args, **kwargs)

        context = type("Ctx", (), {})()
        now_local = datetime(2026, 3, 2, 19, 35, tzinfo=ZoneInfo("Europe/Istanbul"))

        with (
            patch.object(bot, "db_call", new=passthrough),
            patch.object(bot, "get_now_local", return_value=now_local),
            patch.object(bot.database, "get_app_setting", return_value=None),
            patch.object(bot, "daily_summary_job", new=AsyncMock()) as daily_summary_job,
            patch.object(bot.database, "set_app_setting") as set_app_setting,
        ):
            await bot.daily_summary_scheduler_job(context)

        daily_summary_job.assert_awaited_once()
        set_app_setting.assert_called_once_with(
            bot.DAILY_SUMMARY_LAST_SENT_KEY,
            "2026-03-02",
        )

    async def test_daily_summary_scheduler_skips_if_already_sent_today(self) -> None:
        async def passthrough(func, *args, **kwargs):
            return func(*args, **kwargs)

        context = type("Ctx", (), {})()
        now_local = datetime(2026, 3, 2, 20, 5, tzinfo=ZoneInfo("Europe/Istanbul"))

        with (
            patch.object(bot, "db_call", new=passthrough),
            patch.object(bot, "get_now_local", return_value=now_local),
            patch.object(bot.database, "get_app_setting", return_value="2026-03-02"),
            patch.object(bot, "daily_summary_job", new=AsyncMock()) as daily_summary_job,
            patch.object(bot.database, "set_app_setting") as set_app_setting,
        ):
            await bot.daily_summary_scheduler_job(context)

        daily_summary_job.assert_not_awaited()
        set_app_setting.assert_not_called()


if __name__ == "__main__":
    unittest.main()
