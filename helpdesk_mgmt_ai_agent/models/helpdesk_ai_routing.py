# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models, _
import logging

_logger = logging.getLogger(__name__)


class HelpdeskAIRouting(models.AbstractModel):
    """AI-powered intelligent ticket routing and assignment.

    Routing priority chain:
    1. Service item defines target team  (helpdesk_mgmt_service_catalog)
    2. Department type match             (helpdesk_mgmt_department)
    3. Category expertise match
    4. Lowest-load team fallback
    """
    _name = "helpdesk.ai.routing"
    _description = "AI Routing Service"

    @api.model
    def route_ticket(self, ticket):
        """
        Smart routing: assign ticket to best team and user.

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
            'routing_reason': None,
        }

        # If already assigned to a user, respect that choice
        if ticket.user_id:
            result['routing_reason'] = 'Already assigned'
            return result

        # Step 1: Determine best team (if not yet set)
        if not ticket.team_id:
            team = self._find_best_team(ticket)
            if team:
                ticket.write({'team_id': team.id})
                result['assigned_team'] = team.id
                result['routed'] = True
                result['routing_reason'] = f'Auto-assigned to team: {team.name}'

        # Step 2: Assign to best available user within the team
        if ticket.team_id:
            user = self._find_best_user(ticket)
            if user:
                ticket.write({'user_id': user.id})
                result['assigned_user'] = user.id
                result['routed'] = True
                result['routing_reason'] = (
                    (result.get('routing_reason') or '') +
                    f' | User: {user.name} (load-balanced)'
                )

        _logger.info(f"AI Routing complete: {result}")
        return result

    def _find_best_team(self, ticket):
        """Find best team using a 4-level priority chain."""
        Team = self.env['helpdesk.ticket.team']

        # ── Priority 1: Service item explicitly names a team ─────────────────
        # Available when helpdesk_mgmt_service_catalog is installed
        svc_item = getattr(ticket, 'service_item_id', False)
        if svc_item:
            svc_team = svc_item.sudo().get_effective_team()
            if svc_team:
                _logger.debug(
                    "Routing via service item '%s' → team '%s'",
                    svc_item.name, svc_team.name,
                )
                return svc_team

        # ── Priority 2: Department type match ────────────────────────────────
        # Available when helpdesk_mgmt_department is installed
        dept_type = getattr(ticket, 'department_type', False)
        if dept_type:
            dept_teams = Team.search([('department_type', '=', dept_type)])
            if dept_teams:
                best = min(dept_teams, key=lambda t: t.todo_ticket_count)
                _logger.debug(
                    "Routing via department type '%s' → team '%s'",
                    dept_type, best.name,
                )
                return best

        # ── Priority 3: Category expertise match ─────────────────────────────
        if ticket.category_id:
            category_teams = Team.search([
                ('category_ids', 'in', [ticket.category_id.id])
            ])
            if category_teams:
                best = min(category_teams, key=lambda t: t.todo_ticket_count)
                _logger.debug(
                    "Routing via category '%s' → team '%s'",
                    ticket.category_id.name, best.name,
                )
                return best

        # ── Priority 4: Lowest-load team fallback ────────────────────────────
        all_teams = Team.search([])
        if all_teams:
            best = min(all_teams, key=lambda t: t.todo_ticket_count)
            _logger.debug("Routing via fallback (lowest load) → team '%s'", best.name)
            return best

        return None

    def _find_best_user(self, ticket):
        """Find best user in the assigned team based on workload."""
        if not ticket.team_id:
            return None

        team_users = ticket.team_id.user_ids
        if not team_users:
            return None

        User = self.env['res.users']
        user_workload = {}
        for user in team_users:
            open_count = self.env['helpdesk.ticket'].search_count([
                ('user_id', '=', user.id),
                ('stage_id.closed', '=', False),
            ])
            user_workload[user.id] = open_count

        best_user_id = min(user_workload, key=user_workload.get)
        return User.browse(best_user_id)
