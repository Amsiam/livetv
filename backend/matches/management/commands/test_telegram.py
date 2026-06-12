from django.core.management.base import BaseCommand

from matches.notifications import send_telegram_message, telegram_configured


class Command(BaseCommand):
    help = "Send a test message to the configured Telegram chat."

    def handle(self, *args, **options):
        if not telegram_configured():
            self.stderr.write(
                self.style.ERROR(
                    "Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env first."
                )
            )
            return

        if send_telegram_message("✅ LiveTV backend — Telegram notifications are working."):
            self.stdout.write(self.style.SUCCESS("Test message sent."))
        else:
            self.stderr.write(self.style.ERROR("Failed to send test message. Check logs."))
