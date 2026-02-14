# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _


class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"

    task_ids = fields.One2many(
        "helpdesk.task",
        "ticket_id",
        string="Tasks",
    )

    task_count = fields.Integer(compute="_compute_task_count", string="Tasks")
    open_task_count = fields.Integer(compute="_compute_task_count", string="Open Tasks")

    milestone_ids = fields.One2many(
        "helpdesk.task.milestone",
        "ticket_id",
        string="Milestones",
    )

    overall_task_progress = fields.Float(
        compute="_compute_overall_task_progress",
        string="Task Progress (%)",
        store=True,
    )

    has_onsite_tasks = fields.Boolean(
        compute="_compute_has_onsite_tasks",
        string="Has On-Site Tasks",
        store=True,
    )

    @api.depends("task_ids")
    def _compute_task_count(self):
        for ticket in self:
            all_tasks = ticket.task_ids.filtered(lambda t: not t.parent_id)
            ticket.task_count = len(all_tasks)
            ticket.open_task_count = len(all_tasks.filtered(
                lambda t: t.state not in ("done", "cancelled")
            ))

    @api.depends("task_ids.state")
    def _compute_overall_task_progress(self):
        for ticket in self:
            root_tasks = ticket.task_ids.filtered(lambda t: not t.parent_id)
            if root_tasks:
                done = len(root_tasks.filtered(lambda t: t.state == "done"))
                ticket.overall_task_progress = (done / len(root_tasks)) * 100
            else:
                ticket.overall_task_progress = 0.0

    @api.depends("task_ids.task_type")
    def _compute_has_onsite_tasks(self):
        for ticket in self:
            ticket.has_onsite_tasks = any(
                t.task_type == "onsite" for t in ticket.task_ids
            )

    def action_view_tasks(self):
        self.ensure_one()
        return {
            "name": _("Tasks for %s") % self.name,
            "type": "ir.actions.act_window",
            "res_model": "helpdesk.task",
            "view_mode": "tree,kanban,form",
            "domain": [("ticket_id", "=", self.id), ("parent_id", "=", False)],
            "context": {"default_ticket_id": self.id},
        }

    def action_create_onsite_task(self):
        """Manually create a physical / on-site sub-task from the ticket."""
        self.ensure_one()
        return {
            "name": _("Create On-Site Task"),
            "type": "ir.actions.act_window",
            "res_model": "helpdesk.task",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_ticket_id": self.id,
                "default_task_type": "onsite",
                "default_name": _("On-Site Visit: %s") % self.name,
            },
        }

    def action_apply_task_template(self):
        """Clone tasks from a chosen template onto this ticket."""
        self.ensure_one()
        return {
            "name": _("Apply Task Template"),
            "type": "ir.actions.act_window",
            "res_model": "helpdesk.task",
            "view_mode": "tree",
            "domain": [("is_template", "=", True), ("parent_id", "=", False)],
            "context": {"apply_to_ticket_id": self.id},
        }

    def apply_template_tasks(self, template_task_ids):
        """Clone a set of template tasks (and their children) onto this ticket."""
        self.ensure_one()
        templates = self.env["helpdesk.task"].browse(template_task_ids).filtered("is_template")
        for tpl in templates:
            self._clone_task(tpl, parent_id=False)

    def _clone_task(self, template, parent_id=False):
        new_task = template.copy(
            {
                "ticket_id": self.id,
                "is_template": False,
                "state": "draft",
                "parent_id": parent_id,
            }
        )
        for child in template.child_ids:
            self._clone_task(child, parent_id=new_task.id)
        return new_task
