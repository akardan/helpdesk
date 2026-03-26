# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class HelpdeskAIAgentConfig(models.Model):
    """Configuration for AI Agents"""
    _name = "helpdesk.ai.agent.config"
    _description = "AI Agent Configuration"

    name = fields.Char(string="Config Name", required=True)
    description = fields.Text(string="Description")

    # Auto-processing settings
    auto_process_new_tickets = fields.Boolean(
        string="Auto-Process New Tickets",
        default=True,
        help="Automatically process new tickets with AI agents"
    )

    auto_classify = fields.Boolean(string="Auto-Classify", default=True)
    auto_route = fields.Boolean(string="Auto-Route", default=True)
    auto_suggest_knowledge = fields.Boolean(string="Auto-Suggest Knowledge", default=True)
    auto_resolve = fields.Boolean(string="Attempt Auto-Resolution", default=False)

    # Thresholds
    min_confidence_threshold = fields.Float(
        string="Minimum Confidence Threshold (%)",
        default=70.0,
        help="Minimum confidence required for auto-actions"
    )
