# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _


class HelpdeskTask(models.Model):
    """
    Lightweight task model living inside the helpdesk app.

    Supports:
    - Parent / child (sub-task) hierarchy (unlimited depth)
    - Multiple assignees
    - Milestone association
    - Dependency (blocked_by) chain
    - Physical / on-site visit flag
    - Task templates
    """

    _name = "helpdesk.task"
    _description = "Helpdesk Task"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "sequence, id"
    _parent_name = "parent_id"

    # ── Identity ───────────────────────────────────────────────────────────────
    name = fields.Char(string="Task Name", required=True, tracking=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    description = fields.Html(string="Description", translate=True)

    # ── State ──────────────────────────────────────────────────────────────────
    state = fields.Selection(
        [
            ("draft", "To Do"),
            ("in_progress", "In Progress"),
            ("blocked", "Blocked"),
            ("done", "Done"),
            ("cancelled", "Cancelled"),
        ],
        string="State",
        default="draft",
        tracking=True,
    )

    kanban_state = fields.Selection(
        [("normal", "On Track"), ("done", "Ready"), ("blocked", "Blocked")],
        default="normal",
        tracking=True,
    )

    # ── Hierarchy ─────────────────────────────────────────────────────────────
    parent_id = fields.Many2one(
        "helpdesk.task",
        string="Parent Task",
        ondelete="cascade",
        index=True,
    )

    child_ids = fields.One2many(
        "helpdesk.task",
        "parent_id",
        string="Sub-Tasks",
    )

    child_count = fields.Integer(compute="_compute_child_count", string="Sub-Tasks")

    subtask_progress = fields.Float(
        compute="_compute_subtask_progress",
        string="Sub-Task Progress (%)",
        store=True,
    )

    # ── Ticket linkage ────────────────────────────────────────────────────────
    ticket_id = fields.Many2one(
        "helpdesk.ticket",
        string="Ticket",
        ondelete="cascade",
        index=True,
    )

    # ── Assignment ────────────────────────────────────────────────────────────
    user_ids = fields.Many2many(
        "res.users",
        "helpdesk_task_user_rel",
        "task_id",
        "user_id",
        string="Assignees",
        tracking=True,
    )

    team_id = fields.Many2one(
        related="ticket_id.team_id",
        string="Team",
        store=True,
        readonly=True,
    )

    # ── Dates & Duration ──────────────────────────────────────────────────────
    date_deadline = fields.Datetime(string="Deadline", tracking=True)
    date_start = fields.Datetime(string="Start Date")
    date_done = fields.Datetime(string="Done Date", readonly=True)
    planned_hours = fields.Float(string="Planned Hours", default=0.0)
    effective_hours = fields.Float(string="Effective Hours", default=0.0)

    # ── Dependencies ──────────────────────────────────────────────────────────
    blocked_by_ids = fields.Many2many(
        "helpdesk.task",
        "helpdesk_task_dependency_rel",
        "task_id",
        "blocked_by_id",
        string="Blocked By",
        help="This task cannot start until all blocking tasks are done.",
    )

    blocking_ids = fields.Many2many(
        "helpdesk.task",
        "helpdesk_task_dependency_rel",
        "blocked_by_id",
        "task_id",
        string="Blocking",
        help="Tasks that are waiting for this task.",
    )

    # ── Milestone ─────────────────────────────────────────────────────────────
    milestone_id = fields.Many2one(
        "helpdesk.task.milestone",
        string="Milestone",
        ondelete="set null",
    )

    # ── Physical / On-Site ────────────────────────────────────────────────────
    task_type = fields.Selection(
        [
            ("general", "General"),
            ("onsite", "On-Site Visit"),
            ("procurement", "Procurement"),
            ("approval", "Approval"),
            ("communication", "Communication"),
            ("investigation", "Investigation"),
        ],
        string="Task Type",
        default="general",
    )

    location = fields.Char(
        string="Location",
        help="Physical location for on-site tasks.",
    )

    requires_physical_access = fields.Boolean(
        string="Physical Access Required",
        compute="_compute_requires_physical",
        store=True,
    )

    # ── Template flag ─────────────────────────────────────────────────────────
    is_template = fields.Boolean(
        string="Is Template",
        default=False,
        help="Template tasks can be stamped onto tickets to create real tasks quickly.",
    )

    # ── Priority ──────────────────────────────────────────────────────────────
    priority = fields.Selection(
        [("0", "Normal"), ("1", "High")],
        default="0",
        string="Priority",
    )

    # ── Color (kanban) ────────────────────────────────────────────────────────
    color = fields.Integer(compute="_compute_color")

    # ── Computed ──────────────────────────────────────────────────────────────
    @api.depends("child_ids")
    def _compute_child_count(self):
        for task in self:
            task.child_count = len(task.child_ids)

    @api.depends("child_ids.state")
    def _compute_subtask_progress(self):
        for task in self:
            children = task.child_ids
            if children:
                done = len(children.filtered(lambda c: c.state == "done"))
                task.subtask_progress = (done / len(children)) * 100
            else:
                task.subtask_progress = 0.0

    @api.depends("task_type")
    def _compute_requires_physical(self):
        for task in self:
            task.requires_physical_access = task.task_type == "onsite"

    @api.depends("state", "kanban_state")
    def _compute_color(self):
        _map = {
            "done": 10,
            "cancelled": 0,
            "blocked": 1,
            "in_progress": 4,
            "draft": 0,
        }
        for task in self:
            task.color = _map.get(task.state, 0)

    # ── State transitions ─────────────────────────────────────────────────────
    def action_start(self):
        self.write({"state": "in_progress", "date_start": fields.Datetime.now()})

    def action_done(self):
        self.write({"state": "done", "date_done": fields.Datetime.now()})
        # Auto-close parent if all siblings done
        for task in self:
            if task.parent_id and all(
                c.state == "done" for c in task.parent_id.child_ids
            ):
                task.parent_id.action_done()

    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_reset(self):
        self.write({"state": "draft", "date_done": False})

    # ── Create sub-task ───────────────────────────────────────────────────────
    def create_subtask(self, name, task_type="general", **kwargs):
        """Convenience method to create a sub-task under this task."""
        self.ensure_one()
        return self.create(
            {
                "name": name,
                "parent_id": self.id,
                "ticket_id": self.ticket_id.id,
                "task_type": task_type,
                **kwargs,
            }
        )


class HelpdeskTaskMilestone(models.Model):
    """Optional milestone to group tasks by delivery checkpoint."""

    _name = "helpdesk.task.milestone"
    _description = "Helpdesk Task Milestone"
    _order = "date_deadline, name"

    name = fields.Char(string="Milestone Name", required=True)
    ticket_id = fields.Many2one("helpdesk.ticket", ondelete="cascade", index=True)
    date_deadline = fields.Date(string="Target Date")
    reached = fields.Boolean(string="Reached", default=False)

    task_ids = fields.One2many("helpdesk.task", "milestone_id", string="Tasks")
    task_count = fields.Integer(compute="_compute_task_count")

    def _compute_task_count(self):
        for ms in self:
            ms.task_count = len(ms.task_ids)
