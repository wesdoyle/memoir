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
