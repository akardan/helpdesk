# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Helpdesk AI Agent Framework",
    "summary": """
        AI-powered intelligent agents for helpdesk automation:
        auto-classification, smart routing, knowledge matching,
        problem detection, and auto-resolution""",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "category": "Services/Helpdesk",
    "author": "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/helpdesk",
    "depends": [
        "helpdesk_mgmt",
        "helpdesk_mgmt_sla",
        "helpdesk_mgmt_problem",
        "helpdesk_mgmt_knowledge",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ai_agent_data.xml",
        "data/ai_agent_cron.xml",
        "views/helpdesk_ai_agent_views.xml",
        "views/helpdesk_ai_agent_config_views.xml",
        "views/helpdesk_ticket_views.xml",
    ],
    "demo": [],
    "development_status": "Beta",
    "application": False,
    "installable": True,
    "auto_install": False,
}
