from app.services import ambulance

LINE = [
    [74.0, 31.0],
    [74.0, 31.01],
    [74.01, 31.01],
]  # north ~1.1 km, then east ~0.95 km


def test_ambulances_needed():
    assert [ambulance.ambulances_needed(n) for n in (0, 1, 2, 5, 12, 40)] == [
        1,
        1,
        1,
        3,
        6,
        6,
    ]


def test_route_length_and_point_along():
    total = ambulance.route_length_m(LINE)
    assert 2000 < total < 2200
    assert ambulance.point_along(LINE, 0) == (31.0, 74.0)
    assert ambulance.point_along(LINE, total + 500) == (
        31.01,
        74.01,
    )  # clamped to the end
    lat, lng = ambulance.point_along(LINE, 555)  # halfway up the first leg
    assert abs(lat - 31.005) < 0.0005 and lng == 74.0
    lat2, lng2 = ambulance.point_along(LINE, 1500)  # on the second leg
    assert lat2 == 31.01 and 74.0 < lng2 < 74.01
