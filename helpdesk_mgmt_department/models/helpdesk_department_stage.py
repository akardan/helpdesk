# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class HelpdeskDepartmentStage(models.Model):
    """Stage *template* catalogue: pre-defined stage sets grouped by department
    type so teams can bootstrap their own private stage pipelines quickly."""

    _name = "helpdesk.department.stage"
    _description = "Helpdesk Department Stage Template"
    _order = "department_type, sequence"

    name = fields.Char(string="Stage Name", required=True, translate=True)
    sequence = fields.Integer(default=10)

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
    )

    unattended = fields.Boolean(
        string="Unattended",
        help="Tickets in this stage count as unattended.",
    )
    closed = fields.Boolean(
        string="Closed",
        help="Tickets in this stage are considered resolved/closed.",
    )
    fold = fields.Boolean(string="Folded in Kanban")

    description = fields.Text(string="Notes", translate=True)
