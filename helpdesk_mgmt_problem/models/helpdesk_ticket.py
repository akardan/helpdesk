# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _


class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"

    # Problem Management relationships
    problem_ids = fields.Many2many(
        "helpdesk.problem",
        "problem_ticket_rel",
        "ticket_id",
        "problem_id",
        string="Related Problems",
        help="Problems related to this incident"
    )

    problem_count = fields.Integer(
        string="Problems",
        compute="_compute_problem_count"
    )

    known_error_id = fields.Many2one(
        "helpdesk.known.error",
        string="Known Error",
        tracking=True,
        help="Known error from KEDB matching this incident"
    )

    # Pattern detection flags
    recurring_issue = fields.Boolean(
        string="Recurring Issue",
        help="Marked as recurring issue by AI pattern detection"
    )

    similar_ticket_ids = fields.Many2many(
        "helpdesk.ticket",
        "ticket_similar_rel",
        "ticket_id",
        "similar_ticket_id",
        string="Similar Tickets",
        help="AI-detected similar tickets"
    )

    similar_ticket_count = fields.Integer(
        string="Similar Tickets",
        compute="_compute_similar_ticket_count"
    )

    @api.depends("problem_ids")
    def _compute_problem_count(self):
        for ticket in self:
            ticket.problem_count = len(ticket.problem_ids)

    @api.depends("similar_ticket_ids")
    def _compute_similar_ticket_count(self):
        for ticket in self:
            ticket.similar_ticket_count = len(ticket.similar_ticket_ids)

    def action_view_problems(self):
        """View related problems"""
        self.ensure_one()
        return {
            'name': _('Related Problems'),
            'type': 'ir.actions.act_window',
            'res_model': 'helpdesk.problem',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.problem_ids.ids)],
        }

    def action_create_problem(self):
        """Create a new problem from this ticket"""
        self.ensure_one()
        return {
            'name': _('Create Problem'),
            'type': 'ir.actions.act_window',
            'res_model': 'helpdesk.problem',
            'view_mode': 'form',
            'context': {
                'default_name': _('Problem: %s') % self.name,
                'default_description': self.description,
                'default_team_id': self.team_id.id,
                'default_category_id': self.category_id.id,
                'default_tag_ids': [(6, 0, self.tag_ids.ids)],
                'default_ticket_ids': [(6, 0, [self.id])],
            },
            'target': 'new'
        }

    def action_view_similar_tickets(self):
        """View similar tickets"""
        self.ensure_one()
        return {
            'name': _('Similar Tickets'),
            'type': 'ir.actions.act_window',
            'res_model': 'helpdesk.ticket',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.similar_ticket_ids.ids)],
        }

    def action_apply_known_error(self):
        """Manually apply a known error to this ticket"""
        self.ensure_one()
        return {
            'name': _('Apply Known Error'),
            'type': 'ir.actions.act_window',
            'res_model': 'helpdesk.known.error',
            'view_mode': 'tree,form',
            'domain': [('state', '=', 'active')],
            'context': {'ticket_id': self.id},
        }
