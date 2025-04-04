from odoo import models
from collections import defaultdict
from odoo.tools.float_utils import float_round
import logging

_logger = logging.getLogger(__name__)


class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    def _get_attendance_intervals_days_data(self, attendance_intervals):
        """
        Override of resource.calendar's method to safely handle
        division by zero if attendance intervals meta data is broken.
        """
        day_hours = defaultdict(float)
        day_days = defaultdict(float)

        for start, stop, meta in attendance_intervals:
            interval_hours = (stop - start).total_seconds() / 3600
            day_hours[start.date()] += interval_hours

            if len(self) == 1 and self.flexible_hours:
                day_days[start.date()] += interval_hours / self.hours_per_day if self.hours_per_day else 0
            else:
                total_duration_hours = sum(meta.mapped('duration_hours'))
                if total_duration_hours:
                    day_days[start.date()] += sum(meta.mapped('duration_days')) * interval_hours / total_duration_hours
                else:
                    _logger.warning(
                        "Skipping attendance interval with zero total_duration_hours at %s. Interval meta: %s",
                        start.date(), meta
                    )
                    day_days[start.date()] += 0

        return {
            'days': float_round(sum(day_days[day] for day in day_days), precision_rounding=0.001),
            'hours': sum(day_hours.values()),
        }
