# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import timedelta
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HelpdeskSLAStatus(models.Model):
    _name = "helpdesk.sla.status"
    _description = "Helpdesk SLA Status Tracking"
    _order = "deadline_response"
    _rec_name = "ticket_id"

    ticket_id = fields.Many2one(
        "helpdesk.ticket",
        string="Ticket",
        required=True,
        ondelete="cascade",
        index=True
    )

    sla_policy_id = fields.Many2one(
        "helpdesk.sla.policy",
        string="SLA Policy",
        required=True,
        ondelete="restrict"
    )

    # Response SLA tracking
    response_time_target = fields.Float(
        string="Response Time Target (Hours)",
        help="Target response time from SLA policy"
    )

    response_time_actual = fields.Float(
        string="Actual Response Time (Hours)",
        compute="_compute_actual_times",
        store=True,
        help="Actual time taken for first response"
    )

    deadline_response = fields.Datetime(
        string="Response Deadline",
        help="Deadline for first response"
    )

    response_date = fields.Datetime(
        string="First Response Date",
        help="Date of first response to the ticket"
    )

    response_sla_met = fields.Boolean(
        string="Response SLA Met",
        compute="_compute_sla_met",
        store=True
    )

    response_sla_status = fields.Selection([
        ('achieved', 'Achieved'),
        ('in_progress', 'In Progress'),
        ('escalated', 'Escalated'),
        ('breached', 'Breached')
    ], string="Response Status", compute="_compute_sla_status", store=True)

    # Resolution SLA tracking
    resolution_time_target = fields.Float(
        string="Resolution Time Target (Hours)",
        help="Target resolution time from SLA policy"
    )

    resolution_time_actual = fields.Float(
        string="Actual Resolution Time (Hours)",
        compute="_compute_actual_times",
        store=True,
        help="Actual time taken for resolution"
    )

    deadline_resolution = fields.Datetime(
        string="Resolution Deadline",
        help="Deadline for ticket resolution"
    )

    resolution_date = fields.Datetime(
        string="Resolution Date",
        help="Date when ticket was resolved"
    )

    resolution_sla_met = fields.Boolean(
        string="Resolution SLA Met",
        compute="_compute_sla_met",
        store=True
    )

    resolution_sla_status = fields.Selection([
        ('achieved', 'Achieved'),
        ('in_progress', 'In Progress'),
        ('escalated', 'Escalated'),
        ('breached', 'Breached')
    ], string="Resolution Status", compute="_compute_sla_status", store=True)

    # Overall status
    overall_sla_status = fields.Selection([
        ('met', 'Met'),
        ('at_risk', 'At Risk'),
        ('breached', 'Breached')
    ], string="Overall SLA Status", compute="_compute_overall_status", store=True)

    # Escalation tracking
    escalated = fields.Boolean(string="Escalated", default=False)
    escalation_date = fields.Datetime(string="Escalation Date")
    escalation_reason = fields.Text(string="Escalation Reason")

    # Pause tracking
    paused = fields.Boolean(string="SLA Paused", default=False)
    pause_start_date = fields.Datetime(string="Pause Start Date")
    total_pause_duration = fields.Float(
        string="Total Pause Duration (Hours)",
        default=0.0,
        help="Total time SLA has been paused"
    )

    # Progress indicators
    response_progress = fields.Float(
        string="Response Progress (%)",
        compute="_compute_progress"
    )

    resolution_progress = fields.Float(
        string="Resolution Progress (%)",
        compute="_compute_progress"
    )

    # Color coding for kanban/tree views
    color = fields.Integer(string="Color Index", compute="_compute_color")

    @api.depends("ticket_id.create_date", "response_date", "resolution_date")
    def _compute_actual_times(self):
        """Calculate actual response and resolution times"""
        for status in self:
            if status.response_date and status.ticket_id.create_date:
                delta = status.response_date - status.ticket_id.create_date
                status.response_time_actual = delta.total_seconds() / 3600
            else:
                status.response_time_actual = 0.0

            if status.resolution_date and status.ticket_id.create_date:
                delta = status.resolution_date - status.ticket_id.create_date
                status.resolution_time_actual = delta.total_seconds() / 3600
            else:
                status.resolution_time_actual = 0.0

    @api.depends("response_date", "deadline_response", "resolution_date", "deadline_resolution")
    def _compute_sla_met(self):
        """Determine if SLA targets were met"""
        for status in self:
            # Response SLA
            if status.response_date:
                status.response_sla_met = status.response_date <= status.deadline_response
            else:
                status.response_sla_met = False

            # Resolution SLA
            if status.resolution_date:
                status.resolution_sla_met = status.resolution_date <= status.deadline_resolution
            else:
                status.resolution_sla_met = False

    @api.depends("response_sla_met", "deadline_response", "response_date", "escalated")
    def _compute_sla_status(self):
        """Calculate detailed SLA status for response and resolution"""
        now = fields.Datetime.now()

        for status in self:
            # Response status
            if status.response_date:
                status.response_sla_status = 'achieved' if status.response_sla_met else 'breached'
            elif status.escalated:
                status.response_sla_status = 'escalated'
            elif now > status.deadline_response:
                status.response_sla_status = 'breached'
            else:
                status.response_sla_status = 'in_progress'

            # Resolution status
            if status.resolution_date:
                status.resolution_sla_status = 'achieved' if status.resolution_sla_met else 'breached'
            elif status.escalated:
                status.resolution_sla_status = 'escalated'
            elif now > status.deadline_resolution:
                status.resolution_sla_status = 'breached'
            else:
                status.resolution_sla_status = 'in_progress'

    @api.depends("response_sla_status", "resolution_sla_status")
    def _compute_overall_status(self):
        """Calculate overall SLA status"""
        for status in self:
            if 'breached' in (status.response_sla_status, status.resolution_sla_status):
                status.overall_sla_status = 'breached'
            elif 'escalated' in (status.response_sla_status, status.resolution_sla_status):
                status.overall_sla_status = 'at_risk'
            else:
                status.overall_sla_status = 'met'

    @api.depends("deadline_response", "deadline_resolution", "response_date", "resolution_date")
    def _compute_progress(self):
        """Calculate progress percentages for response and resolution"""
        now = fields.Datetime.now()

        for status in self:
            # Response progress
            if status.response_date:
                status.response_progress = 100.0
            elif status.ticket_id.create_date and status.deadline_response:
                total_time = (status.deadline_response - status.ticket_id.create_date).total_seconds()
                elapsed_time = (now - status.ticket_id.create_date).total_seconds()
                if total_time > 0:
                    status.response_progress = min((elapsed_time / total_time) * 100, 100)
                else:
                    status.response_progress = 0.0
            else:
                status.response_progress = 0.0

            # Resolution progress
            if status.resolution_date:
                status.resolution_progress = 100.0
            elif status.ticket_id.create_date and status.deadline_resolution:
                total_time = (status.deadline_resolution - status.ticket_id.create_date).total_seconds()
                elapsed_time = (now - status.ticket_id.create_date).total_seconds()
                if total_time > 0:
                    status.resolution_progress = min((elapsed_time / total_time) * 100, 100)
                else:
                    status.resolution_progress = 0.0
            else:
                status.resolution_progress = 0.0

    @api.depends("overall_sla_status", "resolution_progress")
    def _compute_color(self):
        """Color coding for visual indicators"""
        for status in self:
            if status.overall_sla_status == 'breached':
                status.color = 1  # Red
            elif status.overall_sla_status == 'at_risk' or status.resolution_progress >= 80:
                status.color = 3  # Yellow/Orange
            else:
                status.color = 10  # Green

    def pause_sla(self):
        """Pause SLA timer"""
        for status in self:
            if not status.paused:
                status.write({
                    'paused': True,
                    'pause_start_date': fields.Datetime.now()
                })

    def resume_sla(self):
        """Resume SLA timer and update deadlines"""
        for status in self:
            if status.paused and status.pause_start_date:
                pause_duration = fields.Datetime.now() - status.pause_start_date
                pause_hours = pause_duration.total_seconds() / 3600

                # Update total pause duration
                status.total_pause_duration += pause_hours

                # Extend deadlines by pause duration
                if status.deadline_response:
                    status.deadline_response += pause_duration
                if status.deadline_resolution:
                    status.deadline_resolution += pause_duration

                status.write({
                    'paused': False,
                    'pause_start_date': False
                })

    def trigger_escalation(self, reason=None):
        """Manually trigger escalation"""
        for status in self:
            if not status.escalated:
                status.write({
                    'escalated': True,
                    'escalation_date': fields.Datetime.now(),
                    'escalation_reason': reason or _('Manual escalation triggered')
                })

                # Notify escalation users
                if status.sla_policy_id.escalation_user_ids:
                    status.ticket_id.message_post(
                        body=_('SLA Escalation: %s') % (reason or _('SLA at risk')),
                        subject=_('SLA Escalation - Ticket %s') % status.ticket_id.name,
                        partner_ids=status.sla_policy_id.escalation_user_ids.mapped('partner_id').ids,
                        message_type='notification'
                    )

    def check_escalation_needed(self):
        """Check if escalation is needed based on threshold"""
        for status in self:
            if (status.sla_policy_id.escalate_before_breach
                and not status.escalated
                and not status.resolution_date):

                threshold = status.sla_policy_id.escalation_threshold

                if status.resolution_progress >= threshold:
                    status.trigger_escalation(
                        reason=_('Automatic escalation: %d%% of resolution time elapsed') % threshold
                    )

    @api.model
    def cron_check_sla_escalation(self):
        """Cron job to check SLA escalation needs"""
        # Find all active SLA statuses that need escalation check
        active_statuses = self.search([
            ('ticket_id.stage_id.closed', '=', False),
            ('resolution_date', '=', False),
            ('escalated', '=', False)
        ])

        for status in active_statuses:
            status.check_escalation_needed()
