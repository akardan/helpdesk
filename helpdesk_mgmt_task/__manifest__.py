# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Helpdesk Task Management",
    "summary": "Advanced task management for helpdesk: sub-tasks, milestones, templates, on-site visit tasks, dependencies, and multi-assignee support",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "category": "Services/Helpdesk",
    "author": "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/helpdesk",
    "depends": ["helpdesk_mgmt", "helpdesk_mgmt_service_catalog"],
    "data": [
        "security/ir.model.access.csv",
        "data/task_data.xml",
        "views/helpdesk_task_views.xml",
        "views/helpdesk_ticket_views.xml",
    ],
    "demo": [],
    "development_status": "Beta",
    "application": False,
    "installable": True,
    "auto_install": False,
}
