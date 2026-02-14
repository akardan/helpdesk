# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Helpdesk Multi-Department",
    "summary": "Extend helpdesk teams to full department-level service desks with per-team stages, HR department linking, and cross-department coordination",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "category": "Services/Helpdesk",
    "author": "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/helpdesk",
    "depends": ["helpdesk_mgmt", "hr"],
    "data": [
        "security/ir.model.access.csv",
        "data/department_data.xml",
        "views/helpdesk_ticket_stage_views.xml",
        "views/helpdesk_ticket_team_views.xml",
        "views/helpdesk_ticket_views.xml",
        "views/helpdesk_department_stage_views.xml",
    ],
    "demo": [],
    "development_status": "Beta",
    "application": False,
    "installable": True,
    "auto_install": False,
}
