# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class HelpdeskTicketTeam(models.Model):
    _inherit = "helpdesk.ticket.team"

    # SLA Policy relationship
    sla_policy_ids = fields.One2many(
        "helpdesk.sla.policy",
        "team_id",
        string="SLA Policies"
    )

    sla_policy_count = fields.Integer(
        string="SLA Policies",
        compute="_compute_sla_policy_count"
    )

    # SLA Statistics
    sla_breached_count = fields.Integer(
        string="SLA Breached",
        compute="_compute_sla_stats"
    )

    sla_at_risk_count = fields.Integer(
        string="SLA At Risk",
        compute="_compute_sla_stats"
    )

    sla_success_rate = fields.Float(
        string="SLA Success Rate (%)",
        compute="_compute_sla_stats"
    )

    @api.depends("sla_policy_ids")
    def _compute_sla_policy_count(self):
        for team in self:
            team.sla_policy_count = len(team.sla_policy_ids)

    def _compute_sla_stats(self):
        """Compute SLA statistics for the team"""
        for team in self:
            tickets = self.env['helpdesk.ticket'].search([
                ('team_id', '=', team.id),
                ('stage_id.closed', '=', False)
            ])

            breached = tickets.filtered(lambda t: t.sla_status_display == 'breached')
            at_risk = tickets.filtered(lambda t: t.sla_status_display == 'at_risk')

            team.sla_breached_count = len(breached)
            team.sla_at_risk_count = len(at_risk)

            # Calculate success rate from closed tickets
            closed_tickets = self.env['helpdesk.ticket'].search([
                ('team_id', '=', team.id),
                ('stage_id.closed', '=', True),
                ('sla_active', '=', True)
            ])

            if closed_tickets:
                met = closed_tickets.filtered(lambda t: t.sla_status_display == 'met')
                team.sla_success_rate = (len(met) / len(closed_tickets)) * 100
            else:
                team.sla_success_rate = 0.0

    def action_view_sla_policies(self):
        """Open SLA policies for this team"""
        self.ensure_one()
        return {
            'name': 'SLA Policies',
            'type': 'ir.actions.act_window',
            'res_model': 'helpdesk.sla.policy',
            'view_mode': 'tree,form',
            'domain': [('team_id', '=', self.id)],
            'context': {'default_team_id': self.id}
        }
