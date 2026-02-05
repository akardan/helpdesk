# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _


class HelpdeskKnowledgeArticle(models.Model):
    _name = "helpdesk.knowledge.article"
    _description = "Helpdesk Knowledge Base Article"
    _inherit = ["mail.thread", "mail.activity.mixin", "portal.mixin"]
    _order = "sequence, name"

    name = fields.Char(string="Title", required=True, tracking=True)
    number = fields.Char(string="Article Number", required=True, copy=False, readonly=True, default=lambda self: _("New"))
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    # Content
    description = fields.Html(string="Short Description")
    content = fields.Html(string="Content", required=True)

    # Classification
    category_id = fields.Many2one("helpdesk.knowledge.category", string="Category", tracking=True)
    tag_ids = fields.Many2many("helpdesk.ticket.tag", string="Tags")

    # Visibility
    public = fields.Boolean(string="Public", default=True, help="Visible in customer portal")
    team_ids = fields.Many2many("helpdesk.ticket.team", string="Visible to Teams")

    # AI & Search
    keywords = fields.Char(string="Keywords", help="Keywords for search optimization")
    ai_indexed = fields.Boolean(string="AI Indexed", default=False)

    # Usage Statistics
    view_count = fields.Integer(string="Views", default=0)
    helpful_count = fields.Integer(string="Helpful", default=0)
    not_helpful_count = fields.Integer(string="Not Helpful", default=0)
    usage_score = fields.Float(string="Usage Score", compute="_compute_usage_score", store=True)

    # Related
    ticket_ids = fields.Many2many("helpdesk.ticket", "article_ticket_rel", "article_id", "ticket_id", string="Related Tickets")
    known_error_ids = fields.Many2many("helpdesk.known.error", string="Related Known Errors")

    # Authoring
    author_id = fields.Many2one("res.users", string="Author", default=lambda self: self.env.user)

    @api.depends("view_count", "helpful_count", "not_helpful_count")
    def _compute_usage_score(self):
        for article in self:
            total_feedback = article.helpful_count + article.not_helpful_count
            if total_feedback > 0:
                helpfulness = (article.helpful_count / total_feedback) * 100
                article.usage_score = (helpfulness * 0.7) + (min(article.view_count, 100) * 0.3)
            else:
                article.usage_score = min(article.view_count, 100) * 0.3

    @api.model
    def create(self, vals):
        if vals.get("number", _("New")) == _("New"):
            vals["number"] = self.env["ir.sequence"].next_by_code("helpdesk.knowledge.article") or _("New")
        return super().create(vals)

    def action_mark_helpful(self):
        self.helpful_count += 1

    def action_mark_not_helpful(self):
        self.not_helpful_count += 1

    def increment_view_count(self):
        self.view_count += 1
