"""Create X monitor schema."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "202603250001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tblXMonitorTargets",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("username", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=True),
        sa.Column("include_replies", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("include_retweets", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("media_only", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "keywords_any",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "keywords_all",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "regex_any",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "alert_recipients",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "digest_recipients",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idxTblXMonitorTargetsUsername",
        "tblXMonitorTargets",
        ["username"],
        unique=True,
    )

    op.create_table(
        "tblXMonitorTargetWatermarks",
        sa.Column("target_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("last_seen_post_id", sa.Text(), nullable=True),
        sa.Column("last_seen_post_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_successful_poll_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_attempted_poll_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["target_id"], ["tblXMonitorTargets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("target_id"),
    )

    op.create_table(
        "tblXMonitorPosts",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("post_id", sa.Text(), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("author_username", sa.Text(), nullable=False),
        sa.Column("author_user_id", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("text_raw", sa.Text(), nullable=False),
        sa.Column("text_normalized", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("is_reply", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_retweet", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("has_media", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("lang", sa.Text(), nullable=True),
        sa.Column("raw_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("inserted_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["target_id"], ["tblXMonitorTargets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idxTblXMonitorPostsPostId", "tblXMonitorPosts", ["post_id"], unique=True)
    op.create_index(
        "idxTblXMonitorPostsTargetIdCreatedAt",
        "tblXMonitorPosts",
        ["target_id", "created_at"],
        unique=False,
    )
    op.create_index("idxTblXMonitorPostsCreatedAt", "tblXMonitorPosts", ["created_at"], unique=False)

    op.create_table(
        "tblXMonitorPostMatches",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("post_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("matched", sa.Boolean(), nullable=False),
        sa.Column(
            "matched_rules",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("match_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["tblXMonitorPosts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_id"], ["tblXMonitorTargets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idxTblXMonitorPostMatchesTargetIdCreatedAt",
        "tblXMonitorPostMatches",
        ["target_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "tblXMonitorNotificationEvents",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("post_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("target_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("recipient", sa.Text(), nullable=False),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "payload_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["tblXMonitorPosts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_id"], ["tblXMonitorTargets.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idxTblXMonitorNotificationEventsIdempotencyKey",
        "tblXMonitorNotificationEvents",
        ["idempotency_key"],
        unique=True,
    )

    op.create_table(
        "tblXMonitorFlowRuns",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("flow_name", sa.Text(), nullable=False),
        sa.Column("prefect_flow_run_id", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column(
            "counts_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "tblXMonitorDigestBookmarks",
        sa.Column("digest_key", sa.Text(), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recipient", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("digest_key"),
    )

    op.create_table(
        "tblXMonitorOperatorEvents",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "details_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("dedupe_key", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idxTblXMonitorOperatorEventsDedupeKey",
        "tblXMonitorOperatorEvents",
        ["dedupe_key"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idxTblXMonitorOperatorEventsDedupeKey", table_name="tblXMonitorOperatorEvents")
    op.drop_table("tblXMonitorOperatorEvents")
    op.drop_table("tblXMonitorDigestBookmarks")
    op.drop_table("tblXMonitorFlowRuns")
    op.drop_index(
        "idxTblXMonitorNotificationEventsIdempotencyKey",
        table_name="tblXMonitorNotificationEvents",
    )
    op.drop_table("tblXMonitorNotificationEvents")
    op.drop_index("idxTblXMonitorPostMatchesTargetIdCreatedAt", table_name="tblXMonitorPostMatches")
    op.drop_table("tblXMonitorPostMatches")
    op.drop_index("idxTblXMonitorPostsCreatedAt", table_name="tblXMonitorPosts")
    op.drop_index("idxTblXMonitorPostsTargetIdCreatedAt", table_name="tblXMonitorPosts")
    op.drop_index("idxTblXMonitorPostsPostId", table_name="tblXMonitorPosts")
    op.drop_table("tblXMonitorPosts")
    op.drop_table("tblXMonitorTargetWatermarks")
    op.drop_index("idxTblXMonitorTargetsUsername", table_name="tblXMonitorTargets")
    op.drop_table("tblXMonitorTargets")

