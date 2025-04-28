import pytest
import requests
from metrics import coverage

BASE_URL = "https://petstore3.swagger.io/api/v3"

# Помощник для отправки запросов и записи результатов в метрики
def make_request(method, endpoint, expected_status, **kwargs):
    url = f"{BASE_URL}{endpoint}"
    response = requests.request(method, url, **kwargs)
    coverage.record_test_result(f"{method.upper()} {endpoint}", response.status_code)
    assert response.status_code == expected_status, f"Expected {expected_status}, got {response.status_code}"
    return response

# Тесты для раздела Pet
@pytest.mark.pet
def test_update_pet():
    """PUT /pet: Обновление существующего питомца"""
    pet_data = {
        "id": 1,
        "name": "UpdatedPet",
        "status": "available"
    }
    make_request("PUT", "/pet", 200, json=pet_data)

@pytest.mark.pet
def test_create_pet():
    """POST /pet: Создание нового питомца"""
    pet_data = {
        "id": 2,
        "name": "NewPet",
        "status": "pending"
    }
    make_request("POST", "/pet", 200, json=pet_data)

@pytest.mark.pet
def test_find_pets_by_status():
    """GET /pet/findByStatus: Поиск питомцев по статусу"""
    params = {"status": "available"}
    make_request("GET", "/pet/findByStatus", 200, params=params)

@pytest.mark.pet
def test_find_pets_by_tags():
    """GET /pet/findByTags: Поиск питомцев по тегам"""
    params = {"tags": "tag1"}
    make_request("GET", "/pet/findByTags", 200, params=params)

@pytest.mark.pet
def test_get_pet_by_id():
    """GET /pet/{petId}: Получение питомца по ID"""
    pet_id = 1
    make_request("GET", f"/pet/{pet_id}", 200)

@pytest.mark.pet
def test_update_pet_with_form():
    """POST /pet/{petId}: Обновление питомца через форму"""
    pet_id = 1
    data = {"name": "FormUpdatedPet", "status": "sold"}
    make_request("POST", f"/pet/{pet_id}", 405, data=data)

@pytest.mark.pet
def test_delete_pet():
    """DELETE /pet/{petId}: Удаление питомца"""
    pet_id = 2
    make_request("DELETE", f"/pet/{pet_id}", 200)

@pytest.mark.pet
def test_upload_pet_image():
    """POST /pet/{petId}/uploadImage: Загрузка изображения питомца"""
    pet_id = 1
    files = {"file": ("test.jpg", open("test.jpg", "rb"), "image/jpeg")}
    make_request("POST", f"/pet/{pet_id}/uploadImage", 200, files=files)

# End-to-end тест
@pytest.mark.pet
def test_end_to_end_pet_crud():
    """End-to-end сценарий CRUD для питомца"""
    # Создание питомца
    pet_data = {
        "id": 3,
        "name": "CRUDPet",
        "status": "available"
    }
    create_response = make_request("POST", "/pet", 200, json=pet_data)
    pet_id = create_response.json()["id"]

    # Получение питомца
    make_request("GET", f"/pet/{pet_id}", 200)

    # Обновление питомца
    updated_data = {
        "id": pet_id,
        "name": "UpdatedCRUDPet",
        "status": "sold"
    }
    make_request("PUT", "/pet", 200, json=updated_data)

    # Удаление питомца
    make_request("DELETE", f"/pet/{pet_id}", 200)

# Негативные тесты
@pytest.mark.pet
def test_invalid_pet_id():
    """GET /pet/{petId}: Негативный тест с невалидным ID"""
    invalid_pet_id = 999999
    make_request("GET", f"/pet/{invalid_pet_id}", 404)

@pytest.mark.pet
def test_invalid_pet_data():
    """POST /pet: Негативный тест с невалидными данными"""
    invalid_pet_data = {
        "id": "invalid_id",
        "name": None,
        "status": "unknown"
    }
    make_request("POST", "/pet", 400, json=invalid_pet_data)

# Вывод метрик после выполнения тестов
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
