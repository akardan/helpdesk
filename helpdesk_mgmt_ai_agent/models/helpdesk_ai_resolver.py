# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models, _
import logging

_logger = logging.getLogger(__name__)


class HelpdeskAIResolver(models.AbstractModel):
    """AI-powered automatic ticket resolution"""
    _name = "helpdesk.ai.resolver"
    _description = "AI Auto-Resolution Service"

    @api.model
    def attempt_resolution(self, ticket):
        """
        Attempt to automatically resolve ticket using knowledge base and known errors

        Args:
            ticket: helpdesk.ticket record

        Returns:
            dict: Resolution results
        """
        _logger.info(f"AI Resolver: Attempting auto-resolution for ticket {ticket.number}")

        result = {
            'resolved': False,
            'resolution_method': None,
            'confidence': 0.0,
            'solution_applied': None
        }

        # Check if ticket matches a known error
        known_error_result = self._check_known_errors(ticket)
        if known_error_result['matched']:
            result.update(known_error_result)
            return result

        # Check if simple keyword-based resolution is possible
        simple_resolution = self._attempt_simple_resolution(ticket)
        if simple_resolution['resolved']:
            result.update(simple_resolution)
            return result

        _logger.info(f"AI Resolver: No auto-resolution possible for ticket {ticket.number}")
        return result

    def _check_known_errors(self, ticket):
        """Check if ticket matches a known error"""
        result = {
            'matched': False,
            'resolved': False,
            'resolution_method': 'known_error',
            'confidence': 0.0
        }

        # Search for matching known errors
        KnownError = self.env['helpdesk.known.error']
        known_errors = KnownError.search_matching_known_errors(ticket)

        if known_errors:
            # Apply first matching known error
            known_error = known_errors[0]
            known_error.apply_to_ticket(ticket)

            result['matched'] = True
            result['confidence'] = 85.0

            # If known error has a solution and not just workaround, consider auto-resolved
            if known_error.solution:
                # Post solution as internal note
                ticket.message_post(
                    body=_('AI Agent applied solution from Known Error: %s<br/><br/>Solution: %s') % (
                        known_error.name,
                        known_error.solution
                    ),
                    subject=_('Auto-Resolution Attempted'),
                    message_type='comment'
                )

                # For simple cases, could auto-close (disabled by default for safety)
                # result['resolved'] = True

        return result

    def _attempt_simple_resolution(self, ticket):
        """Attempt simple keyword-based resolution"""
        result = {
            'resolved': False,
            'resolution_method': 'simple_keyword',
            'confidence': 0.0
        }

        # Simple resolutions for common issues
        simple_solutions = {
            'password': _('Password reset instructions have been sent to your email.'),
            'reset': _('Please try resetting the application/device.'),
            'restart': _('Please restart the application/device.'),
            'şifre': _('Şifre sıfırlama talimatları e-postanıza gönderildi.'),
        }

        ticket_text = ((ticket.name or '') + ' ' + (ticket.description or '')).lower()

        for keyword, solution in simple_solutions.items():
            if keyword in ticket_text:
                # Post solution suggestion
                ticket.message_post(
                    body=_('AI Agent Suggestion: %s') % solution,
                    subject=_('Automated Solution Suggestion'),
                    message_type='comment'
                )

                result['confidence'] = 60.0
                result['solution_applied'] = solution
                # Not marking as resolved, just providing suggestion
                break

        return result
