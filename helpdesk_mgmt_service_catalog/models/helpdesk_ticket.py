# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _


class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"

    service_item_id = fields.Many2one(
        "helpdesk.service.item",
        string="Service",
        tracking=True,
        help="The catalog service this ticket was raised for.",
    )

    service_category_id = fields.Many2one(
        related="service_item_id.service_category_id",
        string="Service Category",
        store=True,
        readonly=True,
    )

    # ── Approval ───────────────────────────────────────────────────────────────
    approval_state = fields.Selection(
        [
            ("not_required", "Not Required"),
            ("pending", "Pending Approval"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        string="Approval Status",
        default="not_required",
        tracking=True,
    )

    approver_id = fields.Many2one(
        "res.users",
        string="Approver",
        tracking=True,
    )

    approval_date = fields.Datetime(string="Approval Date", readonly=True)
    approval_notes = fields.Text(string="Approval Notes")

    # ── Checklist ──────────────────────────────────────────────────────────────
    checklist_ids = fields.One2many(
        "helpdesk.ticket.checklist",
        "ticket_id",
        string="Checklist",
    )

    checklist_progress = fields.Float(
        compute="_compute_checklist_progress",
        string="Checklist Progress (%)",
        store=True,
    )

    @api.depends("checklist_ids.done")
    def _compute_checklist_progress(self):
        for ticket in self:
            items = ticket.checklist_ids
            if items:
                ticket.checklist_progress = (
                    len(items.filtered("done")) / len(items)
                ) * 100
            else:
                ticket.checklist_progress = 0.0

    # ── Auto-populate from service item ───────────────────────────────────────
    @api.onchange("service_item_id")
    def _onchange_service_item_id(self):
        if not self.service_item_id:
            return
        item = self.service_item_id
        # Routing
        effective_team = item.get_effective_team()
        if effective_team:
            self.team_id = effective_team
        if item.default_user_id:
            self.user_id = item.default_user_id
        # Priority
        self.priority = item.default_priority
        # Approval
        if item.requires_approval:
            self.approval_state = "pending"
            self.approver_id = item.approval_user_id or (
                effective_team.user_id if effective_team else False
            )
        else:
            self.approval_state = "not_required"

    @api.model
    def create(self, vals):
        ticket = super().create(vals)
        if ticket.service_item_id:
            ticket._apply_service_item_defaults()
        return ticket

    def _apply_service_item_defaults(self):
        """Apply checklist template and set approval if needed."""
        self.ensure_one()
        item = self.service_item_id
        if not item:
            return

        # Create checklist items from template
        if item.checklist_template:
            lines = [l.strip() for l in item.checklist_template.splitlines() if l.strip()]
            for i, line in enumerate(lines, 1):
                self.env["helpdesk.ticket.checklist"].create(
                    {"ticket_id": self.id, "name": line, "sequence": i * 10}
                )

        # Set approval stage
        if item.requires_approval and item.approval_stage_id:
            self.write({"stage_id": item.approval_stage_id.id})

    # ── Approval actions ──────────────────────────────────────────────────────
    def action_approve(self):
        for ticket in self:
            ticket.write(
                {
                    "approval_state": "approved",
                    "approval_date": fields.Datetime.now(),
                }
            )
            ticket.message_post(
                body=_("Request approved by %s.") % self.env.user.name,
                message_type="notification",
            )

    def action_reject(self):
        for ticket in self:
            ticket.write({"approval_state": "rejected"})
            ticket.message_post(
                body=_("Request rejected by %s.") % self.env.user.name,
                message_type="notification",
            )


class HelpdeskTicketChecklist(models.Model):
    """Simple checklist line attached to a ticket."""

    _name = "helpdesk.ticket.checklist"
    _description = "Helpdesk Ticket Checklist Item"
    _order = "sequence, id"

    ticket_id = fields.Many2one(
        "helpdesk.ticket",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(string="Task", required=True)
    done = fields.Boolean(string="Done", default=False)
    done_by_id = fields.Many2one("res.users", string="Done By", readonly=True)
    done_date = fields.Datetime(string="Done Date", readonly=True)

    def toggle_done(self):
        for item in self:
            item.done = not item.done
            if item.done:
                item.done_by_id = self.env.user
                item.done_date = fields.Datetime.now()
            else:
                item.done_by_id = False
                item.done_date = False
