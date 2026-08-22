"""Identity keys: email normally; placeholder emails must not merge distinct people."""

from memoir.mining import Identity


def test_email_is_key_case_insensitively():
    assert Identity("A", "X@Example.com").key == Identity("B", "x@example.com").key


def test_placeholder_emails_do_not_merge_distinct_people():
    assert Identity("Marina", "no@email").key != Identity("Vadim", "no@email").key
    assert Identity("a", "").key != Identity("b", "").key
    assert Identity("a", "root@localhost").key != Identity("b", "root@localhost").key
    assert Identity("a", "x@metal.(none)").key != Identity("b", "y@metal.(none)").key


def test_placeholder_email_same_name_merges():
    assert Identity("Vadim Pisarevsky", "no@email").key == Identity("vadim pisarevsky", "no@email").key


def test_github_noreply_is_a_real_email():
    assert Identity("a", "1+a@users.noreply.github.com").key != Identity("b", "2+b@users.noreply.github.com").key


def test_bot_detection_covers_real_world_automation():
    assert Identity("dependabot[bot]", "x@users.noreply.github.com").is_bot
    assert Identity("Copilot", "198982749+Copilot@users.noreply.github.com").is_bot
    assert Identity("copilot-swe-agent[bot]", "198982749+Copilot@users.noreply.github.com").is_bot
    assert Identity("OpenCV Pushbot", "opencv.buildbot@gmail.com").is_bot
    assert Identity("elasticsearchmachine", "infra-root+elasticsearchmachine@elastic.co").is_bot
    assert Identity("renovate[bot]", "x").is_bot


def test_bot_detection_does_not_flag_humans_with_bot_substrings():
    assert not Identity("sunhaibotb", "sunhaibotb@163.com").is_bot
    assert not Identity("Geoffrey Mon", "geofbot@gmail.com").is_bot
    assert not Identity("Dmitry Chestnykh", "dmitry@codingrobots.com").is_bot
    assert not Identity("Abbott", "abbott@example.com").is_bot
