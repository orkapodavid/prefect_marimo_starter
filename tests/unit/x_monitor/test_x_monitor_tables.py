from src.services.x_monitor.x_monitor_tables import X_MONITOR_METADATA


def test_x_monitor_table_names_follow_repo_conventions():
    table_names = set(X_MONITOR_METADATA.tables)

    assert "tblXMonitorTargets" in table_names
    assert "tblXMonitorTargetWatermarks" in table_names
    assert "tblXMonitorPosts" in table_names
    assert "tblXMonitorPostMatches" in table_names
    assert "tblXMonitorNotificationEvents" in table_names
    assert "tblXMonitorFlowRuns" in table_names
    assert "tblXMonitorDigestBookmarks" in table_names
    assert "tblXMonitorOperatorEvents" in table_names


def test_x_monitor_indexes_follow_repo_conventions():
    targets = X_MONITOR_METADATA.tables["tblXMonitorTargets"]
    index_names = {index.name for index in targets.indexes}
    assert "idxTblXMonitorTargetsUsername" in index_names

    posts = X_MONITOR_METADATA.tables["tblXMonitorPosts"]
    post_index_names = {index.name for index in posts.indexes}
    assert "idxTblXMonitorPostsPostId" in post_index_names
    assert "idxTblXMonitorPostsTargetIdCreatedAt" in post_index_names

    notif = X_MONITOR_METADATA.tables["tblXMonitorNotificationEvents"]
    notif_index_names = {index.name for index in notif.indexes}
    assert "idxTblXMonitorNotificationEventsIdempotencyKey" in notif_index_names


def test_x_monitor_notification_events_has_idempotency_key_column():
    notif = X_MONITOR_METADATA.tables["tblXMonitorNotificationEvents"]
    column_names = {col.name for col in notif.columns}
    assert "idempotency_key" in column_names
    assert "kind" in column_names
    assert "provider" in column_names
    assert "status" in column_names
