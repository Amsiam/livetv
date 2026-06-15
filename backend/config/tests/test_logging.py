import logging

from django.test import SimpleTestCase

from config.logging import ContextFormatter, build_logging_config
from config.log_extra import log_extra


class LoggingConfigTests(SimpleTestCase):
    def test_build_logging_config_has_app_loggers(self):
        config = build_logging_config(debug=False)
        self.assertIn("catalog", config["loggers"])
        self.assertIn("health", config["loggers"])
        self.assertEqual(config["loggers"]["catalog"]["level"], "INFO")

    def test_context_formatter_appends_extra_fields(self):
        formatter = ContextFormatter(
            fmt="%(levelname)s %(message)s",
        )
        record = logging.LogRecord(
            name="catalog.sync",
            level=logging.INFO,
            pathname="",
            lineno=1,
            msg="hello",
            args=(),
            exc_info=None,
        )
        for key, value in log_extra(component="catalog.sync", region="Bangladesh").items():
            setattr(record, key, value)
        formatted = formatter.format(record)
        self.assertIn("hello", formatted)
        self.assertIn("component='catalog.sync'", formatted)
        self.assertIn("region='Bangladesh'", formatted)

    def test_log_extra_renames_reserved_keys(self):
        extra = log_extra(created=5, component="catalog.sync")
        self.assertIn("stat_created", extra)
        self.assertNotIn("created", extra)
