"""add_phase_v_columns

Revision ID: 001
Revises:
Create Date: 2025-12-29

"""
from typing import Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create enum types for Phase V
    op.execute("CREATE TYPE recurrence_enum_v2 AS ENUM ('none', 'daily', 'weekly', 'monthly')")
    op.execute("CREATE TYPE priority_enum_v2 AS ENUM ('low', 'medium', 'high')")
    op.execute("CREATE TYPE task_status_enum_v2 AS ENUM ('pending', 'completed')")
    op.execute("CREATE TYPE reminder_status_enum_v2 AS ENUM ('pending', 'sent', 'failed', 'cancelled')")

    # Alter tasks table to add Phase V columns
    op.alter_column('tasks', 'due_date',
                    existing_type=postgresql.DATE(),
                    type_=postgresql.TIMESTAMP(timezone=True),
                    existing_nullable=True)

    op.add_column('tasks', sa.Column('recurrence', postgresql.ENUM('none', 'daily', 'weekly', 'monthly', name='recurrence_enum_v2'), nullable=True))
    op.add_column('tasks', sa.Column('priority', postgresql.ENUM('low', 'medium', 'high', name='priority_enum_v2'), nullable=True))
    op.add_column('tasks', sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=True))
    op.add_column('tasks', sa.Column('parent_task_id', sa.Integer(), nullable=True))
    op.add_column('tasks', sa.Column('reminder_offset', postgresql.INTERVAL(), nullable=True))

    # Add status column if it doesn't exist (convert completed boolean)
    op.add_column('tasks', sa.Column('status', postgresql.ENUM('pending', 'completed', name='task_status_enum_v2'), nullable=True))

    # Create reminders table
    op.create_table('reminders',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('scheduled_at', postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('reminder_type', sa.String(50), nullable=True),
        sa.Column('status', postgresql.ENUM('pending', 'sent', 'failed', 'cancelled', name='reminder_status_enum_v2'), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=True),
        sa.Column('dapr_job_id', sa.String(255), nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('sent_at', postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ),
    )

    # Create audit_log_entries table
    op.create_table('audit_log_entries',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('event_id', sa.String(255), nullable=False),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=True),
        sa.Column('parent_task_id', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('event_data', postgresql.JSON, nullable=False),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), nullable=True),
    )

    # Create indexes for performance
    op.execute("CREATE INDEX idx_tasks_tags_gin ON tasks USING GIN (tags)")
    op.execute("CREATE INDEX idx_tasks_parent_id ON tasks (parent_task_id)")
    op.execute("CREATE INDEX idx_tasks_recurrence ON tasks (recurrence)")
    op.execute("CREATE INDEX idx_tasks_priority_due_date ON tasks (priority, due_date)")
    op.execute("CREATE INDEX idx_reminders_task_id ON reminders(task_id)")
    op.execute("CREATE INDEX idx_reminders_status ON reminders(status)")
    op.execute("CREATE INDEX idx_reminders_scheduled_at ON reminders(scheduled_at)")
    op.execute("CREATE INDEX idx_audit_event_id ON audit_log_entries(event_id)")
    op.execute("CREATE INDEX idx_audit_event_type ON audit_log_entries(event_type)")
    op.execute("CREATE INDEX idx_audit_task_id ON audit_log_entries(task_id)")

    # Migrate existing data: convert priority from int to enum
    op.execute("UPDATE tasks SET priority = 'medium' WHERE priority IS NULL OR priority = 0")
    op.execute("UPDATE tasks SET priority = 'low' WHERE priority = 1")
    op.execute("UPDATE tasks SET priority = 'high' WHERE priority >= 2")

    # Set default status based on completed field
    op.execute("UPDATE tasks SET status = 'completed' WHERE completed = true")
    op.execute("UPDATE tasks SET status = 'pending' WHERE completed = false OR completed IS NULL")


def downgrade():
    # Drop indexes
    op.execute("DROP INDEX IF EXISTS idx_audit_task_id")
    op.execute("DROP INDEX IF EXISTS idx_audit_event_type")
    op.execute("DROP INDEX IF EXISTS idx_audit_event_id")
    op.execute("DROP INDEX IF EXISTS idx_reminders_scheduled_at")
    op.execute("DROP INDEX IF EXISTS idx_reminders_status")
    op.execute("DROP INDEX IF EXISTS idx_reminders_task_id")
    op.execute("DROP INDEX IF EXISTS idx_tasks_priority_due_date")
    op.execute("DROP INDEX IF EXISTS idx_tasks_recurrence")
    op.execute("DROP INDEX IF EXISTS idx_tasks_parent_id")
    op.execute("DROP INDEX IF EXISTS idx_tasks_tags_gin")

    # Drop tables
    op.drop_table('audit_log_entries')
    op.drop_table('reminders')

    # Drop columns from tasks
    op.drop_column('tasks', 'status')
    op.drop_column('tasks', 'reminder_offset')
    op.drop_column('tasks', 'parent_task_id')
    op.drop_column('tasks', 'tags')
    op.drop_column('tasks', 'priority')
    op.drop_column('tasks', 'recurrence')

    # Revert due_date type
    op.alter_column('tasks', 'due_date',
                    existing_type=postgresql.TIMESTAMP(timezone=True),
                    type_=postgresql.DATE(),
                    existing_nullable=True)

    # Drop enum types
    op.execute("DROP TYPE reminder_status_enum_v2")
    op.execute("DROP TYPE task_status_enum_v2")
    op.execute("DROP TYPE priority_enum_v2")
    op.execute("DROP TYPE recurrence_enum_v2")
