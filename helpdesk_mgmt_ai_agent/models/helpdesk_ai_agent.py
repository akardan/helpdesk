# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
import logging
import json

_logger = logging.getLogger(__name__)


class HelpdeskAIAgent(models.Model):
    """
    AI Agent Orchestrator - Coordinates all AI operations for helpdesk
    This is the main entry point for AI-powered automation
    """
    _name = "helpdesk.ai.agent"
    _description = "Helpdesk AI Agent Orchestrator"

    name = fields.Char(string="Agent Name", required=True)
    agent_type = fields.Selection([
        ('classifier', 'Classification Agent'),
        ('router', 'Routing & Assignment Agent'),
        ('knowledge_matcher', 'Knowledge Base Matcher'),
        ('resolver', 'Auto-Resolution Agent'),
        ('pattern_detector', 'Pattern Detection Agent'),
        ('subtask_creator', 'Sub-task Creator Agent'),
    ], string="Agent Type", required=True)

    active = fields.Boolean(default=True)
    description = fields.Text(string="Description")

    # Configuration
    config_id = fields.Many2one(
        "helpdesk.ai.agent.config",
        string="Configuration"
    )

    # AI Provider settings (placeholder for future LLM integration)
    ai_provider = fields.Selection([
        ('mock', 'Mock AI (for testing)'),
        ('openai', 'OpenAI GPT'),
        ('anthropic', 'Anthropic Claude'),
        ('custom', 'Custom API'),
    ], string="AI Provider", default='mock')

    api_endpoint = fields.Char(string="API Endpoint")
    api_key = fields.Char(string="API Key")

    # Statistics
    execution_count = fields.Integer(string="Total Executions", default=0)
    success_count = fields.Integer(string="Successful Executions", default=0)
    failure_count = fields.Integer(string="Failed Executions", default=0)
    success_rate = fields.Float(
        string="Success Rate (%)",
        compute="_compute_success_rate"
    )

    @api.depends("success_count", "execution_count")
    def _compute_success_rate(self):
        for agent in self:
            if agent.execution_count > 0:
                agent.success_rate = (agent.success_count / agent.execution_count) * 100
            else:
                agent.success_rate = 0.0

    @api.model
    def process_ticket_with_ai(self, ticket):
        """
        Main orchestration method - processes a ticket through all enabled AI agents

        Args:
            ticket: helpdesk.ticket record

        Returns:
            dict: Results from all AI agents
        """
        _logger.info(f"AI Agent Orchestrator: Processing ticket {ticket.number}")

        results = {
            'ticket_id': ticket.id,
            'ticket_number': ticket.number,
            'agents_executed': [],
            'actions_taken': [],
        }

        # 1. Classification Agent
        classifier = self._get_active_agent('classifier')
        if classifier:
            classification_result = classifier._execute_classification(ticket)
            results['classification'] = classification_result
            results['agents_executed'].append('classifier')

        # 2. Knowledge Matcher Agent
        knowledge_matcher = self._get_active_agent('knowledge_matcher')
        if knowledge_matcher:
            knowledge_result = knowledge_matcher._execute_knowledge_match(ticket)
            results['knowledge_articles'] = knowledge_result
            results['agents_executed'].append('knowledge_matcher')

        # 3. Auto-Resolution Attempt
        resolver = self._get_active_agent('resolver')
        if resolver:
            resolution_result = resolver._attempt_auto_resolution(ticket)
            results['auto_resolution'] = resolution_result
            results['agents_executed'].append('resolver')

        # 4. If not auto-resolved, route to appropriate team/user
        if not results.get('auto_resolution', {}).get('resolved', False):
            router = self._get_active_agent('router')
            if router:
                routing_result = router._execute_routing(ticket)
                results['routing'] = routing_result
                results['agents_executed'].append('router')

        # 5. Check if physical access is required and create sub-tasks
        subtask_creator = self._get_active_agent('subtask_creator')
        if subtask_creator:
            subtask_result = subtask_creator._check_and_create_subtasks(ticket)
            results['subtasks'] = subtask_result
            results['agents_executed'].append('subtask_creator')

        # 6. Pattern Detection (async, doesn't block)
        pattern_detector = self._get_active_agent('pattern_detector')
        if pattern_detector:
            pattern_result = pattern_detector._detect_patterns(ticket)
            results['patterns'] = pattern_result
            results['agents_executed'].append('pattern_detector')

        _logger.info(f"AI Agent Orchestrator: Completed processing ticket {ticket.number}")
        _logger.debug(f"AI Agent Results: {json.dumps(results, indent=2)}")

        return results

    def _get_active_agent(self, agent_type):
        """Get active agent of specified type"""
        return self.search([
            ('agent_type', '=', agent_type),
            ('active', '=', True)
        ], limit=1)

    def _execute_classification(self, ticket):
        """Execute classification logic - implemented in helpdesk_ai_classification.py"""
        return self.env['helpdesk.ai.classification'].classify_ticket(ticket)

    def _execute_knowledge_match(self, ticket):
        """Execute knowledge matching - implemented in helpdesk_ai_knowledge_matcher.py"""
        return self.env['helpdesk.ai.knowledge.matcher'].match_articles(ticket)

    def _attempt_auto_resolution(self, ticket):
        """Execute auto-resolution - implemented in helpdesk_ai_resolver.py"""
        return self.env['helpdesk.ai.resolver'].attempt_resolution(ticket)

    def _execute_routing(self, ticket):
        """Execute smart routing - implemented in helpdesk_ai_routing.py"""
        return self.env['helpdesk.ai.routing'].route_ticket(ticket)

    def _check_and_create_subtasks(self, ticket):
        """Check for physical access needs and create sub-tasks"""
        # Check if description mentions physical access keywords
        physical_keywords = [
            'on-site', 'onsite', 'visit', 'physical',
            'replace', 'install', 'hardware', 'cable',
            'fiziksel', 'yerinde', 'ziyaret', 'kurulum'
        ]

        description_lower = (ticket.description or '').lower()
        name_lower = (ticket.name or '').lower()

        requires_physical = any(
            keyword in description_lower or keyword in name_lower
            for keyword in physical_keywords
        )

        if requires_physical:
            # Create sub-task for physical access
            ticket.message_post(
                body=_('AI Agent detected physical access requirement. '
                       'Consider creating on-site visit task.'),
                subject=_('Physical Access Required'),
                message_type='notification'
            )

            return {
                'physical_access_required': True,
                'detected_keywords': [
                    kw for kw in physical_keywords
                    if kw in description_lower or kw in name_lower
                ],
                'suggestion': 'Create on-site visit task'
            }

        return {'physical_access_required': False}

    def _detect_patterns(self, ticket):
        """Detect recurring patterns"""
        # Find similar tickets
        similar_tickets = self.env['helpdesk.ticket'].search([
            ('category_id', '=', ticket.category_id.id),
            ('id', '!=', ticket.id),
            ('create_date', '>=', fields.Datetime.subtract(fields.Datetime.now(), days=30))
        ], limit=10)

        if len(similar_tickets) >= 3:
            # Mark as potential recurring issue
            ticket.write({'recurring_issue': True})

            # Link similar tickets
            ticket.write({
                'similar_ticket_ids': [(6, 0, similar_tickets.ids)]
            })

            return {
                'pattern_detected': True,
                'similar_ticket_count': len(similar_tickets),
                'suggestion': 'Consider creating a Problem record'
            }

        return {'pattern_detected': False}

    @api.model
    def cron_process_unclassified_tickets(self):
        """Cron job to process tickets that haven't been processed by AI"""
        tickets = self.env['helpdesk.ticket'].search([
            ('stage_id.closed', '=', False),
            ('ai_processed', '=', False)
        ], limit=50)

        for ticket in tickets:
            try:
                self.process_ticket_with_ai(ticket)
                ticket.write({'ai_processed': True})
            except Exception as e:
                _logger.error(f"Error processing ticket {ticket.number} with AI: {str(e)}")
