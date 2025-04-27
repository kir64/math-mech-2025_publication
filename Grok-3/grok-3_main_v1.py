import pytest
import requests
import json
from metrics import coverage

BASE_URL = "https://petstore3.swagger.io/api/v3"
PET_ENDPOINT = "/pet"
PET_ID_ENDPOINT = "/pet/{petId}"
FIND_BY_STATUS_ENDPOINT = "/pet/findByStatus"
FIND_BY_TAGS_ENDPOINT = "/pet/findByTags"
UPLOAD_IMAGE_ENDPOINT = "/pet/{petId}/uploadImage"


@pytest.fixture
def pet_data():
    return {
        "id": 9999,
        "name": "TestPet",
        "category": {"id": 1, "name": "Dogs"},
        "photoUrls": ["string"],
        "tags": [{"id": 1, "name": "tag1"}],
        "status": "available"
    }


@pytest.fixture
def invalid_pet_data():
    return {
        "id": "invalid",  # Invalid type
        "name": "",  # Empty name
        "category": {},  # Empty category
        "photoUrls": [],  # Empty photoUrls
        "tags": [],  # Empty tags
        "status": "invalid"  # Invalid status
    }


# CRUD End-to-End Test
def test_pet_crud_e2e(pet_data):
    # Create (POST /pet)
    response = requests.post(f"{BASE_URL}{PET_ENDPOINT}", json=pet_data)
    assert response.status_code == 200
    coverage.record_test_result("POST /pet", response.status_code)

    pet_id = pet_data["id"]

    # Read (GET /pet/{petId})
    response = requests.get(f"{BASE_URL}{PET_ID_ENDPOINT.format(petId=pet_id)}")
    assert response.status_code == 200
    coverage.record_test_result("GET /pet/{petId}", response.status_code)

    # Update (PUT /pet)
    updated_pet = pet_data.copy()
    updated_pet["name"] = "UpdatedPet"
    response = requests.put(f"{BASE_URL}{PET_ENDPOINT}", json=updated_pet)
    assert response.status_code == 200
    coverage.record_test_result("PUT /pet", response.status_code)

    # Delete (DELETE /pet/{petId})
    response = requests.delete(f"{BASE_URL}{PET_ID_ENDPOINT.format(petId=pet_id)}")
    assert response.status_code == 200
    coverage.record_test_result("DELETE /pet/{petId}", response.status_code)


# Status Code Tests
def test_post_pet_valid(pet_data):
    response = requests.post(f"{BASE_URL}{PET_ENDPOINT}", json=pet_data)
    assert response.status_code == 200
    coverage.record_test_result("POST /pet", response.status_code)


def test_post_pet_invalid(invalid_pet_data):
    response = requests.post(f"{BASE_URL}{PET_ENDPOINT}", json=invalid_pet_data)
    assert response.status_code == 400
    coverage.record_test_result("POST /pet", response.status_code)


def test_put_pet_valid(pet_data):
    response = requests.post(f"{BASE_URL}{PET_ENDPOINT}", json=pet_data)
    response = requests.put(f"{BASE_URL}{PET_ENDPOINT}", json=pet_data)
    assert response.status_code == 200
    coverage.record_test_result("PUT /pet", response.status_code)


def test_put_pet_invalid_id():
    invalid_data = {"id": -1, "name": "Test", "status": "available"}
    response = requests.put(f"{BASE_URL}{PET_ENDPOINT}", json=invalid_data)
    assert response.status_code == 400
    coverage.record_test_result("PUT /pet", response.status_code)


def test_get_pet_by_id(pet_data):
    response = requests.post(f"{BASE_URL}{PET_ENDPOINT}", json=pet_data)
    response = requests.get(f"{BASE_URL}{PET_ID_ENDPOINT.format(petId=pet_data['id'])}")
    assert response.status_code == 200
    coverage.record_test_result("GET /pet/{petId}", response.status_code)


def test_get_pet_not_found():
    response = requests.get(f"{BASE_URL}{PET_ID_ENDPOINT.format(petId=999999)}")
    assert response.status_code == 404
    coverage.record_test_result("GET /pet/{petId}", response.status_code)


def test_find_by_status_valid():
    response = requests.get(f"{BASE_URL}{FIND_BY_STATUS_ENDPOINT}?status=available")
    assert response.status_code == 200
    coverage.record_test_result("GET /pet/findByStatus", response.status_code)


def test_find_by_status_invalid():
    response = requests.get(f"{BASE_URL}{FIND_BY_STATUS_ENDPOINT}?status=invalid")
    assert response.status_code == 400
    coverage.record_test_result("GET /pet/findByStatus", response.status_code)


def test_find_by_tags_valid(pet_data):
    response = requests.post(f"{BASE_URL}{PET_ENDPOINT}", json=pet_data)
    response = requests.get(f"{BASE_URL}{FIND_BY_TAGS_ENDPOINT}?tags=tag1")
    assert response.status_code == 200
    coverage.record_test_result("GET /pet/findByTags", response.status_code)


def test_delete_pet(pet_data):
    response = requests.post(f"{BASE_URL}{PET_ENDPOINT}", json=pet_data)
    response = requests.delete(f"{BASE_URL}{PET_ID_ENDPOINT.format(petId=pet_data['id'])}")
    assert response.status_code == 200
    coverage.record_test_result("DELETE /pet/{petId}", response.status_code)


# Negative Tests
def test_post_pet_missing_headers():
    response = requests.post(f"{BASE_URL}{PET_ENDPOINT}", json={}, headers={})
    assert response.status_code == 400
    coverage.record_test_result("POST /pet", response.status_code)


def test_upload_image_invalid():
    response = requests.post(f"{BASE_URL}{UPLOAD_IMAGE_ENDPOINT.format(petId=9999)}",
                             files={'file': ('test.txt', 'content')})
    assert response.status_code == 415
    coverage.record_test_result("POST /pet/{petId}/uploadImage", response.status_code)


# Run metrics after tests
def pytest_sessionfinish(session, exitstatus):
    metrics = coverage.calculate_metrics()

    print("\n==================================================")
    print("               API COVERAGE REPORT                ")
    print("==================================================\n")

    print(f"1. Среднее покрытие эндпоинтов раздела Pet: {metrics['avg_endpoint_coverage']:.1f}%")
    print(f"2. Покрытие статус-кодов раздела Pet: {metrics['pet_status_coverage']:.1f}%")
    print(f"3. Полностью покрытые эндпоинты API: {metrics['full_endpoint_coverage']:.1f}%")
    print(f"4. Общее покрытие статус-кодов API: {metrics['total_api_coverage']:.1f}%\n")

    print("Детали по endpoint'ам:")
    for endpoint, data in coverage.coverage_data.items():
        tested = data["tested"]
        expected = data["status_codes"]
        ratio = len(tested) / len(expected) * 100 if expected else 0
        print(f"{endpoint}: {len(tested)}/{len(expected)} ({ratio:.1f}%) ------> {tested} / {expected}")
