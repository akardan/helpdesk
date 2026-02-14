# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class HelpdeskServiceCategory(models.Model):
    """Top-level grouping in the service catalog (e.g. 'IT Services', 'HR Services')."""

    _name = "helpdesk.service.category"
    _description = "Helpdesk Service Catalog Category"
    _order = "sequence, name"

    name = fields.Char(string="Category Name", required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    description = fields.Html(string="Description", translate=True)

    department_type = fields.Selection(
        [
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
        required=True,
        default="general",
    )

    team_id = fields.Many2one(
        "helpdesk.ticket.team",
        string="Default Team",
        help="Tickets created from this category are routed to this team by default.",
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
