# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import timedelta
from odoo import api, fields, models, _


class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"

    # SLA Status relationship
    sla_status_ids = fields.One2many(
        "helpdesk.sla.status",
        "ticket_id",
        string="SLA Statuses"
    )

    sla_active = fields.Boolean(
        string="SLA Active",
        compute="_compute_sla_active",
        store=True
    )

    sla_deadline_response = fields.Datetime(
        string="Response Deadline",
        compute="_compute_sla_deadlines",
        store=True,
        help="Earliest response deadline from active SLAs"
    )

    sla_deadline_resolution = fields.Datetime(
        string="Resolution Deadline",
        compute="_compute_sla_deadlines",
        store=True,
        help="Earliest resolution deadline from active SLAs"
    )

    sla_status_display = fields.Selection([
        ('met', 'SLA Met'),
        ('at_risk', 'At Risk'),
        ('breached', 'Breached'),
        ('none', 'No SLA')
    ], string="SLA Status", compute="_compute_sla_status_display", store=True)

    sla_color = fields.Integer(
        string="SLA Color",
        compute="_compute_sla_status_display"
    )

    # First response tracking
    first_response_date = fields.Datetime(
        string="First Response Date",
        help="Date of first staff response"
    )

    # Resolution tracking
    resolution_date = fields.Datetime(
        string="Resolution Date",
        help="Date when ticket was resolved"
    )

    @api.depends("sla_status_ids")
    def _compute_sla_active(self):
        for ticket in self:
            ticket.sla_active = bool(ticket.sla_status_ids)

    @api.depends("sla_status_ids.deadline_response", "sla_status_ids.deadline_resolution")
    def _compute_sla_deadlines(self):
        for ticket in self:
            active_statuses = ticket.sla_status_ids.filtered(
                lambda s: not s.resolution_date
            )

            if active_statuses:
                # Get earliest response deadline
                response_deadlines = active_statuses.filtered(
                    lambda s: s.deadline_response and not s.response_date
                ).mapped('deadline_response')
                ticket.sla_deadline_response = min(response_deadlines) if response_deadlines else False

                # Get earliest resolution deadline
                resolution_deadlines = active_statuses.mapped('deadline_resolution')
                ticket.sla_deadline_resolution = min(resolution_deadlines) if resolution_deadlines else False
            else:
                ticket.sla_deadline_response = False
                ticket.sla_deadline_resolution = False

    @api.depends("sla_status_ids.overall_sla_status", "sla_active")
    def _compute_sla_status_display(self):
        for ticket in self:
            if not ticket.sla_active:
                ticket.sla_status_display = 'none'
                ticket.sla_color = 0
            else:
                statuses = ticket.sla_status_ids.mapped('overall_sla_status')
                if 'breached' in statuses:
                    ticket.sla_status_display = 'breached'
                    ticket.sla_color = 1  # Red
                elif 'at_risk' in statuses:
                    ticket.sla_status_display = 'at_risk'
                    ticket.sla_color = 3  # Orange
                else:
                    ticket.sla_status_display = 'met'
                    ticket.sla_color = 10  # Green

    @api.model
    def create(self, vals):
        """Create ticket and apply matching SLA policies"""
        ticket = super().create(vals)
        ticket._apply_sla_policies()
        return ticket

    def write(self, vals):
        """Track important events for SLA: first response, resolution, stage changes"""
        result = super().write(vals)

        # Track first response
        if 'message_ids' in vals or 'user_id' in vals:
            self._check_first_response()

        # Track resolution
        if 'stage_id' in vals:
            self._check_resolution()
            self._check_sla_pause()

        # Re-apply SLA if critical fields change
        if any(field in vals for field in ['team_id', 'priority', 'category_id', 'tag_ids']):
            self._apply_sla_policies()

        return result

    def _apply_sla_policies(self):
        """Find and apply matching SLA policies to this ticket"""
        SLAStatus = self.env['helpdesk.sla.status']

        for ticket in self:
            # Skip if ticket is already closed
            if ticket.stage_id.closed:
                continue

            # Find matching SLA policies
            policies = self.env['helpdesk.sla.policy'].search([
                ('active', '=', True),
                ('team_id', '=', ticket.team_id.id)
            ])

            for policy in policies:
                if policy.match_ticket(ticket):
                    # Check if SLA status already exists
                    existing = SLAStatus.search([
                        ('ticket_id', '=', ticket.id),
                        ('sla_policy_id', '=', policy.id)
                    ], limit=1)

                    if not existing:
                        # Create new SLA status
                        ticket._create_sla_status(policy)

    def _create_sla_status(self, policy):
        """Create SLA status record for this ticket and policy"""
        self.ensure_one()

        # Calculate deadlines
        response_deadline = self._calculate_deadline(
            self.create_date,
            policy.response_time,
            policy
        )

        resolution_deadline = self._calculate_deadline(
            self.create_date,
            policy.resolution_time,
            policy
        )

        # Create SLA status
        return self.env['helpdesk.sla.status'].create({
            'ticket_id': self.id,
            'sla_policy_id': policy.id,
            'response_time_target': policy.response_time,
            'resolution_time_target': policy.resolution_time,
            'deadline_response': response_deadline,
            'deadline_resolution': resolution_deadline,
        })

    def _calculate_deadline(self, start_date, hours, policy):
        """Calculate deadline considering working hours if configured"""
        if not start_date or not hours:
            return False

        # For now, use simple calendar calculation
        # TODO: Implement working hours calculation using resource.calendar
        deadline = start_date + timedelta(hours=hours)
        return deadline

    def _check_first_response(self):
        """Check if this is the first staff response and update SLA"""
        for ticket in self:
            if not ticket.first_response_date:
                # Check if there's a message from a staff member (not customer)
                staff_messages = ticket.message_ids.filtered(
                    lambda m: m.message_type == 'comment'
                    and m.author_id != ticket.partner_id
                    and m.create_date > ticket.create_date
                )

                if staff_messages:
                    first_response = min(staff_messages.mapped('create_date'))
                    ticket.write({'first_response_date': first_response})

                    # Update SLA statuses
                    for sla_status in ticket.sla_status_ids:
                        if not sla_status.response_date:
                            sla_status.write({'response_date': first_response})

    def _check_resolution(self):
        """Check if ticket is resolved and update SLA"""
        for ticket in self:
            if ticket.stage_id.closed and not ticket.resolution_date:
                resolution_date = fields.Datetime.now()
                ticket.write({'resolution_date': resolution_date})

                # Update SLA statuses
                for sla_status in ticket.sla_status_ids:
                    if not sla_status.resolution_date:
                        sla_status.write({'resolution_date': resolution_date})

    def _check_sla_pause(self):
        """Check if SLA should be paused or resumed based on stage"""
        for ticket in self:
            for sla_status in ticket.sla_status_ids:
                policy = sla_status.sla_policy_id

                # Check if current stage requires SLA pause
                should_pause = ticket.stage_id in policy.exclude_stage_ids

                if should_pause and not sla_status.paused:
                    sla_status.pause_sla()
                elif not should_pause and sla_status.paused:
                    sla_status.resume_sla()

    def action_view_sla_status(self):
        """Open SLA status view for this ticket"""
        self.ensure_one()
        return {
            'name': _('SLA Status'),
            'type': 'ir.actions.act_window',
            'res_model': 'helpdesk.sla.status',
            'view_mode': 'tree,form',
            'domain': [('ticket_id', '=', self.id)],
            'context': {'default_ticket_id': self.id}
        }

    @api.model
    def cron_apply_sla_policies(self):
        """Cron job to apply SLA policies to tickets without SLA"""
        # Find open tickets without SLA
        tickets = self.search([
            ('stage_id.closed', '=', False),
            ('sla_active', '=', False)
        ])

        for ticket in tickets:
            ticket._apply_sla_policies()
