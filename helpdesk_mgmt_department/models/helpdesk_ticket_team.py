# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class HelpdeskTicketTeam(models.Model):
    _inherit = "helpdesk.ticket.team"

    # ── Department linkage ─────────────────────────────────────────────────────
    hr_department_id = fields.Many2one(
        "hr.department",
        string="HR Department",
        help="Link this helpdesk team to an HR department for reporting and routing.",
    )

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
        default="general",
        required=True,
        help="Functional type of this service desk. "
             "Controls default stage set and AI routing behaviour.",
    )

    department_icon = fields.Char(
        string="Department Icon",
        compute="_compute_department_icon",
    )

    # ── Per-team stage configuration ───────────────────────────────────────────
    stage_ids = fields.Many2many(
        "helpdesk.ticket.stage",
        "helpdesk_stage_team_rel",
        "team_id",
        "stage_id",
        string="Allowed Stages",
        help="Stages visible for tickets in this team. "
             "Leave empty to fall back to shared (global) stages.",
    )

    # ── Cross-department routing ───────────────────────────────────────────────
    escalation_team_ids = fields.Many2many(
        "helpdesk.ticket.team",
        "helpdesk_team_escalation_rel",
        "team_id",
        "escalation_team_id",
        string="Escalate To Teams",
        help="Teams to which tickets from this team can be escalated or transferred.",
    )

    # ── Counters per department type ───────────────────────────────────────────
    todo_ticket_count_by_dept = fields.Char(
        string="Ticket Summary",
        compute="_compute_dept_summary",
    )

    _DEPT_ICONS = {
        "it": "fa-laptop",
        "hr": "fa-users",
        "finance": "fa-money",
        "facilities": "fa-building",
        "legal": "fa-gavel",
        "marketing": "fa-bullhorn",
        "logistics": "fa-truck",
        "customer_service": "fa-headphones",
        "general": "fa-cogs",
    }

    @api.depends("department_type")
    def _compute_department_icon(self):
        for team in self:
            team.department_icon = self._DEPT_ICONS.get(
                team.department_type, "fa-cogs"
            )

    def _compute_dept_summary(self):
        for team in self:
            open_count = len(
                team.ticket_ids.filtered(lambda t: not t.stage_id.closed)
            )
            closed_count = len(
                team.ticket_ids.filtered(lambda t: t.stage_id.closed)
            )
            team.todo_ticket_count_by_dept = f"{open_count} open / {closed_count} closed"

    # ── Stage bootstrap ────────────────────────────────────────────────────────
    def action_create_default_stages(self):
        """Create a private stage set for this team based on department_type."""
        self.ensure_one()
        Stage = self.env["helpdesk.ticket.stage"]

        _STAGE_TEMPLATES = {
            "it": [
                ("New", 1, True, False),
                ("In Progress", 2, False, False),
                ("Awaiting User", 3, False, False),
                ("Pending Change", 4, False, False),
                ("Resolved", 5, False, True),
                ("Closed", 6, False, True),
            ],
            "hr": [
                ("Received", 1, True, False),
                ("Under Review", 2, False, False),
                ("Pending Approval", 3, False, False),
                ("Approved", 4, False, False),
                ("Completed", 5, False, True),
                ("Rejected", 6, False, True),
            ],
            "finance": [
                ("Submitted", 1, True, False),
                ("Under Review", 2, False, False),
                ("Pending Documents", 3, False, False),
                ("In Process", 4, False, False),
                ("Completed", 5, False, True),
                ("Rejected", 6, False, True),
            ],
            "facilities": [
                ("Reported", 1, True, False),
                ("Assessed", 2, False, False),
                ("Scheduled", 3, False, False),
                ("In Progress", 4, False, False),
                ("Completed", 5, False, True),
                ("Cancelled", 6, False, True),
            ],
        }

        templates = _STAGE_TEMPLATES.get(
            self.department_type,
            [  # default generic
                ("New", 1, True, False),
                ("In Progress", 2, False, False),
                ("Awaiting", 3, False, False),
                ("Done", 4, False, True),
                ("Cancelled", 5, False, True),
            ],
        )

        new_stages = self.env["helpdesk.ticket.stage"]
        for name, seq, unattended, closed in templates:
            stage = Stage.create(
                {
                    "name": name,
                    "sequence": seq,
                    "unattended": unattended,
                    "closed": closed,
                    "team_ids": [(4, self.id)],
                    "department_type": self.department_type,
                    "company_id": self.company_id.id,
                }
            )
            new_stages |= stage

        self.stage_ids = new_stages
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Stages Created",
                "message": f"{len(new_stages)} stages created for team '{self.name}'.",
                "type": "success",
            },
        }
