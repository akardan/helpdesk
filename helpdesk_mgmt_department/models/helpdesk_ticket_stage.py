# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class HelpdeskTicketStage(models.Model):
    _inherit = "helpdesk.ticket.stage"

    # A stage can be restricted to specific teams.
    # Empty = shared across all teams (default Odoo behaviour).
    team_ids = fields.Many2many(
        "helpdesk.ticket.team",
        "helpdesk_stage_team_rel",
        "stage_id",
        "team_id",
        string="Restricted to Teams",
        help="If set, this stage is only visible for these teams. "
             "Leave empty to share across all teams.",
    )

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        """Show only the current team's stages (or globally shared stages) in Kanban."""
        team_id = (
            self.env.context.get("default_team_id")
            or self.env.context.get("search_default_team_id")
        )
        if team_id:
            return stages.filtered(
                lambda s: not s.team_ids or team_id in s.team_ids.ids
            )
        return super()._read_group_stage_ids(stages, domain, order)
