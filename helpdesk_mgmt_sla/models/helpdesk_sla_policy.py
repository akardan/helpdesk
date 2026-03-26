# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class HelpdeskSLAPolicy(models.Model):
    _name = "helpdesk.sla.policy"
    _description = "Helpdesk SLA Policy"
    _order = "sequence, name"

    name = fields.Char(string="Policy Name", required=True, translate=True)
    description = fields.Text(string="Description", translate=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)

    # Team and criteria
    team_id = fields.Many2one(
        "helpdesk.ticket.team",
        string="Helpdesk Team",
        required=True,
        help="Team to which this SLA policy applies"
    )

    # ITIL Priority Matrix: Priority = f(Urgency, Impact)
    priority_ids = fields.Many2many(
        "helpdesk.ticket.priority",
        string="Priorities",
        help="SLA applies to tickets with these priorities. Leave empty for all priorities."
    )

    category_ids = fields.Many2many(
        "helpdesk.ticket.category",
        string="Categories",
        help="SLA applies to tickets with these categories. Leave empty for all categories."
    )

    tag_ids = fields.Many2many(
        "helpdesk.ticket.tag",
        string="Tags",
        help="SLA applies to tickets with these tags. Leave empty for all tags."
    )

    # SLA Targets (in working hours)
    response_time = fields.Float(
        string="Response Time (Hours)",
        required=True,
        default=4.0,
        help="Time limit for first response to the ticket"
    )

    resolution_time = fields.Float(
        string="Resolution Time (Hours)",
        required=True,
        default=24.0,
        help="Time limit for resolving the ticket"
    )

    # Escalation settings
    escalate_before_breach = fields.Boolean(
        string="Escalate Before Breach",
        default=True,
        help="Automatically escalate ticket before SLA breach"
    )

    escalation_threshold = fields.Float(
        string="Escalation Threshold (%)",
        default=80.0,
        help="Escalate when this percentage of SLA time has elapsed (e.g., 80%)"
    )

    escalation_user_ids = fields.Many2many(
        "res.users",
        "sla_policy_escalation_users_rel",
        "sla_policy_id",
        "user_id",
        string="Escalate To",
        help="Users to be notified when escalation is triggered"
    )

    # Working hours
    use_working_hours = fields.Boolean(
        string="Use Working Hours",
        default=True,
        help="Calculate SLA based on working hours instead of calendar hours"
    )

    resource_calendar_id = fields.Many2one(
        "resource.calendar",
        string="Working Hours",
        help="Working hours calendar for SLA calculation. If empty, uses company's default."
    )

    # Stage-based pause
    exclude_stage_ids = fields.Many2many(
        "helpdesk.ticket.stage",
        string="Pause SLA in Stages",
        help="SLA timer will be paused when ticket is in these stages (e.g., 'Waiting on Customer')"
    )

    # Statistics
    sla_status_count = fields.Integer(
        string="Active SLA Statuses",
        compute="_compute_sla_status_count"
    )

    success_rate = fields.Float(
        string="Success Rate (%)",
        compute="_compute_success_rate",
        store=False
    )

    @api.depends("team_id")
    def _compute_sla_status_count(self):
        for policy in self:
            policy.sla_status_count = self.env["helpdesk.sla.status"].search_count([
                ("sla_policy_id", "=", policy.id),
                ("ticket_id.stage_id.closed", "=", False)
            ])

    def _compute_success_rate(self):
        """Calculate SLA success rate (percentage of tickets meeting SLA)"""
        for policy in self:
            statuses = self.env["helpdesk.sla.status"].search([
                ("sla_policy_id", "=", policy.id),
                ("ticket_id.stage_id.closed", "=", True)
            ])

            if statuses:
                met_count = len(statuses.filtered(lambda s: s.response_sla_met and s.resolution_sla_met))
                policy.success_rate = (met_count / len(statuses)) * 100
            else:
                policy.success_rate = 0.0

    def match_ticket(self, ticket):
        """Check if this SLA policy matches the given ticket criteria"""
        self.ensure_one()

        # Check team
        if ticket.team_id != self.team_id:
            return False

        # Check priority
        if self.priority_ids and ticket.priority not in self.priority_ids.mapped('value'):
            return False

        # Check category
        if self.category_ids and ticket.category_id not in self.category_ids:
            return False

        # Check tags
        if self.tag_ids and not (self.tag_ids & ticket.tag_ids):
            return False

        return True

    def action_view_sla_statuses(self):
        """View SLA statuses for this policy"""
        self.ensure_one()
        return {
            'name': 'SLA Statuses',
            'type': 'ir.actions.act_window',
            'res_model': 'helpdesk.sla.status',
            'view_mode': 'tree,form',
            'domain': [('sla_policy_id', '=', self.id)],
            'context': {'default_sla_policy_id': self.id}
        }


class HelpdeskTicketPriority(models.Model):
    """Extended priority model for ITIL urgency/impact matrix"""
    _name = "helpdesk.ticket.priority"
    _description = "Helpdesk Ticket Priority"
    _order = "sequence"

    name = fields.Char(string="Priority Name", required=True, translate=True)
    value = fields.Selection([
        ('0', 'Low'),
        ('1', 'Medium'),
        ('2', 'High'),
        ('3', 'Critical')
    ], string="Priority Level", required=True, default='1')
    sequence = fields.Integer(default=10)
    description = fields.Text(string="Description")
    color = fields.Integer(string="Color Index", default=0)
