# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class HelpdeskServiceItem(models.Model):
    """A single service offering in the catalog (e.g. 'Request Laptop', 'Leave Application')."""

    _name = "helpdesk.service.item"
    _description = "Helpdesk Service Catalog Item"
    _inherit = ["mail.thread"]
    _order = "sequence, name"

    name = fields.Char(string="Service Name", required=True, translate=True, tracking=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    code = fields.Char(string="Service Code", help="Short code used in ticket number prefix (e.g. LPT → LPT-0001)")

    service_category_id = fields.Many2one(
        "helpdesk.service.category",
        string="Service Category",
        required=True,
        ondelete="cascade",
    )

    department_type = fields.Selection(
        related="service_category_id.department_type",
        store=True,
        readonly=True,
    )

    # ── Routing ────────────────────────────────────────────────────────────────
    team_id = fields.Many2one(
        "helpdesk.ticket.team",
        string="Responsible Team",
        help="Overrides the category's default team.",
    )

    default_user_id = fields.Many2one(
        "res.users",
        string="Default Assignee",
    )

    # ── SLA ────────────────────────────────────────────────────────────────────
    sla_response_hours = fields.Float(
        string="Response Time (h)",
        default=4.0,
        help="First-response target in working hours for this service.",
    )

    sla_resolution_hours = fields.Float(
        string="Resolution Time (h)",
        default=24.0,
        help="Resolution target in working hours for this service.",
    )

    # ── Priority ───────────────────────────────────────────────────────────────
    default_priority = fields.Selection(
        [("0", "Low"), ("1", "Medium"), ("2", "High"), ("3", "Very High")],
        string="Default Priority",
        default="1",
    )

    # ── Approval ───────────────────────────────────────────────────────────────
    requires_approval = fields.Boolean(
        string="Requires Approval",
        default=False,
        help="Tickets for this service need manager approval before processing.",
    )

    approval_user_id = fields.Many2one(
        "res.users",
        string="Approver",
        help="Default approver for this service. Falls back to team leader if empty.",
    )

    approval_stage_id = fields.Many2one(
        "helpdesk.ticket.stage",
        string="Approval Stage",
        help="Ticket moves to this stage while awaiting approval.",
    )

    # ── Description / Portal ───────────────────────────────────────────────────
    description = fields.Html(string="Service Description", translate=True)
    portal_visible = fields.Boolean(
        string="Visible in Portal",
        default=True,
        help="Show this service in the customer self-service portal.",
    )

    fulfillment_instructions = fields.Html(
        string="Fulfillment Instructions",
        translate=True,
        help="Internal step-by-step guide shown to the agent handling this service.",
    )

    # ── Checklist template ─────────────────────────────────────────────────────
    checklist_template = fields.Text(
        string="Default Checklist",
        help="Newline-separated checklist items auto-added when ticket is created from this service. "
             "e.g.:\nVerify identity\nPrepare equipment\nDeliver to user",
    )

    # ── Physical access ────────────────────────────────────────────────────────
    requires_physical_access = fields.Boolean(
        string="Requires Physical Access",
        default=False,
        help="When enabled the AI agent will automatically create an on-site sub-task.",
    )

    estimated_duration = fields.Float(
        string="Estimated Duration (h)",
        default=0.5,
    )

    # ── Statistics ─────────────────────────────────────────────────────────────
    ticket_count = fields.Integer(
        compute="_compute_ticket_count",
        string="Tickets",
    )

    avg_resolution_hours = fields.Float(
        compute="_compute_avg_resolution",
        string="Avg Resolution (h)",
    )

    @api.depends()
    def _compute_ticket_count(self):
        for item in self:
            item.ticket_count = self.env["helpdesk.ticket"].search_count(
                [("service_item_id", "=", item.id)]
            )

    @api.depends()
    def _compute_avg_resolution(self):
        for item in self:
            tickets = self.env["helpdesk.ticket"].search(
                [("service_item_id", "=", item.id), ("stage_id.closed", "=", True)]
            )
            if tickets:
                total = sum(
                    (t.closed_date - t.create_date).total_seconds() / 3600
                    for t in tickets
                    if t.closed_date and t.create_date
                )
                item.avg_resolution_hours = total / len(tickets)
            else:
                item.avg_resolution_hours = 0.0

    def get_effective_team(self):
        """Return the team that should handle this service item."""
        self.ensure_one()
        return self.team_id or self.service_category_id.team_id
