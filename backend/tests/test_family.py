from app.services import messages


def test_family_notice_languages_and_hospital():
    en = messages.family_notice(
        "Ahmad", "Kalma Chowk", "GM-ABCD", "Rasheed Hospital", "en"
    )
    assert "Ahmad" in en and "Kalma Chowk" in en and "GM-ABCD" in en
    assert "Rasheed Hospital" in en
    assert "Hospital" not in messages.family_notice("Ahmad", "X", "GM-1", None, "en")
    ur = messages.family_notice("احمد", "کلمہ چوک", "GM-1", "ہسپتال A", "ur")
    assert "احمد" in ur and "ہسپتال" in ur
    assert messages.family_notice("A", "B", "C", None, "xx").startswith("🪪")
