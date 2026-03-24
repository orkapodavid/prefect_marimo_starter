from src.services.x_monitor.x_monitor_matching import evaluate_target_match


def test_match_keywords_any():
    result = evaluate_target_match(
        target={
            "include_replies": False,
            "include_retweets": False,
            "media_only": False,
            "keywords_any": ["earnings", "guidance"],
            "keywords_all": [],
            "regex_any": [],
        },
        post={
            "is_reply": False,
            "is_retweet": False,
            "has_media": False,
            "text_raw": "Quarterly earnings are out",
        },
    )
    assert result.matched is True
    assert "keywords_any" in result.matched_rules


def test_reject_reply_when_disabled():
    result = evaluate_target_match(
        target={
            "include_replies": False,
            "include_retweets": False,
            "media_only": False,
            "keywords_any": [],
            "keywords_all": [],
            "regex_any": [],
        },
        post={
            "is_reply": True,
            "is_retweet": False,
            "has_media": False,
            "text_raw": "Some reply text",
        },
    )
    assert result.matched is False


def test_reject_retweet_when_disabled():
    result = evaluate_target_match(
        target={
            "include_replies": False,
            "include_retweets": False,
            "media_only": False,
            "keywords_any": [],
            "keywords_all": [],
            "regex_any": [],
        },
        post={
            "is_reply": False,
            "is_retweet": True,
            "has_media": False,
            "text_raw": "RT: something",
        },
    )
    assert result.matched is False


def test_reject_no_media_when_media_only():
    result = evaluate_target_match(
        target={
            "include_replies": False,
            "include_retweets": False,
            "media_only": True,
            "keywords_any": [],
            "keywords_all": [],
            "regex_any": [],
        },
        post={
            "is_reply": False,
            "is_retweet": False,
            "has_media": False,
            "text_raw": "No media here",
        },
    )
    assert result.matched is False


def test_match_with_media_when_media_only():
    result = evaluate_target_match(
        target={
            "include_replies": False,
            "include_retweets": False,
            "media_only": True,
            "keywords_any": ["earnings"],
            "keywords_all": [],
            "regex_any": [],
        },
        post={
            "is_reply": False,
            "is_retweet": False,
            "has_media": True,
            "text_raw": "Quarterly earnings are out",
        },
    )
    assert result.matched is True


def test_match_keywords_all_requires_every_keyword():
    result = evaluate_target_match(
        target={
            "include_replies": False,
            "include_retweets": False,
            "media_only": False,
            "keywords_any": [],
            "keywords_all": ["earnings", "guidance"],
            "regex_any": [],
        },
        post={
            "is_reply": False,
            "is_retweet": False,
            "has_media": False,
            "text_raw": "Quarterly earnings are out",
        },
    )
    assert result.matched is False


def test_match_regex_any():
    result = evaluate_target_match(
        target={
            "include_replies": False,
            "include_retweets": False,
            "media_only": False,
            "keywords_any": [],
            "keywords_all": [],
            "regex_any": [r"\bSEC\b", r"\bpartnership\b"],
        },
        post={
            "is_reply": False,
            "is_retweet": False,
            "has_media": False,
            "text_raw": "Filed with the SEC today",
        },
    )
    assert result.matched is True
    assert "regex_any" in result.matched_rules


def test_no_rules_means_match_all():
    result = evaluate_target_match(
        target={
            "include_replies": False,
            "include_retweets": False,
            "media_only": False,
            "keywords_any": [],
            "keywords_all": [],
            "regex_any": [],
        },
        post={
            "is_reply": False,
            "is_retweet": False,
            "has_media": False,
            "text_raw": "Any post at all",
        },
    )
    assert result.matched is True
