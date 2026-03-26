# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Helpdesk SLA Management",
    "summary": """
        ITIL-compliant SLA Management for Helpdesk Tickets with automated monitoring and escalation""",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "category": "Services/Helpdesk",
    "author": "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/helpdesk",
    "depends": ["helpdesk_mgmt"],
    "data": [
        "security/ir.model.access.csv",
        "data/sla_data.xml",
        "data/sla_cron.xml",
        "views/helpdesk_sla_policy_views.xml",
        "views/helpdesk_sla_status_views.xml",
        "views/helpdesk_ticket_views.xml",
        "views/helpdesk_ticket_team_views.xml",
    ],
    "demo": [],
    "development_status": "Beta",
    "application": False,
    "installable": True,
    "auto_install": False,
}
