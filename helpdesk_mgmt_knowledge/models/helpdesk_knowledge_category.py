# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class HelpdeskKnowledgeCategory(models.Model):
    _name = "helpdesk.knowledge.category"
    _description = "Knowledge Base Category"
    _order = "sequence, name"
    _parent_name = "parent_id"
    _parent_store = True

    name = fields.Char(string="Category Name", required=True)
    parent_id = fields.Many2one("helpdesk.knowledge.category", string="Parent Category", ondelete="cascade")
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many("helpdesk.knowledge.category", "parent_id", string="Sub-Categories")
    sequence = fields.Integer(default=10)
    article_count = fields.Integer(string="Articles", compute="_compute_article_count")

    def _compute_article_count(self):
        for category in self:
            category.article_count = self.env["helpdesk.knowledge.article"].search_count([("category_id", "=", category.id)])
