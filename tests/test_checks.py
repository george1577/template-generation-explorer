from templategen.checks import (
    ERROR, VERIFY, check_facts_to_verify, check_language, check_missing_placeholders,
    check_unknown_placeholders, guess_language, run_checks,
)

GOOD_EN = (
    "Dear [CUSTOMER_NAME],\n\nI'm [TOUR_GUIDE], and I'll be your guide for your family tour. "
    "We will see the cathedral and you can try the marzipan.\n\nSee you soon,\n[TOUR_GUIDE]"
)
GOOD_PL = (
    "Drogi [CUSTOMER_NAME],\n\nNazywam się [TOUR_GUIDE] i będę Państwa przewodnikiem w Toledo. "
    "Zobaczymy katedrę i spróbujemy marcepanu. Nie mogę się doczekać!\n\nDo zobaczenia,\n[TOUR_GUIDE]"
)


def test_clean_english_template_has_no_findings():
    assert run_checks(GOOD_EN, "English") == []


def test_clean_polish_template_has_no_findings():
    assert run_checks(GOOD_PL, "Polish") == []


def test_missing_placeholder():
    findings = check_missing_placeholders("Dear [CUSTOMER_NAME], see you soon!")
    assert [f.snippet for f in findings] == ["[TOUR_GUIDE]"]
    assert findings[0].severity == ERROR


def test_unknown_placeholder_listed_once():
    findings = check_unknown_placeholders("[CUSTOMER_NAME] [Your Name] [Your Name] [IMIĘ]")
    assert [f.snippet for f in findings] == ["[Your Name]", "[IMIĘ]"]


def test_language_guess():
    assert guess_language(GOOD_EN)[0] == "English"
    assert guess_language(GOOD_PL)[0] == "Polish"
    assert check_language(GOOD_EN, "Polish")[0].check == "wrong language"
    assert check_language(GOOD_PL, "Polish") == []


def test_facts_to_verify():
    text = (
        "The tour starts at 9:30 am on 12 May and costs €45. Call +34 912 345 678 "
        "or visit https://example.com. Zbiórka 3 maja, cena 200 zł."
    )
    kinds = [f.message.split("Mentions a ")[1].split(".")[0] for f in check_facts_to_verify(text)]
    assert kinds.count("price") == 2
    assert "time" in kinds and "date" in kinds
    assert "phone number" in kinds and "web or email address" in kinds
    assert all(f.severity == VERIFY for f in check_facts_to_verify(text))


def test_ordinary_text_has_no_facts():
    assert check_facts_to_verify(GOOD_EN) == []


def test_fact_snippets_show_the_whole_value():
    snippets = [f.snippet for f in check_facts_to_verify("Tickets cost €25.50 per person, or 100 zł.")]
    assert snippets == ["€25.50", "100 zł"]


def test_plain_numbers_are_not_facts():
    assert check_facts_to_verify("We have 2 hours. Built in 1226, 600 years ago.") == []
