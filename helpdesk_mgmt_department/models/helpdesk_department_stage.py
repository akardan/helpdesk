# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class HelpdeskDepartmentStage(models.Model):
    """Stage template catalogue: administrators define stage pipelines
    per HR department so teams can bootstrap their own Kanban stages quickly."""

    _name = "helpdesk.department.stage"
    _description = "Helpdesk Stage Template"
    _order = "hr_department_id, sequence"

    name = fields.Char(string="Stage Name", required=True, translate=True)
    sequence = fields.Integer(default=10)

    # ── Link to actual HR department ──────────────────────────────────────────
    hr_department_id = fields.Many2one(
        "hr.department",
        string="Department",
        ondelete="cascade",
        index=True,
        help="The HR department this stage template belongs to. "
             "Leave empty to mark as a generic / shared template.",
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
