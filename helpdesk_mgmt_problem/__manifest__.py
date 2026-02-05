# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Helpdesk Problem Management",
    "summary": """
        ITIL-compliant Problem Management - identify root causes and prevent recurring incidents""",
    "version": "14.0.1.0.0",
    "license": "AGPL-3",
    "category": "After-Sales",
    "author": "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/helpdesk",
    "depends": ["helpdesk_mgmt"],
    "data": [
        "security/ir.model.access.csv",
        "data/problem_data.xml",
        "views/helpdesk_problem_views.xml",
        "views/helpdesk_known_error_views.xml",
        "views/helpdesk_ticket_views.xml",
    ],
    "demo": [],
    "development_status": "Beta",
    "installable": True,
    "auto_install": False,
}
