import pytest
import requests
import json
from metrics import coverage

BASE_URL = "https://petstore3.swagger.io/api/v3"

def create_pet():
    return {
        "category": {"id": 0, "name": "string"},
        "name": "doggie",
        "photoUrls": ["string"],
        "tags": [{"id": 0, "name": "string"}],
        "status": "available"
    }

def update_pet(pet_id):
    return {
        "id": pet_id,
        "category": {"id": 1, "name": "updated_string"},
        "name": "updated_doggie",
        "photoUrls": ["updated_string"],
        "tags": [{"id": 1, "name": "updated_string"}],
        "status": "sold"
    }

@pytest.fixture
def pet_id():
    """Фикстура для создания и получения ID нового питомца."""
    pet_data = create_pet()
    response = requests.post(f"{BASE_URL}/pet", json=pet_data)
    assert response.status_code == 200, f"Failed to create pet: {response.text}"
    pet_id = response.json()["id"]
    yield pet_id
    # Cleanup: delete the created pet
    delete_response = requests.delete(f"{BASE_URL}/pet/{pet_id}")
    assert delete_response.status_code in [200, 404], f"Failed to delete pet {pet_id}: {delete_response.text}"

def validate_status_codes(endpoint, method, expected_statuses):
    """Вспомогательная функция для валидации статус-кодов."""
    url = f"{BASE_URL}{endpoint}"
    if method == "GET":
        response = requests.get(url)
    elif method == "POST":
        response = requests.post(url, json={}) # Пустой body для проверки статус-кодов
    elif method == "PUT":
        response = requests.put(url, json={}) # Пустой body для проверки статус-кодов
    elif method == "DELETE":
        response = requests.delete(url)
    else:
        pytest.fail(f"Unsupported HTTP method: {method}")

    coverage.record_test_result(f"{method.upper()} {endpoint}", response.status_code)
    assert str(response.status_code) in expected_statuses, \
        f"Unexpected status code {response.status_code} for {method} {endpoint}, expected {expected_statuses}"

def get_expected_status_codes(endpoint, method):
    """Получает ожидаемые статус-коды из загруженной спецификации."""
    key = f"{method.upper()} {endpoint}"
    return coverage.coverage_data.get(key, {}).get("status_codes", [])

# Тесты для валидации эндпоинтов по документации
def test_validate_put_pet_status_codes():
    validate_status_codes("/pet", "PUT", get_expected_status_codes("/pet", "PUT"))

def test_validate_post_pet_status_codes():
    validate_status_codes("/pet", "POST", get_expected_status_codes("/pet", "POST"))

def test_validate_get_pet_find_by_status_status_codes():
    validate_status_codes("/pet/findByStatus?status=available", "GET", get_expected_status_codes("/pet/findByStatus", "GET"))

def test_validate_get_pet_find_by_tags_status_codes():
    validate_status_codes("/pet/findByTags?tags=string", "GET", get_expected_status_codes("/pet/findByTags", "GET"))

def test_validate_get_pet_by_id_status_codes(pet_id):
    validate_status_codes(f"/pet/{pet_id}", "GET", get_expected_status_codes("/pet/{petId}", "GET"))

def test_validate_post_pet_by_id_status_codes(pet_id):
    validate_status_codes(f"/pet/{pet_id}", "POST", get_expected_status_codes("/pet/{petId}", "POST"))

def test_validate_delete_pet_by_id_status_codes(pet_id):
    validate_status_codes(f"/pet/{pet_id}", "DELETE", get_expected_status_codes("/pet/{petId}", "DELETE"))

def test_validate_post_pet_upload_image_status_codes(pet_id):
    url = f"{BASE_URL}/pet/{pet_id}/uploadImage"
    files = {'file': ('test.txt', b'test content', 'text/plain')}
    response = requests.post(url, files=files)
    coverage.record_test_result(f"POST /pet/{{petId}}/uploadImage", response.status_code)
    assert str(response.status_code) in get_expected_status_codes("/pet/{petId}/uploadImage", "POST"), \
        f"Unexpected status code {response.status_code} for POST /pet/{{petId}}/uploadImage, expected {get_expected_status_codes('/pet/{petId}/uploadImage', 'POST')}"

