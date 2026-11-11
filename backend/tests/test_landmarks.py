from app.models.ai import Landmark
from app.services import landmarks

LAT, LNG = 31.5036, 74.3305


def el(name, lat, lng, **tags):
    return {
        "type": "node",
        "id": 1,
        "lat": lat,
        "lon": lng,
        "tags": {"name": name, **tags},
    }


def test_rank_priority_distance_and_compass():
    elements = [
        el("Kalma Chowk", LAT, LNG - 0.0020, junction="roundabout"),  # ~200 m west
        el("Madni Masjid", LAT - 0.0008, LNG + 0.0008, amenity="place_of_worship"),
        el("PSO Petrol Pump", LAT + 0.0004, LNG, amenity="fuel"),  # ~45 m north
        el("Unnamed", LAT, LNG, amenity="fuel")
        | {"tags": {"amenity": "fuel"}},  # dropped: no name
        el("Far Away Bank", LAT + 0.01, LNG, amenity="bank"),  # beyond 300 m
    ]
    found = landmarks.rank(elements, LAT, LNG, "en")
    assert [lm.name for lm in found] == [
        "Madni Masjid",
        "PSO Petrol Pump",
        "Kalma Chowk",
    ]
    assert (
        found[0].compass == "SE" and found[1].compass == "N" and found[2].compass == "W"
    )
    assert [lm.index for lm in found] == [1, 2, 3]


def test_urdu_name_preferred_for_urdu():
    e = [
        el(
            "Mosque",
            LAT,
            LNG + 0.001,
            amenity="place_of_worship",
            **{"name:ur": "مسجد"},
        )
    ]
    assert landmarks.rank(e, LAT, LNG, "ur")[0].name == "مسجد"
    assert landmarks.rank(e, LAT, LNG, "en")[0].name == "Mosque"


LMS = [
    Landmark(index=1, kind="fuel", name="PSO Petrol Pump", distance_m=40, compass="N"),
    Landmark(
        index=2,
        kind="place_of_worship",
        name="Madni Masjid",
        distance_m=120,
        compass="SE",
    ),
]


def test_validation_accepts_grounded_line():
    en = "Near PSO Petrol Pump, 40 m north, close to Madni Masjid."
    assert landmarks.validate_landmark_line(en, en, [1, 2], LMS)


def test_validation_rejects_invented_names_and_distances():
    ok = "Near PSO Petrol Pump, 40 m north."
    assert not landmarks.validate_landmark_line(
        ok, "Near Shell Petrol Pump, 40 m north.", [1], LMS
    )  # name
    assert not landmarks.validate_landmark_line(
        ok, "Near PSO Petrol Pump, 400 m north.", [1], LMS
    )  # distance
    assert not landmarks.validate_landmark_line(ok, ok, [], LMS)  # nothing used
    assert not landmarks.validate_landmark_line(ok, ok, [9], LMS)  # unknown index
    assert not landmarks.validate_landmark_line(
        ok, ok + " see https://x.io", [1], LMS
    )  # url


def test_validation_converts_urdu_digits():
    en = "Near PSO Petrol Pump, 40 m north."
    assert landmarks.validate_landmark_line("پٹرول پمپ کے قریب ۴۰ میٹر", en, [1], LMS)
    assert not landmarks.validate_landmark_line(
        "پٹرول پمپ کے قریب ۹۰۰ میٹر", en, [1], LMS
    )


def test_template_lines():
    assert (
        landmarks.template_landmark_line(LMS, "en")
        == "Near PSO Petrol Pump (40 m N), close to Madni Masjid."
    )
    assert (
        landmarks.template_landmark_line(LMS, "ur")
        == "PSO Petrol Pump کے قریب (40 میٹر شمال)، Madni Masjid کے نزدیک۔"
    )
    assert landmarks.template_landmark_line(LMS, "es").startswith(
        "Cerca de PSO Petrol Pump (40 m norte)"
    )
    assert landmarks.template_landmark_line([], "en") == ""
    assert (
        landmarks.template_landmark_line(LMS[:1], "en")
        == "Near PSO Petrol Pump (40 m N)."
    )
