# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models, _
import logging
import re

_logger = logging.getLogger(__name__)


class HelpdeskAIKnowledgeMatcher(models.AbstractModel):
    """AI-powered knowledge base article matching"""
    _name = "helpdesk.ai.knowledge.matcher"
    _description = "AI Knowledge Matcher Service"

    @api.model
    def match_articles(self, ticket):
        """
        Match relevant knowledge base articles to ticket

        Args:
            ticket: helpdesk.ticket record

        Returns:
            dict: Matched articles
        """
        _logger.info(f"AI Knowledge Matcher: Processing ticket {ticket.number}")

        result = {
            'matched_articles': [],
            'match_count': 0,
            'confidence': 0.0
        }

        # Extract keywords from ticket
        keywords = self._extract_keywords(ticket)

        # Search for matching articles
        articles = self._search_articles(ticket, keywords)

        if articles:
            # Link articles to ticket
            ticket.write({
                'knowledge_article_ids': [(6, 0, articles.ids)]
            })

            result['matched_articles'] = articles.ids
            result['match_count'] = len(articles)
            result['confidence'] = min(len(articles) * 25, 100)  # Max 100%

            # Post message with article suggestions
            article_links = '<br/>'.join([
                f'<a href="/web#id={art.id}&model=helpdesk.knowledge.article">{art.name}</a>'
                for art in articles[:3]  # Top 3
            ])

            ticket.message_post(
                body=_('AI Agent found relevant knowledge base articles:<br/>%s') % article_links,
                subject=_('Knowledge Base Suggestions'),
                message_type='notification'
            )

        _logger.info(f"AI Knowledge Matcher complete: {result}")
        return result

    def _extract_keywords(self, ticket):
        """Extract keywords from ticket"""
        text = ''
        if ticket.name:
            text += ticket.name + ' '
        if ticket.description:
            text += re.sub('<[^<]+?>', '', ticket.description)

        # Simple keyword extraction (split by spaces, remove common words)
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 've', 'to'}
        words = text.lower().split()
        keywords = [w for w in words if len(w) > 3 and w not in stop_words]

        return keywords[:10]  # Top 10 keywords

    def _search_articles(self, ticket, keywords):
        """Search for matching articles"""
        Article = self.env['helpdesk.knowledge.article']

        domain = [('active', '=', True)]

        # Category match
        if ticket.category_id:
            domain.append(('category_id', '=', ticket.category_id.id))

        articles = Article.search(domain, limit=5)

        # If no category match, try keyword search
        if not articles and keywords:
            keyword_domain = ['|' for _ in range(len(keywords) - 1)]
            for keyword in keywords:
                keyword_domain.append(('name', 'ilike', keyword))

            articles = Article.search(keyword_domain, limit=5)

        return articles
