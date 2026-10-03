import pytest

from app.game.models import GameError
from app.game.sanitize import clean_free_text, clean_name, unique_name


def test_clean_name_collapses_whitespace_and_truncates() -> None:
    assert clean_name('  Ada    Lovelace  ') == 'Ada Lovelace'
    assert clean_name('x' * 30) == 'x' * 20


def test_clean_name_rejects_too_short() -> None:
    with pytest.raises(GameError, match='at least 2'):
        clean_name(' a ')


def test_clean_name_rejects_blocked_words_but_allows_innocent_substrings() -> None:
    with pytest.raises(GameError, match='different name'):
        clean_name('Big Shit')
    assert clean_name('Dickens') == 'Dickens'


def test_unique_name_adds_numeric_suffix_case_insensitively() -> None:
    assert unique_name('Ada', {'ada', 'Ada2'}) == 'Ada3'
    assert unique_name('Bob', {'Ada'}) == 'Bob'


def test_unique_name_stays_within_max_length() -> None:
    long_name = 'x' * 20
    assert unique_name(long_name, {long_name}) == 'x' * 19 + '2'


def test_clean_free_text_masks_blocked_words_and_truncates() -> None:
    assert clean_free_text('show   me the shit', 200) == 'show me the ****'
    assert clean_free_text('a' * 300, 200) == 'a' * 200


def test_clean_free_text_rejects_blank_input() -> None:
    with pytest.raises(GameError, match='type something'):
        clean_free_text('   ', 200)


@pytest.mark.parametrize('name', ['ShitHead', 'fuckoff', 'BigDick99', 'fu​ck you'])
def test_clean_name_rejects_strong_words_hidden_inside_names(name: str) -> None:
    with pytest.raises(GameError, match='different name'):
        clean_name(name)


@pytest.mark.parametrize('name', ['Dickens', 'Arsenal Fan', 'Scunthorpe', 'Peacock', 'Sparse Matrix'])
def test_clean_name_allows_innocent_words(name: str) -> None:
    assert clean_name(name) == name


def test_clean_free_text_masks_strong_word_substrings_and_zero_width_tricks() -> None:
    assert clean_free_text('you ShitHead', 200) == 'you ****Head'
    assert clean_free_text('fu​ck this', 200) == '**** this'
    assert clean_free_text('parse the Dickens novel', 200) == 'parse the Dickens novel'
