# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models, _
import logging

_logger = logging.getLogger(__name__)


class HelpdeskAIRouting(models.AbstractModel):
    """AI-powered intelligent ticket routing and assignment"""
    _name = "helpdesk.ai.routing"
    _description = "AI Routing Service"

    @api.model
    def route_ticket(self, ticket):
        """
        Smart routing: assign ticket to best team and user

        Args:
            ticket: helpdesk.ticket record

        Returns:
            dict: Routing results
        """
        _logger.info(f"AI Routing: Processing ticket {ticket.number}")

        result = {
            'routed': False,
            'assigned_team': None,
            'assigned_user': None,
            'routing_reason': None
        }

        # If already assigned, skip
        if ticket.user_id:
            result['routing_reason'] = 'Already assigned'
            return result

        # Step 1: Determine best team (if not set)
        if not ticket.team_id:
            team = self._find_best_team(ticket)
            if team:
                ticket.write({'team_id': team.id})
                result['assigned_team'] = team.id
                result['routed'] = True
                result['routing_reason'] = f'Auto-assigned to team: {team.name}'

        # Step 2: Assign to best available user in team
        if ticket.team_id:
            user = self._find_best_user(ticket)
            if user:
                ticket.write({'user_id': user.id})
                result['assigned_user'] = user.id
                result['routed'] = True
                result['routing_reason'] = f'Auto-assigned to user: {user.name} (load-based)'

        _logger.info(f"AI Routing complete: {result}")
        return result

    def _find_best_team(self, ticket):
        """Find best team based on category and expertise"""
        Team = self.env['helpdesk.ticket.team']

        # If ticket has category, find team with matching category
        if ticket.category_id:
            teams = Team.search([
                ('category_ids', 'in', [ticket.category_id.id])
            ])

            if teams:
                # Return team with lowest current load
                return min(teams, key=lambda t: t.todo_ticket_count)

        # Default: return team with lowest load
        all_teams = Team.search([])
        if all_teams:
            return min(all_teams, key=lambda t: t.todo_ticket_count)

        return None

    def _find_best_user(self, ticket):
        """Find best user based on workload and expertise"""
        if not ticket.team_id:
            return None

        User = self.env['res.users']
        team_users = ticket.team_id.user_ids

        if not team_users:
            return None

        # Calculate workload for each user
        user_workload = {}
        for user in team_users:
            # Count open tickets assigned to user
            open_ticket_count = self.env['helpdesk.ticket'].search_count([
                ('user_id', '=', user.id),
                ('stage_id.closed', '=', False)
            ])
            user_workload[user.id] = open_ticket_count

        # Return user with lowest workload
        best_user_id = min(user_workload, key=user_workload.get)
        return User.browse(best_user_id)
