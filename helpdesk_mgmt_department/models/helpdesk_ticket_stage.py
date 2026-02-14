# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class HelpdeskTicketStage(models.Model):
    _inherit = "helpdesk.ticket.stage"

    # Bir aşama belirli team'lere kısıtlanabilir.
    # Boş bırakılırsa (mevcut davranış) tüm team'ler görür.
    team_ids = fields.Many2many(
        "helpdesk.ticket.team",
        "helpdesk_stage_team_rel",
        "stage_id",
        "team_id",
        string="Restricted to Teams",
        help="If set, this stage is only visible for these teams. "
             "Leave empty to share across all teams (default behaviour).",
    )

    department_type = fields.Selection(
        [
            ("all", "All Departments"),
            ("it", "Information Technology"),
            ("hr", "Human Resources"),
            ("finance", "Finance & Accounting"),
            ("facilities", "Facilities & Maintenance"),
            ("legal", "Legal & Compliance"),
            ("marketing", "Marketing & Communications"),
            ("logistics", "Logistics & Supply Chain"),
            ("customer_service", "Customer Service"),
            ("general", "General Services"),
        ],
        string="Department Type",
        default="all",
        help="Department type this stage belongs to. "
             "Used as a template when creating per-team stages.",
    )

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        """Override: when viewing kanban for a specific team, only show that
        team's stages (or stages with no team restriction)."""
        team_id = self.env.context.get("default_team_id") or self.env.context.get(
            "search_default_team_id"
        )
        if team_id:
            return stages.filtered(
                lambda s: not s.team_ids or team_id in s.team_ids.ids
            )
        return super()._read_group_stage_ids(stages, domain, order)
