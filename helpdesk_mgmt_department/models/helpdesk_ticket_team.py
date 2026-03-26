# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _


class HelpdeskTicketTeam(models.Model):
    _inherit = "helpdesk.ticket.team"

    # ── HR Department (primary department reference) ───────────────────────────
    hr_department_id = fields.Many2one(
        "hr.department",
        string="Department",
        ondelete="restrict",
        help="The HR department this helpdesk team belongs to. "
             "Used for routing, reporting, and stage bootstrap.",
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

    # ── Stage bootstrap ────────────────────────────────────────────────────────
    def action_create_default_stages(self):
        """Create a private stage set for this team based on the linked HR department name."""
        self.ensure_one()
        Stage = self.env["helpdesk.ticket.stage"]

        category = self._detect_template_category()
        templates = self._get_stage_templates(category)

        new_stages = Stage
        for name, seq, unattended, closed in templates:
            stage = Stage.create({
                "name": name,
                "sequence": seq,
                "unattended": unattended,
                "closed": closed,
                "team_ids": [(4, self.id)],
                "company_id": self.company_id.id,
            })
            new_stages |= stage

        self.stage_ids = new_stages
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Stages Created"),
                "message": _(
                    "%(count)d stages created for team '%(team)s'.",
                    count=len(new_stages),
                    team=self.name,
                ),
                "type": "success",
            },
        }

    def _detect_template_category(self):
        """Infer a stage template category from the linked hr.department name."""
        if not self.hr_department_id:
            return "general"
        name = self.hr_department_id.name.lower()
        if any(kw in name for kw in ["it ", "i.t.", "information", "technology",
                                      "bilgi", "teknoloji", "teknik"]):
            return "it"
        if any(kw in name for kw in ["hr", "human", "people", "personnel",
                                      "ik", "insan", "personel", "workforce"]):
            return "hr"
        if any(kw in name for kw in ["finance", "accounting", "treasury",
                                      "mali", "muhasebe", "finans"]):
            return "finance"
        if any(kw in name for kw in ["facilities", "building", "maintenance",
                                      "bina", "tesis", "altyapı"]):
            return "facilities"
        if any(kw in name for kw in ["legal", "compliance", "law",
                                      "hukuk", "yasal", "uyumluluk"]):
            return "legal"
        if any(kw in name for kw in ["marketing", "communications", "brand",
                                      "pazarlama", "iletişim"]):
            return "marketing"
        if any(kw in name for kw in ["logistics", "supply", "warehouse",
                                      "lojistik", "tedarik", "depo"]):
            return "logistics"
        if any(kw in name for kw in ["customer", "support", "service desk",
                                      "müşteri", "destek"]):
            return "customer_service"
        return "general"

    @staticmethod
    def _get_stage_templates(category):
        """Return (name, sequence, unattended, closed) tuples for the given category."""
        _TEMPLATES = {
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
            "legal": [
                ("Received", 1, True, False),
                ("Legal Review", 2, False, False),
                ("Pending Approval", 3, False, False),
                ("Completed", 4, False, True),
            ],
            "marketing": [
                ("Request Received", 1, True, False),
                ("In Review", 2, False, False),
                ("In Production", 3, False, False),
                ("Delivered", 4, False, True),
                ("Cancelled", 5, False, True),
            ],
            "logistics": [
                ("Order Received", 1, True, False),
                ("Processing", 2, False, False),
                ("In Transit", 3, False, False),
                ("Delivered", 4, False, True),
                ("Cancelled", 5, False, True),
            ],
            "customer_service": [
                ("New", 1, True, False),
                ("Open", 2, False, False),
                ("Pending Response", 3, False, False),
                ("Resolved", 4, False, True),
            ],
        }
        return _TEMPLATES.get(
            category,
            [  # general fallback
                ("New", 1, True, False),
                ("In Progress", 2, False, False),
                ("Awaiting", 3, False, False),
                ("Done", 4, False, True),
                ("Cancelled", 5, False, True),
            ],
        )
