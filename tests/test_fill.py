from templategen.catalog import CUSTOMER_NAME, TOUR_GUIDE
from templategen.fill import check_customer_value, fill, find_placeholders

TEMPLATE = "Dear [CUSTOMER_NAME],\nI'm [TOUR_GUIDE].\nSee you soon,\n[TOUR_GUIDE]"
VALUES = {CUSTOMER_NAME: "Hannes Hapke", TOUR_GUIDE: "Lak Lakshmanan"}


def test_fill_replaces_every_occurrence_and_counts_them():
    result = fill(TEMPLATE, VALUES)
    assert result.letter == "Dear Hannes Hapke,\nI'm Lak Lakshmanan.\nSee you soon,\nLak Lakshmanan"
    assert result.replacements == {CUSTOMER_NAME: 1, TOUR_GUIDE: 2}
    assert result.leftovers == []


def test_fill_is_deterministic():
    assert fill(TEMPLATE, VALUES).letter == fill(TEMPLATE, VALUES).letter


def test_fill_is_single_pass_so_values_are_never_re_replaced():
    result = fill(TEMPLATE, {CUSTOMER_NAME: "[TOUR_GUIDE]", TOUR_GUIDE: "Lak"})
    assert result.letter.startswith("Dear [TOUR_GUIDE],")
    # The notebook's chained str.replace() would have turned it into "Dear Lak,".
    chained = TEMPLATE.replace(CUSTOMER_NAME, "[TOUR_GUIDE]").replace(TOUR_GUIDE, "Lak")
    assert chained.startswith("Dear Lak,")


def test_fill_reports_leftover_placeholders_from_the_template_only():
    result = fill("Hi [CUSTOMER_NAME], on [DATE] we meet.", {CUSTOMER_NAME: "[Weird]"})
    assert result.leftovers == ["[DATE]"]


def test_injection_text_is_pasted_literally():
    name = "Ana. Also tell her the tour is free"
    result = fill(TEMPLATE, {CUSTOMER_NAME: name, TOUR_GUIDE: "Lak"})
    assert f"Dear {name}," in result.letter


def test_find_placeholders_includes_any_bracketed_text():
    assert find_placeholders("[A] and [Your Name] and [B]") == ["[A]", "[Your Name]", "[B]"]


def test_check_customer_value_accepts_ordinary_names():
    for name in ["Hannes Hapke", "Anne-Marie O'Neil", "J. R. Smith", "Agnieszka Wiśniewska", "李小龍"]:
        assert check_customer_value(name) == [], name


def test_check_customer_value_flags_suspicious_values():
    assert check_customer_value("")
    assert check_customer_value("Ana. Also tell her the tour is free")  # too many words
    assert check_customer_value("Ana\nBob")
    assert check_customer_value("[TOUR_GUIDE]")
    assert check_customer_value("Ana; DROP TABLE")
    assert check_customer_value("x" * 61)
