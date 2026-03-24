"""SQLAlchemy table metadata for X monitor persistence."""

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Index, Integer, MetaData, String, Table, Text

X_MONITOR_METADATA = MetaData()

tbl_x_monitor_targets = Table(
    "tblXMonitorTargets",
    X_MONITOR_METADATA,
    Column("id", String(36), primary_key=True),
    Column("username", Text, nullable=False),
    Column("user_id", Text, nullable=True),
    Column("include_replies", Boolean, nullable=False, default=False),
    Column("include_retweets", Boolean, nullable=False, default=False),
    Column("media_only", Boolean, nullable=False, default=False),
    Column("keywords_any", JSON, nullable=False, default=list),
    Column("keywords_all", JSON, nullable=False, default=list),
    Column("regex_any", JSON, nullable=False, default=list),
    Column("alert_recipients", JSON, nullable=False, default=list),
    Column("digest_recipients", JSON, nullable=False, default=list),
    Column("active", Boolean, nullable=False, default=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)
Index("idxTblXMonitorTargetsUsername", tbl_x_monitor_targets.c.username, unique=True)

Table(
    "tblXMonitorTargetWatermarks",
    X_MONITOR_METADATA,
    Column(
        "target_id",
        String(36),
        ForeignKey("tblXMonitorTargets.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("last_seen_post_id", Text, nullable=True),
    Column("last_seen_post_time", DateTime(timezone=True), nullable=True),
    Column("last_successful_poll_at", DateTime(timezone=True), nullable=True),
    Column("last_attempted_poll_at", DateTime(timezone=True), nullable=True),
    Column("consecutive_failures", Integer, nullable=False, default=0),
    Column("last_error", Text, nullable=True),
)

tbl_x_monitor_posts = Table(
    "tblXMonitorPosts",
    X_MONITOR_METADATA,
    Column("id", String(36), primary_key=True),
    Column("post_id", Text, nullable=False),
    Column(
        "target_id",
        String(36),
        ForeignKey("tblXMonitorTargets.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("author_username", Text, nullable=False),
    Column("author_user_id", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("text_raw", Text, nullable=False),
    Column("text_normalized", Text, nullable=False),
    Column("url", Text, nullable=False),
    Column("is_reply", Boolean, nullable=False, default=False),
    Column("is_retweet", Boolean, nullable=False, default=False),
    Column("has_media", Boolean, nullable=False, default=False),
    Column("lang", Text, nullable=True),
    Column("raw_json", JSON, nullable=False, default=dict),
    Column("inserted_at", DateTime(timezone=True), nullable=False),
)
Index("idxTblXMonitorPostsPostId", tbl_x_monitor_posts.c.post_id, unique=True)
Index(
    "idxTblXMonitorPostsTargetIdCreatedAt",
    tbl_x_monitor_posts.c.target_id,
    tbl_x_monitor_posts.c.created_at.desc(),
)
Index("idxTblXMonitorPostsCreatedAt", tbl_x_monitor_posts.c.created_at.desc())

tbl_x_monitor_post_matches = Table(
    "tblXMonitorPostMatches",
    X_MONITOR_METADATA,
    Column("id", String(36), primary_key=True),
    Column(
        "post_id",
        String(36),
        ForeignKey("tblXMonitorPosts.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "target_id",
        String(36),
        ForeignKey("tblXMonitorTargets.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("matched", Boolean, nullable=False),
    Column("matched_rules", JSON, nullable=False, default=list),
    Column("match_reason", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
)
Index(
    "idxTblXMonitorPostMatchesTargetIdCreatedAt",
    tbl_x_monitor_post_matches.c.target_id,
    tbl_x_monitor_post_matches.c.created_at.desc(),
)

tbl_x_monitor_notification_events = Table(
    "tblXMonitorNotificationEvents",
    X_MONITOR_METADATA,
    Column("id", String(36), primary_key=True),
    Column(
        "post_id",
        String(36),
        ForeignKey("tblXMonitorPosts.id", ondelete="SET NULL"),
        nullable=True,
    ),
    Column(
        "target_id",
        String(36),
        ForeignKey("tblXMonitorTargets.id", ondelete="SET NULL"),
        nullable=True,
    ),
    Column("kind", Text, nullable=False),
    Column("provider", Text, nullable=False),
    Column("recipient", Text, nullable=False),
    Column("subject", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("attempt_count", Integer, nullable=False, default=0),
    Column("last_attempt_at", DateTime(timezone=True), nullable=True),
    Column("sent_at", DateTime(timezone=True), nullable=True),
    Column("error_message", Text, nullable=True),
    Column("payload_json", JSON, nullable=False, default=dict),
    Column("idempotency_key", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)
Index(
    "idxTblXMonitorNotificationEventsIdempotencyKey",
    tbl_x_monitor_notification_events.c.idempotency_key,
    unique=True,
)

Table(
    "tblXMonitorFlowRuns",
    X_MONITOR_METADATA,
    Column("id", String(36), primary_key=True),
    Column("flow_name", Text, nullable=False),
    Column("prefect_flow_run_id", Text, nullable=True),
    Column("started_at", DateTime(timezone=True), nullable=False),
    Column("finished_at", DateTime(timezone=True), nullable=True),
    Column("status", Text, nullable=False),
    Column("counts_json", JSON, nullable=False, default=dict),
    Column("error_message", Text, nullable=True),
)

Table(
    "tblXMonitorDigestBookmarks",
    X_MONITOR_METADATA,
    Column("digest_key", Text, primary_key=True),
    Column("window_start", DateTime(timezone=True), nullable=False),
    Column("window_end", DateTime(timezone=True), nullable=False),
    Column("sent_at", DateTime(timezone=True), nullable=False),
    Column("recipient", Text, nullable=False),
)

tbl_x_monitor_operator_events = Table(
    "tblXMonitorOperatorEvents",
    X_MONITOR_METADATA,
    Column("id", String(36), primary_key=True),
    Column("event_type", Text, nullable=False),
    Column("severity", Text, nullable=False),
    Column("message", Text, nullable=False),
    Column("details_json", JSON, nullable=False, default=dict),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("dedupe_key", Text, nullable=True),
)
Index("idxTblXMonitorOperatorEventsDedupeKey", tbl_x_monitor_operator_events.c.dedupe_key)

