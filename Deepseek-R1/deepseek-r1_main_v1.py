import pytest
import requests
from metrics import coverage

BASE_URL = "https://petstore3.swagger.io/api/v3"


# Helper functions
def create_pet():
    pet_data = {
        "name": "TestPet",
        "photoUrls": ["http://example.com/photo.jpg"],
        "status": "available"
    }
    response = requests.post(f"{BASE_URL}/pet", json=pet_data)
    assert response.status_code == 200
    return response.json()["id"]


def delete_pet(pet_id):
    response = requests.delete(f"{BASE_URL}/pet/{pet_id}")
    if response.status_code == 200:
        print(f"Pet {pet_id} deleted")


# Tests for POST /pet
def test_create_pet_valid():
    pet_data = {
        "name": "ValidPet",
        "photoUrls": ["http://example.com/photo.jpg"],
        "status": "available"
    }
    response = requests.post(f"{BASE_URL}/pet", json=pet_data)
    assert response.status_code == 200
    coverage.record_test_result("POST /pet", response.status_code)
    delete_pet(response.json()["id"])


def test_create_pet_invalid():
    invalid_data = {"invalidField": "value"}
    response = requests.post(f"{BASE_URL}/pet", json=invalid_data)
    assert response.status_code in [400, 405]
    coverage.record_test_result("POST /pet", response.status_code)


# Tests for PUT /pet
def test_update_pet_valid():
    pet_id = create_pet()
    update_data = {
        "id": pet_id,
        "name": "UpdatedPet",
        "status": "sold"
    }
    response = requests.put(f"{BASE_URL}/pet", json=update_data)
    assert response.status_code == 200
    coverage.record_test_result("PUT /pet", response.status_code)
    delete_pet(pet_id)


def test_update_pet_not_found():
    update_data = {
        "id": 999999,
        "name": "Ghost",
        "status": "sold"
    }
    response = requests.put(f"{BASE_URL}/pet", json=update_data)
    assert response.status_code == 404
    coverage.record_test_result("PUT /pet", response.status_code)


# Tests for GET /pet/{petId}
def test_get_pet_valid():
    pet_id = create_pet()
    response = requests.get(f"{BASE_URL}/pet/{pet_id}")
    assert response.status_code == 200
    coverage.record_test_result("GET /pet/{petId}", response.status_code)
    delete_pet(pet_id)


def test_get_pet_invalid_id():
    response = requests.get(f"{BASE_URL}/pet/invalid_id")
    assert response.status_code == 400
    coverage.record_test_result("GET /pet/{petId}", response.status_code)


def test_get_pet_not_found():
    response = requests.get(f"{BASE_URL}/pet/999999")
    assert response.status_code == 404
    coverage.record_test_result("GET /pet/{petId}", response.status_code)


# Tests for DELETE /pet/{petId}
def test_delete_pet_valid():
    pet_id = create_pet()
    response = requests.delete(f"{BASE_URL}/pet/{pet_id}")
    assert response.status_code == 200
    coverage.record_test_result("DELETE /pet/{petId}", response.status_code)


def test_delete_pet_invalid_id():
    response = requests.delete(f"{BASE_URL}/pet/invalid_id")
    assert response.status_code == 400
    coverage.record_test_result("DELETE /pet/{petId}", response.status_code)


def test_delete_pet_not_found():
    response = requests.delete(f"{BASE_URL}/pet/999999")
    assert response.status_code == 404
    coverage.record_test_result("DELETE /pet/{petId}", response.status_code)


# Tests for GET /pet/findByStatus
def test_find_by_status_valid():
    response = requests.get(f"{BASE_URL}/pet/findByStatus", params={"status": "available"})
    assert response.status_code == 200
    coverage.record_test_result("GET /pet/findByStatus", response.status_code)


def test_find_by_status_invalid():
    response = requests.get(f"{BASE_URL}/pet/findByStatus", params={"status": "invalid"})
    assert response.status_code == 400
    coverage.record_test_result("GET /pet/findByStatus", response.status_code)


# Tests for POST /pet/{petId}/uploadImage
def test_upload_image_valid():
    pet_id = create_pet()
    files = {"file": ("image.jpg", b"fake_image_data", "image/jpeg")}
    response = requests.post(f"{BASE_URL}/pet/{pet_id}/uploadImage", files=files)
    assert response.status_code == 200
    coverage.record_test_result("POST /pet/{petId}/uploadImage", response.status_code)
    delete_pet(pet_id)


def test_upload_image_invalid():
    pet_id = create_pet()
    files = {"file": ("text.txt", b"text data", "text/plain")}
    response = requests.post(f"{BASE_URL}/pet/{pet_id}/uploadImage", files=files)
    assert response.status_code == 415
    coverage.record_test_result("POST /pet/{petId}/uploadImage", response.status_code)
    delete_pet(pet_id)


# End-to-end CRUD test
def test_pet_crud_flow():
    # Create
    pet_data = {
        "name": "CRUDPet",
        "photoUrls": ["http://example.com/photo.jpg"],
        "status": "available"
    }
    create_resp = requests.post(f"{BASE_URL}/pet", json=pet_data)
    assert create_resp.status_code == 200
    pet_id = create_resp.json()["id"]
    coverage.record_test_result("POST /pet", create_resp.status_code)

    # Read
    get_resp = requests.get(f"{BASE_URL}/pet/{pet_id}")
    assert get_resp.status_code == 200
    coverage.record_test_result("GET /pet/{petId}", get_resp.status_code)

    # Update
    update_data = {
        "id": pet_id,
        "name": "UpdatedCRUDPet",
        "status": "sold"
    }
    update_resp = requests.put(f"{BASE_URL}/pet", json=update_data)
    assert update_resp.status_code == 200
    coverage.record_test_result("PUT /pet", update_resp.status_code)

    # Delete
    delete_resp = requests.delete(f"{BASE_URL}/pet/{pet_id}")
    assert delete_resp.status_code == 200
    coverage.record_test_result("DELETE /pet/{petId}", delete_resp.status_code)

    # Verify delete
    get_deleted_resp = requests.get(f"{BASE_URL}/pet/{pet_id}")
    assert get_deleted_resp.status_code == 404
    coverage.record_test_result("GET /pet/{petId}", get_deleted_resp.status_code)


# Fixture to print coverage report
@pytest.fixture(scope="session", autouse=True)
def print_coverage(request):
    def report():
        metrics = coverage.calculate_metrics()
        print("\n==================================================")
        print("               API COVERAGE REPORT                ")
        print("==================================================\n")
        print(f"1. Среднее покрытие эндпоинтов раздела Pet: {metrics['avg_endpoint_coverage']:.1f}%")
        print(f"2. Покрытие статус-кодов раздела Pet: {metrics['pet_status_coverage']:.1f}%")
        print(f"3. Полностью покрытые эндпоинты API: {metrics['full_endpoint_coverage']:.1f}%")
        print(f"4. Общее покрытие статус-кодов API: {metrics['total_api_coverage']:.1f}%\n")
        print("Детали по endpoint'ам:")
        for endpoint in coverage.coverage_data:
            data = coverage.coverage_data[endpoint]
            tested = len(data["tested"])
            expected = len(data["status_codes"])
            ratio = (tested / expected * 100) if expected > 0 else 0.0
            print(f"{endpoint}: {tested}/{expected} ({ratio:.1f}%) ------> {data['tested']} / {data['status_codes']}")

    request.addfinalizer(report)
