from cleartake import drift


def words(text):
    return [drift.Word(w, i * 0.5, i * 0.5 + 0.4) for i, w in enumerate(text.split())]


def test_identical_transcripts_have_no_drift():
    result = drift.compare(words("hello there, world."), words("Hello there world"))
    assert result["changes"] == [] and result["difference_rate"] == 0


def test_changed_dropped_and_added_words_are_labelled():
    before = words("we ship the build on friday night")
    after = words("we ship a build on friday")
    result = drift.compare(before, after)
    kinds = {c["kind"]: c for c in result["changes"]}
    assert kinds["changed"]["before"] == "the" and kinds["changed"]["after"] == "a"
    assert kinds["dropped"]["before"] == "night"
    assert (result["changed"], result["dropped"], result["added"]) == (1, 1, 0)
    assert result["difference_rate"] == round(2 / 7, 4)


def test_added_word_is_timestamped_from_the_result():
    result = drift.compare(words("one two"), words("one hello two"))
    change = result["changes"][0]
    assert change["kind"] == "added" and change["after"] == "hello" and change["start"] == 0.5


def test_empty_input_does_not_divide_by_zero():
    assert drift.compare([], [])["difference_rate"] == 0


def test_digits_and_number_words_count_as_the_same_word():
    before = [drift.Word("6", 0, 0.5), drift.Word("cats", 0.5, 1.0)]
    after = [drift.Word("Six", 0, 0.5), drift.Word("cats.", 0.5, 1.0)]
    assert drift.compare(before, after)["difference_rate"] == 0.0
