# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models, _
import logging
import re

_logger = logging.getLogger(__name__)


class HelpdeskAIClassification(models.AbstractModel):
    """AI-powered ticket classification service"""
    _name = "helpdesk.ai.classification"
    _description = "AI Classification Service"

    @api.model
    def classify_ticket(self, ticket):
        """
        Classify ticket: determine category, priority, tags

        Args:
            ticket: helpdesk.ticket record

        Returns:
            dict: Classification results
        """
        _logger.info(f"AI Classification: Processing ticket {ticket.number}")

        result = {
            'classified': False,
            'suggested_category': None,
            'suggested_priority': None,
            'suggested_tags': [],
            'confidence': 0.0
        }

        # Extract text for analysis
        text = self._extract_text(ticket)

        # Determine priority based on urgency keywords
        priority = self._determine_priority(text)
        if priority:
            result['suggested_priority'] = priority
            if not ticket.priority or ticket.priority == '1':  # Default medium
                ticket.write({'priority': priority})
                result['classified'] = True

        # Determine category
        category = self._determine_category(text, ticket)
        if category:
            result['suggested_category'] = category.id
            if not ticket.category_id:
                ticket.write({'category_id': category.id})
                result['classified'] = True

        # Suggest tags
        tags = self._suggest_tags(text)
        if tags:
            result['suggested_tags'] = tags.ids
            if not ticket.tag_ids:
                ticket.write({'tag_ids': [(6, 0, tags.ids)]})
                result['classified'] = True

        result['confidence'] = self._calculate_confidence(result)

        _logger.info(f"AI Classification complete: {result}")
        return result

    def _extract_text(self, ticket):
        """Extract relevant text from ticket"""
        text_parts = []
        if ticket.name:
            text_parts.append(ticket.name)
        if ticket.description:
            # Strip HTML tags
            desc = re.sub('<[^<]+?>', '', ticket.description)
            text_parts.append(desc)
        return ' '.join(text_parts).lower()

    def _determine_priority(self, text):
        """Determine priority based on urgency keywords"""
        # Critical priority keywords
        critical_keywords = [
            'urgent', 'critical', 'down', 'outage', 'emergency',
            'production', 'acil', 'kritik', 'çalışmıyor'
        ]

        # High priority keywords
        high_keywords = [
            'important', 'asap', 'high', 'broken', 'error',
            'önemli', 'hata', 'bozuk'
        ]

        if any(keyword in text for keyword in critical_keywords):
            return '3'  # Critical
        elif any(keyword in text for keyword in high_keywords):
            return '2'  # High

        return '1'  # Medium (default)

    def _determine_category(self, text, ticket):
        """Determine category based on keywords"""
        Category = self.env['helpdesk.ticket.category']

        # Keyword to category mapping (simplified)
        category_keywords = {
            'network': ['network', 'internet', 'wifi', 'connection', 'ağ', 'bağlantı'],
            'hardware': ['hardware', 'computer', 'laptop', 'printer', 'donanım', 'bilgisayar'],
            'software': ['software', 'application', 'program', 'install', 'yazılım', 'uygulama'],
            'email': ['email', 'outlook', 'mail', 'e-posta', 'eposta'],
            'access': ['access', 'password', 'login', 'account', 'erişim', 'şifre'],
        }

        # Find matching category
        for category_name, keywords in category_keywords.items():
            if any(keyword in text for keyword in keywords):
                # Try to find existing category
                category = Category.search([
                    '|',
                    ('name', 'ilike', category_name),
                    ('name', 'ilike', category_name.capitalize())
                ], limit=1)

                if category:
                    return category

        # Default to first available category
        return Category.search([], limit=1)

    def _suggest_tags(self, text):
        """Suggest relevant tags"""
        Tag = self.env['helpdesk.ticket.tag']

        suggested_tags = self.env['helpdesk.ticket.tag']

        # Tag keyword mapping
        tag_keywords = {
            'urgent': ['urgent', 'critical', 'acil'],
            'hardware': ['hardware', 'donanım'],
            'software': ['software', 'yazılım'],
            'network': ['network', 'ağ'],
        }

        for tag_name, keywords in tag_keywords.items():
            if any(keyword in text for keyword in keywords):
                tag = Tag.search([('name', 'ilike', tag_name)], limit=1)
                if tag:
                    suggested_tags |= tag

        return suggested_tags

    def _calculate_confidence(self, result):
        """Calculate confidence score (0-100%)"""
        confidence = 0.0
        weights = {
            'suggested_category': 40,
            'suggested_priority': 30,
            'suggested_tags': 30,
        }

        if result['suggested_category']:
            confidence += weights['suggested_category']
        if result['suggested_priority']:
            confidence += weights['suggested_priority']
        if result['suggested_tags']:
            confidence += weights['suggested_tags']

        return confidence
