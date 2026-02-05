# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, _


class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"

    knowledge_article_ids = fields.Many2many(
        "helpdesk.knowledge.article",
        "article_ticket_rel",
        "ticket_id",
        "article_id",
        string="Suggested Articles"
    )

    article_count = fields.Integer(string="Articles", compute="_compute_article_count")

    def _compute_article_count(self):
        for ticket in self:
            ticket.article_count = len(ticket.knowledge_article_ids)

    def action_view_knowledge_articles(self):
        self.ensure_one()
        return {
            'name': _('Suggested Knowledge Articles'),
            'type': 'ir.actions.act_window',
            'res_model': 'helpdesk.knowledge.article',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.knowledge_article_ids.ids)],
        }
