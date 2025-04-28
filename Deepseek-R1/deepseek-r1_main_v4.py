import pytest
import requests
import time
from metrics import coverage

BASE_URL = "https://petstore3.swagger.io/api/v3"
MAX_RETRIES = 3
RETRY_DELAY = 1


def create_pet_safe():
    """Создание питомца с полным набором обязательных полей"""
    pet_data = {
        "name": f"TestPet_{int(time.time())}",
        "photoUrls": ["https://example.com/photo.jpg"],
        "status": "available",
        "category": {"id": 1, "name": "Dogs"},
        "tags": [{"id": 1, "name": "test"}]
    }

    for _ in range(MAX_RETRIES):
        try:
            response = requests.post(
                f"{BASE_URL}/pet",
                json=pet_data,
                timeout=5
            )
            if response.status_code == 200:
                return response.json()["id"]
        except requests.exceptions.RequestException:
            pass
        time.sleep(RETRY_DELAY)
    pytest.fail("Не удалось создать тестового питомца")


@pytest.fixture
def test_pet():
    pet_id = create_pet_safe()
    yield pet_id
    for _ in range(MAX_RETRIES):
        response = requests.delete(f"{BASE_URL}/pet/{pet_id}")
        if response.status_code == 200:
            break
        time.sleep(RETRY_DELAY)


# 1. Тесты для POST /pet --------------------------------------------------------
def test_post_pet_minimal():
    """Создание с минимальными обязательными полями"""
    pet_data = {
        "name": "MinimalPet",
        "photoUrls": ["https://example.com/photo.jpg"],
        "status": "available"
    }
    response = requests.post(f"{BASE_URL}/pet", json=pet_data)
    assert response.status_code in [200, 201], f"Фактический код: {response.status_code}"
    coverage.record_test_result("POST /pet", response.status_code)


# 2. Тесты для PUT /pet ---------------------------------------------------------
def test_put_pet_full_update(test_pet):
    """Полное обновление существующего питомца"""
    update_data = {
        "id": test_pet,
        "name": "UpdatedPet",
        "status": "sold",
        "photoUrls": ["https://new.com/photo.jpg"],
        "category": {"id": 2, "name": "Cats"}
    }

    response = requests.put(f"{BASE_URL}/pet", json=update_data)
    assert response.status_code in [200, 204], f"Фактический код: {response.status_code}"
    coverage.record_test_result("PUT /pet", response.status_code)


# 3. Тесты для GET /pet/{petId} -------------------------------------------------
def test_get_pet_exists(test_pet):
    response = requests.get(f"{BASE_URL}/pet/{test_pet}")
    assert response.status_code == 200, f"Фактический код: {response.status_code}"
    coverage.record_test_result("GET /pet/{petId}", 200)


# 4. Тесты для DELETE /pet/{petId} ----------------------------------------------
def test_delete_pet_with_confirmation(test_pet):
    response = requests.delete(f"{BASE_URL}/pet/{test_pet}")
    assert response.status_code == 200, f"Фактический код: {response.status_code}"
    coverage.record_test_result("DELETE /pet/{petId}", 200)


# 5. Тесты для GET /pet/findByStatus --------------------------------------------
@pytest.mark.parametrize("status", ["available", "pending", "sold"])
def test_find_by_status_valid(status):
    response = requests.get(f"{BASE_URL}/pet/findByStatus", params={"status": status})
    assert response.status_code == 200, f"Фактический код: {response.status_code}"
    coverage.record_test_result("GET /pet/findByStatus", 200)


# 6. Тесты для POST /pet/{petId}/uploadImage ------------------------------------
def test_upload_image_valid(test_pet):
    files = {'file': ('image.jpg', b'content', 'image/jpeg')}
    response = requests.post(
        f"{BASE_URL}/pet/{test_pet}/uploadImage",
        files=files,
        headers={"Content-Type": "multipart/form-data"}
    )
    assert response.status_code == 200, f"Фактический код: {response.status_code}"
    coverage.record_test_result("POST /pet/{petId}/uploadImage", 200)


# Фикстура для отчетности
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

    request.addfinalizer(report)
