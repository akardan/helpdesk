# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _


class HelpdeskKnownError(models.Model):
    _name = "helpdesk.known.error"
    _description = "Known Error Database (ITIL)"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char(
        string="Known Error Title",
        required=True,
        tracking=True
    )

    number = fields.Char(
        string="KE Number",
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: _("New")
    )

    description = fields.Html(
        string="Error Description",
        tracking=True
    )

    # ITIL States
    state = fields.Selection([
        ('active', 'Active'),
        ('obsolete', 'Obsolete'),
        ('resolved', 'Resolved')
    ], string="State", default='active', required=True, tracking=True)

    # Root Cause and Solutions
    root_cause = fields.Html(
        string="Root Cause",
        required=True,
        tracking=True,
        help="Known root cause of the error"
    )

    workaround = fields.Html(
        string="Workaround",
        tracking=True,
        help="Temporary workaround to apply when this error occurs"
    )

    solution = fields.Html(
        string="Permanent Solution",
        tracking=True,
        help="Permanent solution to fix this error"
    )

    # Relationships
    problem_id = fields.Many2one(
        "helpdesk.problem",
        string="Related Problem",
        tracking=True,
        ondelete="set null"
    )

    ticket_ids = fields.Many2many(
        "helpdesk.ticket",
        "known_error_ticket_rel",
        "known_error_id",
        "ticket_id",
        string="Affected Tickets"
    )

    ticket_count = fields.Integer(
        string="Affected Tickets",
        compute="_compute_ticket_count"
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

    # Severity and Impact
    severity = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical')
    ], string="Severity", default='medium', tracking=True)

    affected_users_estimate = fields.Integer(
        string="Estimated Affected Users"
    )

    # Search optimization
    symptom_keywords = fields.Char(
        string="Symptom Keywords",
        help="Keywords to help match tickets with this known error"
    )

    # Dates
    create_date = fields.Datetime(
        string="Identified On",
        readonly=True
    )

    resolved_date = fields.Datetime(
        string="Resolved Date",
        tracking=True
    )

    # Usage statistics
    usage_count = fields.Integer(
        string="Times Applied",
        default=0,
        help="Number of times this known error was applied to tickets"
    )

    last_used_date = fields.Datetime(
        string="Last Used",
        help="Last time this known error was applied"
    )

    # AI matching
    ai_match_enabled = fields.Boolean(
        string="Enable AI Matching",
        default=True,
        help="Allow AI to automatically suggest this known error for matching tickets"
    )

    @api.depends("ticket_ids")
    def _compute_ticket_count(self):
        for error in self:
            error.ticket_count = len(error.ticket_ids)

    @api.model
    def create(self, vals):
        """Generate known error number on creation"""
        if vals.get("number", _("New")) == _("New"):
            vals["number"] = self.env["ir.sequence"].next_by_code(
                "helpdesk.known.error"
            ) or _("New")
        return super().create(vals)

    def write(self, vals):
        """Track state transitions"""
        if 'state' in vals:
            if vals['state'] == 'resolved' and not self.resolved_date:
                vals['resolved_date'] = fields.Datetime.now()

        return super().write(vals)

    def action_mark_active(self):
        """Mark known error as active"""
        self.write({'state': 'active'})

    def action_mark_obsolete(self):
        """Mark known error as obsolete"""
        self.write({'state': 'obsolete'})

    def action_mark_resolved(self):
        """Mark known error as resolved"""
        self.write({
            'state': 'resolved',
            'resolved_date': fields.Datetime.now()
        })

    def action_view_tickets(self):
        """View affected tickets"""
        self.ensure_one()
        return {
            'name': _('Affected Tickets'),
            'type': 'ir.actions.act_window',
            'res_model': 'helpdesk.ticket',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.ticket_ids.ids)],
        }

    def apply_to_ticket(self, ticket):
        """Apply this known error to a ticket"""
        self.ensure_one()
        ticket.write({
            'known_error_id': self.id,
        })

        # Post message to ticket
        ticket.message_post(
            body=_('Known Error Applied: %s<br/>Workaround: %s') % (
                self.name,
                self.workaround or _('No workaround available')
            ),
            subject=_('Known Error Applied'),
            message_type='notification'
        )

        # Update usage statistics
        self.write({
            'usage_count': self.usage_count + 1,
            'last_used_date': fields.Datetime.now()
        })

    @api.model
    def search_matching_known_errors(self, ticket):
        """Search for known errors matching a ticket (for AI agent)"""
        # This will be enhanced by AI agent
        # Basic keyword matching for now
        domain = [('state', '=', 'active')]

        if ticket.category_id:
            domain.append(('category_id', '=', ticket.category_id.id))

        return self.search(domain, limit=10)
