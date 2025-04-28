import pytest
import requests
from metrics import coverage

BASE_URL = "https://petstore3.swagger.io/api/v3"


# Helper functions с обработкой ошибок
def create_test_pet():
    """Создание питомца с валидными данными и обработкой 500 ошибки"""
    pet_data = {
        "id": 999888777,
        "name": "TestPet",
        "photoUrls": ["https://example.com/photo.jpg"],
        "status": "available",
        "category": {"id": 1, "name": "Dogs"},
        "tags": [{"id": 1, "name": "trained"}]
    }
    try:
        response = requests.post(f"{BASE_URL}/pet", json=pet_data, timeout=5)
        if response.status_code == 200:
            return response.json()["id"]
        return None
    except requests.exceptions.RequestException:
        return None


def clean_test_pet(pet_id):
    """Гарантированная очистка тестовых данных"""
    try:
        requests.delete(f"{BASE_URL}/pet/{pet_id}", timeout=3)
    except requests.exceptions.RequestException:
        pass


# Фикстура для тестовых данных
@pytest.fixture
def test_pet():
    pet_id = create_test_pet()
    yield pet_id
    if pet_id:
        clean_test_pet(pet_id)


# 1. Тесты для POST /pet --------------------------------------------------------
def test_post_pet_success(test_pet):
    """Позитивный тест создания питомца (200 OK)"""
    assert test_pet is not None
    coverage.record_test_result("POST /pet", 200)


def test_post_pet_invalid_data():
    """Невалидные данные (400 Bad Request)"""
    response = requests.post(f"{BASE_URL}/pet", json={"invalid": "data"})
    assert response.status_code in [400, 415]
    coverage.record_test_result("POST /pet", response.status_code)


# 2. Тесты для PUT /pet ---------------------------------------------------------
def test_put_pet_success(test_pet):
    """Успешное обновление питомца (200 OK)"""
    update_data = {
        "id": test_pet,
        "name": "UpdatedPet",
        "status": "sold",
        "photoUrls": ["https://new-url.com/photo.jpg"]
    }
    response = requests.put(f"{BASE_URL}/pet", json=update_data)
    assert response.status_code == 200
    coverage.record_test_result("PUT /pet", 200)


def test_put_pet_invalid_id():
    """Невалидный ID (404 Not Found)"""
    response = requests.put(f"{BASE_URL}/pet", json={"id": "invalid"})
    assert response.status_code == 404
    coverage.record_test_result("PUT /pet", 404)


# 3. Тесты для GET /pet/{petId} -------------------------------------------------
def test_get_pet_success(test_pet):
    """Успешное получение питомца (200 OK)"""
    response = requests.get(f"{BASE_URL}/pet/{test_pet}")
    assert response.status_code == 200
    coverage.record_test_result("GET /pet/{petId}", 200)


def test_get_pet_not_found():
    """Питомец не найден (404 Not Found)"""
    response = requests.get(f"{BASE_URL}/pet/999999999")
    assert response.status_code == 404
    coverage.record_test_result("GET /pet/{petId}", 404)


# 4. Тесты для DELETE /pet/{petId} ----------------------------------------------
def test_delete_pet_success(test_pet):
    """Успешное удаление питомца (200 OK)"""
    response = requests.delete(f"{BASE_URL}/pet/{test_pet}")
    assert response.status_code == 200
    coverage.record_test_result("DELETE /pet/{petId}", 200)


def test_delete_pet_invalid_id():
    """Невалидный ID (400 Bad Request)"""
    response = requests.delete(f"{BASE_URL}/pet/invalid_id")
    assert response.status_code == 400
    coverage.record_test_result("DELETE /pet/{petId}", 400)


# 5. Тесты для GET /pet/findByStatus --------------------------------------------
@pytest.mark.parametrize("status", ["available", "pending", "sold"])
def test_find_by_status_valid(status):
    """Различные валидные статусы (200 OK)"""
    response = requests.get(f"{BASE_URL}/pet/findByStatus", params={"status": status})
    assert response.status_code == 200
    coverage.record_test_result("GET /pet/findByStatus", 200)


def test_find_by_status_invalid():
    """Невалидный статус (400 Bad Request)"""
    response = requests.get(f"{BASE_URL}/pet/findByStatus", params={"status": "invalid"})
    assert response.status_code == 400
    coverage.record_test_result("GET /pet/findByStatus", 400)


# 6. Тесты для POST /pet/{petId}/uploadImage ------------------------------------
def test_upload_image_success(test_pet):
    """Успешная загрузка изображения (200 OK)"""
    files = {'file': ('image.jpg', b'content', 'image/jpeg')}
    response = requests.post(f"{BASE_URL}/pet/{test_pet}/uploadImage", files=files)
    assert response.status_code == 200
    coverage.record_test_result("POST /pet/{petId}/uploadImage", 200)


def test_upload_image_invalid_type(test_pet):
    """Неверный тип файла (415 Unsupported Media Type)"""
    files = {'file': ('file.txt', b'text', 'text/plain')}
    response = requests.post(f"{BASE_URL}/pet/{test_pet}/uploadImage", files=files)
    assert response.status_code == 415
    coverage.record_test_result("POST /pet/{petId}/uploadImage", 415)


# End-to-End CRUD тест ---------------------------------------------------------
def test_full_pet_lifecycle():
    # Create
    pet_data = {
        "id": 987654321,
        "name": "FullLifecyclePet",
        "photoUrls": ["https://lifecycle.com/photo.jpg"],
        "status": "pending",
        "category": {"id": 2, "name": "Cats"}
    }
    create_resp = requests.post(f"{BASE_URL}/pet", json=pet_data)
    assert create_resp.status_code == 200
    pet_id = create_resp.json()["id"]
    coverage.record_test_result("POST /pet", 200)

    # Read
    get_resp = requests.get(f"{BASE_URL}/pet/{pet_id}")
    assert get_resp.status_code == 200
    coverage.record_test_result("GET /pet/{petId}", 200)

    # Update
    update_data = {"id": pet_id, "status": "sold"}
    update_resp = requests.put(f"{BASE_URL}/pet", json=update_data)
    assert update_resp.status_code == 200
    coverage.record_test_result("PUT /pet", 200)

    # Delete
    delete_resp = requests.delete(f"{BASE_URL}/pet/{pet_id}")
    assert delete_resp.status_code == 200
    coverage.record_test_result("DELETE /pet/{petId}", 200)

    # Verify
    verify_resp = requests.get(f"{BASE_URL}/pet/{pet_id}")
    assert verify_resp.status_code == 404
    coverage.record_test_result("GET /pet/{petId}", 404)


# Фикстура для отчетности
@pytest.fixture(scope="session", autouse=True)
def print_coverage_report(request):
    def finalizer():
        metrics = coverage.calculate_metrics()

        print("\n" + "=" * 50)
        print("           API COVERAGE REPORT")
        print("=" * 50 + "\n")

        print(f"1. Pet endpoints coverage: {metrics['avg_endpoint_coverage']:.1f}%")
        print(f"2. Pet status codes coverage: {metrics['pet_status_coverage']:.1f}%")
        print(f"3. Fully covered endpoints: {metrics['full_endpoint_coverage']:.1f}%")
        print(f"4. Total API coverage: {metrics['total_api_coverage']:.1f}%\n")

        print("Endpoint details:")
        for endpoint in sorted(coverage.coverage_data):
            data = coverage.coverage_data[endpoint]
            tested = len(data["tested"])
            total = len(data["status_codes"])
            print(f"{endpoint}: {tested}/{total} ({tested / total * 100:.1f}%)")

    request.addfinalizer(finalizer)
