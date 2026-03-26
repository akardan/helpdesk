# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Helpdesk Service Catalog",
    "summary": "Multi-department service catalog with request types, approval workflows, SLA targets per service, and dynamic form fields",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "category": "Services/Helpdesk",
    "author": "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/helpdesk",
    "depends": ["helpdesk_mgmt", "helpdesk_mgmt_department"],
    "data": [
        "security/ir.model.access.csv",
        "data/service_catalog_data.xml",
        "views/helpdesk_service_category_views.xml",
        "views/helpdesk_service_item_views.xml",
        "views/helpdesk_ticket_views.xml",
        "views/portal_catalog_templates.xml",
    ],
    "demo": [],
    "development_status": "Beta",
    "application": False,
    "installable": True,
    "auto_install": False,
}
