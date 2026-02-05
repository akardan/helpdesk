# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Helpdesk Knowledge Base",
    "summary": """
        Knowledge Base for Helpdesk with AI-powered search and recommendations""",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "category": "Services/Helpdesk",
    "author": "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/helpdesk",
    "depends": ["helpdesk_mgmt", "portal"],
    "data": [
        "security/knowledge_security.xml",
        "security/ir.model.access.csv",
        "data/knowledge_data.xml",
        "views/helpdesk_knowledge_article_views.xml",
        "views/helpdesk_knowledge_category_views.xml",
        "views/helpdesk_ticket_views.xml",
        "views/portal_templates.xml",
    ],
    "demo": [],
    "development_status": "Beta",
    "application": False,
    "installable": True,
    "auto_install": False,
}
