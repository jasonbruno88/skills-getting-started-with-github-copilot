from copy import deepcopy

import pytest


def test_root_redirects_to_activity_page(client):
    # Arrange
    expected_location = "/static/index.html"

    # Act
    response = client.get("/", follow_redirects=False)

    # Assert
    assert response.status_code == 307
    assert response.headers["location"] == expected_location


def test_activity_page_is_served(client):
    # Arrange
    path = "/static/index.html"

    # Act
    response = client.get(path)

    # Assert
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Mergington High School" in response.text


def test_get_activities_returns_current_data(client, activity_data):
    # Arrange
    expected = deepcopy(activity_data)

    # Act
    response = client.get("/activities")

    # Assert
    assert response.status_code == 200
    assert response.json() == expected


@pytest.mark.parametrize("activity_name", ["Chess Club", "Art Club"])
def test_signup_adds_participant_once(client, activity_data, activity_name):
    # Arrange
    email = "new+student@school.edu"
    expected = deepcopy(activity_data)
    expected[activity_name]["participants"].append(email)

    # Act
    response = client.post(
        f"/activities/{activity_name}/signup", params={"email": email}
    )
    activities_response = client.get("/activities")

    # Assert
    assert response.status_code == 200
    assert response.json() == {"message": f"Signed up {email} for {activity_name}"}
    assert activities_response.status_code == 200
    assert activities_response.json() == expected
    assert activities_response.json()[activity_name]["participants"].count(email) == 1


@pytest.mark.parametrize("email", ["existing@school.edu", "new+student@school.edu"])
def test_duplicate_signup_does_not_change_activities(client, activity_data, email):
    # Arrange
    path = "/activities/Chess Club/signup"
    if email not in activity_data["Chess Club"]["participants"]:
        client.post(path, params={"email": email})
    before = client.get("/activities").json()

    # Act
    response = client.post(path, params={"email": email})
    activities_response = client.get("/activities")

    # Assert
    assert response.status_code == 400
    assert response.json() == {"detail": "Student already signed up for this activity"}
    assert activities_response.status_code == 200
    assert activities_response.json() == before


@pytest.mark.parametrize("method", ["POST", "DELETE"])
def test_unknown_activity_does_not_change_activities(client, activity_data, method):
    # Arrange
    expected = deepcopy(activity_data)
    path = "/activities/Unknown Club/signup"

    # Act
    response = client.request(method, path, params={"email": "student@school.edu"})
    activities_response = client.get("/activities")

    # Assert
    assert response.status_code == 404
    assert response.json() == {"detail": "Activity not found"}
    assert activities_response.status_code == 200
    assert activities_response.json() == expected


def test_unregister_removes_only_selected_participant(client, activity_data):
    # Arrange
    email = "existing@school.edu"
    expected = deepcopy(activity_data)
    expected["Chess Club"]["participants"].remove(email)

    # Act
    response = client.delete("/activities/Chess Club/signup", params={"email": email})
    activities_response = client.get("/activities")

    # Assert
    assert response.status_code == 200
    assert response.json() == {"message": f"Unregistered {email} from Chess Club"}
    assert activities_response.status_code == 200
    assert activities_response.json() == expected


@pytest.mark.parametrize("previously_registered", [False, True])
def test_unregister_missing_participant_preserves_state(client, previously_registered):
    # Arrange
    path = "/activities/Chess Club/signup"
    email = "existing@school.edu" if previously_registered else "absent@school.edu"
    if previously_registered:
        client.delete(path, params={"email": email})
    before = client.get("/activities").json()

    # Act
    response = client.delete(path, params={"email": email})
    activities_response = client.get("/activities")

    # Assert
    assert response.status_code == 400
    assert response.json() == {"detail": "Student is not signed up for this activity"}
    assert activities_response.status_code == 200
    assert activities_response.json() == before


@pytest.mark.parametrize("method", ["POST", "DELETE"])
def test_email_is_required(client, activity_data, method):
    # Arrange
    expected = deepcopy(activity_data)
    path = "/activities/Chess Club/signup"

    # Act
    response = client.request(method, path)
    activities_response = client.get("/activities")

    # Assert
    assert response.status_code == 422
    assert any(error["loc"] == ["query", "email"] for error in response.json()["detail"])
    assert activities_response.status_code == 200
    assert activities_response.json() == expected


def test_participant_can_register_again_after_unregistering(client, activity_data):
    # Arrange
    path = "/activities/Art Club/signup"
    email = "returning+student@school.edu"
    expected_registered = deepcopy(activity_data)
    expected_registered["Art Club"]["participants"].append(email)

    # Act
    signup_response = client.post(path, params={"email": email})
    after_signup = client.get("/activities")
    unregister_response = client.delete(path, params={"email": email})
    after_unregister = client.get("/activities")
    second_signup_response = client.post(path, params={"email": email})
    after_second_signup = client.get("/activities")

    # Assert
    assert signup_response.status_code == 200
    assert unregister_response.status_code == 200
    assert second_signup_response.status_code == 200
    assert after_signup.status_code == 200
    assert after_signup.json() == expected_registered
    assert after_unregister.status_code == 200
    assert after_unregister.json() == activity_data
    assert after_second_signup.status_code == 200
    assert after_second_signup.json() == expected_registered