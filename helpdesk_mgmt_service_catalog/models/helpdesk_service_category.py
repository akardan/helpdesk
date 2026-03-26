# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class HelpdeskServiceCategory(models.Model):
    """Top-level grouping in the service catalog (e.g. 'IT Services', 'HR Services').

    Each category is owned by an hr.department so that routing, reporting,
    and access rules inherit from the company's existing department structure.
    """

    _name = "helpdesk.service.category"
    _description = "Helpdesk Service Catalog Category"
    _order = "sequence, name"

    name = fields.Char(string="Category Name", required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    description = fields.Html(string="Description", translate=True)

    # ── HR Department ownership ───────────────────────────────────────────────
    department_id = fields.Many2one(
        "hr.department",
        string="Department",
        ondelete="restrict",
        index=True,
        help="The HR department that owns this service category. "
             "Tickets raised from this category are routed to the team "
             "linked to this department.",
    )

    # ── Default routing ───────────────────────────────────────────────────────
    team_id = fields.Many2one(
        "helpdesk.ticket.team",
        string="Default Team",
        help="Fallback team when no service item defines a specific team.",
    )

    icon = fields.Char(
        string="Font-Awesome Icon",
        default="fa-wrench",
        help="e.g. fa-laptop, fa-users, fa-money",
    )

    color = fields.Integer(default=0)

    service_item_ids = fields.One2many(
        "helpdesk.service.item",
        "service_category_id",
        string="Service Items",
    )

    service_item_count = fields.Integer(
        compute="_compute_service_item_count",
        string="Services",
    )

    def _compute_service_item_count(self):
        for cat in self:
            cat.service_item_count = len(cat.service_item_ids.filtered("active"))
