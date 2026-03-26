# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _


class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"

    # ── Department (derived from the team's hr.department link) ───────────────
    hr_department_id = fields.Many2one(
        related="team_id.hr_department_id",
        string="Department",
        store=True,
        readonly=True,
    )

    hr_department_manager_id = fields.Many2one(
        related="team_id.hr_department_id.manager_id.user_id",
        string="Department Manager",
        store=False,
        readonly=True,
    )

    # ── Cross-department transfer history ─────────────────────────────────────
    transferred_from_team_id = fields.Many2one(
        "helpdesk.ticket.team",
        string="Transferred From",
        readonly=True,
        help="Original team when this ticket was transferred between departments.",
    )

    transfer_reason = fields.Text(
        string="Transfer Reason",
        help="Reason for inter-department transfer.",
    )

    # ── Stage domain helper ────────────────────────────────────────────────────
    available_stage_ids = fields.Many2many(
        "helpdesk.ticket.stage",
        compute="_compute_available_stage_ids",
        string="Available Stages",
    )

    @api.depends("team_id", "team_id.stage_ids")
    def _compute_available_stage_ids(self):
        all_stages = self.env["helpdesk.ticket.stage"].search([])
        for ticket in self:
            if ticket.team_id and ticket.team_id.stage_ids:
                ticket.available_stage_ids = ticket.team_id.stage_ids
            else:
                # Fall back to globally shared stages (no team restriction)
                ticket.available_stage_ids = all_stages.filtered(
                    lambda s: not s.team_ids
                )

    @api.onchange("team_id")
    def _onchange_team_id_stage(self):
        """Reset stage to first available stage of the new team."""
        if self.team_id and self.team_id.stage_ids:
            self.stage_id = self.team_id.stage_ids.sorted("sequence")[:1]

    def do_transfer(self, target_team_id, reason=""):
        """Transfer this ticket to another team/department."""
        for ticket in self:
            old_team = ticket.team_id
            ticket.write({
                "transferred_from_team_id": old_team.id,
                "transfer_reason": reason,
                "team_id": target_team_id,
                "user_id": False,
            })
            old_dept = old_team.hr_department_id.name or old_team.name
            new_dept = ticket.team_id.hr_department_id.name or ticket.team_id.name
            ticket.message_post(
                body=_(
                    "Ticket transferred from <b>%(from_dept)s</b> "
                    "to <b>%(to_dept)s</b>.<br/>Reason: %(reason)s",
                    from_dept=old_dept,
                    to_dept=new_dept,
                    reason=reason or _("N/A"),
                ),
                message_type="notification",
            )
