# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
import logging
import json

_logger = logging.getLogger(__name__)


class HelpdeskAIAgent(models.Model):
    """
    AI Agent Orchestrator - Coordinates all AI operations for helpdesk.

    Processing pipeline:
    1. Classify  → priority, category, tags
    2. Knowledge → surface matching KB articles
    3. Resolve   → attempt auto-close via KEDB
    4. Route     → service-item → dept-type → category → fallback
    5. Tasks     → create on-site tasks / apply service templates
    6. Patterns  → detect recurring issues → problem record suggestion
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

    # ── Orchestrator ──────────────────────────────────────────────────────────

    @api.model
    def process_ticket_with_ai(self, ticket):
        """
        Main orchestration method - processes a ticket through all enabled agents.

        Args:
            ticket: helpdesk.ticket record

        Returns:
            dict: Results from all AI agents
        """
        _logger.info("AI Agent Orchestrator: Processing ticket %s", ticket.number)

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

        # 4. Route to appropriate team/user (skip if auto-resolved)
        if not results.get('auto_resolution', {}).get('resolved', False):
            router = self._get_active_agent('router')
            if router:
                routing_result = router._execute_routing(ticket)
                results['routing'] = routing_result
                results['agents_executed'].append('router')

        # 5. Physical-access sub-tasks + service item task templates
        subtask_creator = self._get_active_agent('subtask_creator')
        if subtask_creator:
            subtask_result = subtask_creator._check_and_create_subtasks(ticket)
            results['subtasks'] = subtask_result
            results['agents_executed'].append('subtask_creator')
            if subtask_result.get('task_created'):
                results['actions_taken'].append('onsite_task_created')
            if subtask_result.get('template_applied'):
                results['actions_taken'].append('task_template_applied')

        # 6. Pattern Detection (enrichment, non-blocking)
        pattern_detector = self._get_active_agent('pattern_detector')
        if pattern_detector:
            pattern_result = pattern_detector._detect_patterns(ticket)
            results['patterns'] = pattern_result
            results['agents_executed'].append('pattern_detector')

        _logger.info(
            "AI Agent Orchestrator: Completed ticket %s | agents=%s | actions=%s",
            ticket.number,
            results['agents_executed'],
            results['actions_taken'],
        )
        _logger.debug("AI Agent Results: %s", json.dumps(results, indent=2))

        return results

    def _get_active_agent(self, agent_type):
        """Get active agent of specified type."""
        return self.search([
            ('agent_type', '=', agent_type),
            ('active', '=', True)
        ], limit=1)

    # ── Per-agent execution methods ───────────────────────────────────────────

    def _execute_classification(self, ticket):
        return self.env['helpdesk.ai.classification'].classify_ticket(ticket)

    def _execute_knowledge_match(self, ticket):
        return self.env['helpdesk.ai.knowledge.matcher'].match_articles(ticket)

    def _attempt_auto_resolution(self, ticket):
        return self.env['helpdesk.ai.resolver'].attempt_resolution(ticket)

    def _execute_routing(self, ticket):
        return self.env['helpdesk.ai.routing'].route_ticket(ticket)

    def _check_and_create_subtasks(self, ticket):
        """
        Determine physical-access requirements and act accordingly.

        Detection priority:
        1. Service item ``requires_physical_access`` flag (explicit)
        2. Keyword scan of ticket name / description (heuristic)

        When physical access is confirmed:
        - Creates a ``helpdesk.task`` record of type 'onsite' (if not already present)
        - Posts a chatter notification

        Also applies task templates from service item when available.
        """
        physical_access_required = False
        detected_keywords = []
        task_created = False
        template_applied = False

        # ── Check 1: Service item explicit flag ──────────────────────────────
        svc_item = getattr(ticket, 'service_item_id', False)
        if svc_item and svc_item.requires_physical_access:
            physical_access_required = True
            _logger.debug(
                "Physical access required via service item '%s' on ticket %s",
                svc_item.name, ticket.number,
            )

        # ── Check 2: Keyword heuristic ───────────────────────────────────────
        if not physical_access_required:
            physical_keywords = [
                'on-site', 'onsite', 'visit', 'physical',
                'replace', 'install', 'hardware', 'cable',
                'fiziksel', 'yerinde', 'ziyaret', 'kurulum',
                'sahaya', 'saha', 'bakım', 'tamir',
            ]
            text = ' '.join([
                (ticket.name or ''),
                (ticket.description or ''),
            ]).lower()
            detected_keywords = [kw for kw in physical_keywords if kw in text]
            if detected_keywords:
                physical_access_required = True
                _logger.debug(
                    "Physical access detected via keywords %s on ticket %s",
                    detected_keywords, ticket.number,
                )

        # ── Create on-site task if needed ────────────────────────────────────
        if physical_access_required:
            # Avoid creating duplicate onsite tasks
            existing_onsite = ticket.task_ids.filtered(
                lambda t: t.task_type == 'onsite' and not t.parent_id
            )
            if not existing_onsite:
                assignee_ids = [ticket.user_id.id] if ticket.user_id else []
                self.env['helpdesk.task'].create({
                    'name': _('On-Site Visit: %s') % ticket.name,
                    'ticket_id': ticket.id,
                    'task_type': 'onsite',
                    'state': 'draft',
                    'user_ids': [(6, 0, assignee_ids)],
                    'location': getattr(ticket.partner_id, 'city', '') or '',
                })
                task_created = True
                ticket.message_post(
                    body=_(
                        'AI Agent automatically created an on-site visit task '
                        'because physical access is required for this ticket.'
                    ),
                    subject=_('On-Site Task Created'),
                    message_type='notification',
                )
                _logger.info(
                    "AI Agent created onsite task for ticket %s", ticket.number
                )

        # ── Apply service item task template (if any) ─────────────────────
        # Only attempt if the ticket has no tasks yet (fresh ticket)
        if svc_item and not ticket.task_ids:
            template_tasks = self.env['helpdesk.task'].search([
                ('is_template', '=', True),
                ('parent_id', '=', False),
            ])
            # Match template by service item name (convention-based lookup)
            matching_template = template_tasks.filtered(
                lambda t: t.name.lower() in svc_item.name.lower() or
                          svc_item.name.lower() in t.name.lower()
            )
            if matching_template:
                ticket.apply_template_tasks(matching_template[:1].ids)
                template_applied = True
                _logger.info(
                    "AI Agent applied task template '%s' to ticket %s",
                    matching_template[0].name, ticket.number,
                )

        return {
            'physical_access_required': physical_access_required,
            'detected_keywords': detected_keywords,
            'task_created': task_created,
            'template_applied': template_applied,
        }

    def _detect_patterns(self, ticket):
        """Detect recurring patterns and suggest Problem record creation."""
        similar_tickets = self.env['helpdesk.ticket'].search([
            ('category_id', '=', ticket.category_id.id),
            ('id', '!=', ticket.id),
            ('create_date', '>=', fields.Datetime.subtract(fields.Datetime.now(), days=30))
        ], limit=10)

        if len(similar_tickets) >= 3:
            ticket.write({
                'recurring_issue': True,
                'similar_ticket_ids': [(6, 0, similar_tickets.ids)],
            })

            return {
                'pattern_detected': True,
                'similar_ticket_count': len(similar_tickets),
                'suggestion': 'Consider creating a Problem record',
            }

        return {'pattern_detected': False}

    # ── Cron ─────────────────────────────────────────────────────────────────

    @api.model
    def cron_process_unclassified_tickets(self):
        """Process tickets that haven't been processed by AI yet."""
        tickets = self.env['helpdesk.ticket'].search([
            ('stage_id.closed', '=', False),
            ('ai_processed', '=', False),
        ], limit=50)

        for ticket in tickets:
            try:
                self.process_ticket_with_ai(ticket)
                ticket.write({'ai_processed': True})
            except Exception as e:
                _logger.error(
                    "Error processing ticket %s with AI: %s",
                    ticket.number, str(e),
                )