# End-to-end кейс с CRUD-операциями
def test_create_read_update_delete_pet():
    # Create
    pet_data = create_pet()
    create_response = requests.post(f"{BASE_URL}/pet", json=pet_data)
    assert create_response.status_code == 200
    coverage.record_test_result("POST /pet", create_response.status_code)
    pet_id = create_response.json()["id"]

    # Read
    read_response = requests.get(f"{BASE_URL}/pet/{pet_id}")
    assert read_response.status_code == 200
    coverage.record_test_result(f"GET /pet/{{petId}}", read_response.status_code)
    assert read_response.json()["name"] == "doggie"

    # Update
    updated_pet_data = update_pet(pet_id)
    update_response = requests.put(f"{BASE_URL}/pet", json=updated_pet_data)
    assert update_response.status_code == 200
    coverage.record_test_result("PUT /pet", update_response.status_code)
    updated_read_response = requests.get(f"{BASE_URL}/pet/{pet_id}")
    assert updated_read_response.status_code == 200
    assert updated_read_response.json()["name"] == "updated_doggie"
    assert updated_read_response.json()["status"] == "sold"

    # Delete
    delete_response = requests.delete(f"{BASE_URL}/pet/{pet_id}")
    assert delete_response.status_code == 200
    coverage.record_test_result(f"DELETE /pet/{{petId}}", delete_response.status_code)
    get_after_delete_response = requests.get(f"{BASE_URL}/pet/{pet_id}")
    assert get_after_delete_response.status_code == 404
    coverage.record_test_result(f"GET /pet/{{petId}}", get_after_delete_response.status_code)

# Негативные проверки
def test_create_pet_with_invalid_status():
    invalid_pet_data = create_pet()
    invalid_pet_data["status"] = "invalid_status"
    response = requests.post(f"{BASE_URL}/pet", json=invalid_pet_data)
    coverage.record_test_result("POST /pet", response.status_code)
    assert response.status_code == 400 # Или другой ожидаемый код ошибки

def test_get_pet_with_invalid_id():
    invalid_id = "invalid_id"
    response = requests.get(f"{BASE_URL}/pet/{invalid_id}")
    coverage.record_test_result(f"GET /pet/{{petId}}", response.status_code)
    assert response.status_code == 400

def test_update_pet_with_missing_required_field(pet_id):
    invalid_pet_data = {"name": "incomplete_pet"}
    response = requests.put(f"{BASE_URL}/pet", json=invalid_pet_data)
    coverage.record_test_result("PUT /pet", response.status_code)
    assert response.status_code in [400, 405] # Зависит от реализации API

def test_post_pet_upload_image_with_no_file(pet_id):
    url = f"{BASE_URL}/pet/{pet_id}/uploadImage"
    response = requests.post(url)
    coverage.record_test_result(f"POST /pet/{{petId}}/uploadImage", response.status_code)
    assert response.status_code in [400, 415] # Зависит от реализации API

@pytest.fixture(scope="session", autouse=True)
def final_report():
    yield
    metrics = coverage.calculate_metrics()
    print("\n==================================================")
    print("\t\t\tAPI COVERAGE REPORT\t\t\t\t")
    print("==================================================")
    print(f"1. Среднее покрытие эндпоинтов раздела Pet: {metrics['avg_endpoint_coverage']:.1f}%")
    print(f"2. Покрытие статус-кодов раздела Pet: {metrics['pet_status_coverage']:.1f}%")
    print(f"3. Полностью покрытые эндпоинты API: {metrics['full_endpoint_coverage']:.1f}%")
    print(f"4. Общее покрытие статус-кодов API: {metrics['total_api_coverage']:.1f}%")
    print("\nДетали по endpoint'ам:")
    for endpoint, data in coverage.coverage_data.items():
        expected_count = len(data["status_codes"])
        tested_count = len(data["tested"])
        coverage_percentage = (tested_count / expected_count * 100) if expected_count > 0 else 0.0
        print(f"{endpoint}: {tested_count}/{expected_count} ({coverage_percentage:.1f}%) ------> {sorted(data['tested'])} / {sorted(data['status_codes'])}")
    print("\n=========================")
