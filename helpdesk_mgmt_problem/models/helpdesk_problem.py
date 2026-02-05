# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _


class HelpdeskProblem(models.Model):
    _name = "helpdesk.problem"
    _description = "Helpdesk Problem (ITIL)"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "priority desc, create_date desc"

    name = fields.Char(
        string="Problem Summary",
        required=True,
        tracking=True
    )

    number = fields.Char(
        string="Problem Number",
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: _("New")
    )

    description = fields.Html(
        string="Problem Description",
        tracking=True,
        help="Detailed description of the problem"
    )

    # ITIL Problem States
    state = fields.Selection([
        ('identified', 'Identified'),
        ('investigation', 'Under Investigation'),
        ('root_cause_found', 'Root Cause Found'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
        ('cancelled', 'Cancelled')
    ], string="State", default='identified', required=True, tracking=True)

    # Priority
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Medium'),
        ('2', 'High'),
        ('3', 'Critical')
    ], string="Priority", default='1', tracking=True)

    # Root Cause Analysis
    root_cause = fields.Html(
        string="Root Cause",
        tracking=True,
        help="Identified root cause of the problem"
    )

    root_cause_date = fields.Datetime(
        string="Root Cause Identified Date",
        tracking=True
    )

    # Solution/Workaround
    solution = fields.Html(
        string="Permanent Solution",
        tracking=True,
        help="Permanent solution to fix the root cause"
    )

    workaround = fields.Html(
        string="Workaround",
        tracking=True,
        help="Temporary workaround to mitigate the problem impact"
    )

    # Assignment
    team_id = fields.Many2one(
        "helpdesk.ticket.team",
        string="Team",
        tracking=True
    )

    user_id = fields.Many2one(
        "res.users",
        string="Assigned To",
        tracking=True,
        domain="[('id', 'in', team_user_ids)]"
    )

    team_user_ids = fields.Many2many(
        "res.users",
        related="team_id.user_ids",
        string="Team Members"
    )

    # Related Items
    ticket_ids = fields.Many2many(
        "helpdesk.ticket",
        "problem_ticket_rel",
        "problem_id",
        "ticket_id",
        string="Related Tickets",
        help="Incidents related to this problem"
    )

    ticket_count = fields.Integer(
        string="Related Tickets",
        compute="_compute_ticket_count"
    )

    known_error_id = fields.Many2one(
        "helpdesk.known.error",
        string="Known Error",
        help="Known Error Database entry for this problem"
    )

    # Category and Tags
    category_id = fields.Many2one(
        "helpdesk.ticket.category",
        string="Category",
        tracking=True
    )

    tag_ids = fields.Many2many(
        "helpdesk.ticket.tag",
        string="Tags"
    )

    # Dates
    create_date = fields.Datetime(
        string="Created On",
        readonly=True
    )

    resolution_date = fields.Datetime(
        string="Resolution Date",
        tracking=True
    )

    closed_date = fields.Datetime(
        string="Closed Date",
        tracking=True
    )

    # Impact Analysis
    affected_users_count = fields.Integer(
        string="Affected Users",
        help="Estimated number of affected users"
    )

    business_impact = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical')
    ], string="Business Impact", tracking=True)

    # AI Analysis fields
    pattern_detected = fields.Boolean(
        string="Pattern Detected by AI",
        help="AI detected recurring pattern in tickets"
    )

    ai_confidence_score = fields.Float(
        string="AI Confidence Score",
        help="AI confidence in root cause identification (0-100%)"
    )

    ai_suggested_solution = fields.Html(
        string="AI Suggested Solution"
    )

    # Color for kanban
    color = fields.Integer(string="Color Index")

    @api.depends("ticket_ids")
    def _compute_ticket_count(self):
        for problem in self:
            problem.ticket_count = len(problem.ticket_ids)

    @api.model
    def create(self, vals):
        """Generate problem number on creation"""
        if vals.get("number", _("New")) == _("New"):
            vals["number"] = self.env["ir.sequence"].next_by_code(
                "helpdesk.problem"
            ) or _("New")
        return super().create(vals)

    def write(self, vals):
        """Track state transitions"""
        if 'state' in vals:
            # Track root cause found date
            if vals['state'] == 'root_cause_found' and not self.root_cause_date:
                vals['root_cause_date'] = fields.Datetime.now()

            # Track resolution date
            if vals['state'] == 'resolved' and not self.resolution_date:
                vals['resolution_date'] = fields.Datetime.now()

            # Track closed date
            if vals['state'] == 'closed' and not self.closed_date:
                vals['closed_date'] = fields.Datetime.now()

        return super().write(vals)

    def action_start_investigation(self):
        """Start problem investigation"""
        self.write({'state': 'investigation'})

    def action_root_cause_found(self):
        """Mark root cause as found"""
        self.write({
            'state': 'root_cause_found',
            'root_cause_date': fields.Datetime.now()
        })

    def action_resolve(self):
        """Mark problem as resolved"""
        self.write({
            'state': 'resolved',
            'resolution_date': fields.Datetime.now()
        })

    def action_close(self):
        """Close problem"""
        self.write({
            'state': 'closed',
            'closed_date': fields.Datetime.now()
        })

    def action_cancel(self):
        """Cancel problem"""
        self.write({'state': 'cancelled'})

    def action_view_tickets(self):
        """View related tickets"""
        self.ensure_one()
        return {
            'name': _('Related Tickets'),
            'type': 'ir.actions.act_window',
            'res_model': 'helpdesk.ticket',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.ticket_ids.ids)],
            'context': {'default_problem_id': self.id}
        }

    def action_create_known_error(self):
        """Create known error from this problem"""
        self.ensure_one()
        return {
            'name': _('Create Known Error'),
            'type': 'ir.actions.act_window',
            'res_model': 'helpdesk.known.error',
            'view_mode': 'form',
            'context': {
                'default_problem_id': self.id,
                'default_name': self.name,
                'default_description': self.description,
                'default_root_cause': self.root_cause,
                'default_workaround': self.workaround,
                'default_solution': self.solution,
            },
            'target': 'new'
        }

    @api.model
    def detect_recurring_patterns(self):
        """AI method to detect recurring patterns in tickets and create problems"""
        # This will be implemented with AI agent
        # Placeholder for AI pattern detection
        pass
