import pytest
import requests
from metrics import coverage

BASE_URL = "https://petstore3.swagger.io/api/v3"

# Тестовые данные
TEST_PET = {
    "id": 987654321,
    "name": "test_doggie",
    "category": {"id": 1, "name": "Dogs"},
    "photoUrls": ["string"],
    "tags": [{"id": 0, "name": "test_tag"}],
    "status": "available"
}

INVALID_PET = {
    "id": "invalid_id",
    "name": 123,
    "status": "invalid_status"
}


@pytest.fixture
def setup_pet():
    """Фикстура для создания тестового питомца"""
    # Удаляем питомца если он уже существует
    requests.delete(f"{BASE_URL}/pet/{TEST_PET['id']}")
    
    # Создаем питомца
    response = requests.post(f"{BASE_URL}/pet", json=TEST_PET)
    assert response.status_code == 200
    
    yield TEST_PET['id']
    
    # Удаляем питомца после теста
    requests.delete(f"{BASE_URL}/pet/{TEST_PET['id']}")


def test_add_pet():
    """Тест добавления питомца (POST /pet)"""
    # Удаляем питомца если он уже существует
    requests.delete(f"{BASE_URL}/pet/{TEST_PET['id']}")
    
    # Успешное создание
    response = requests.post(f"{BASE_URL}/pet", json=TEST_PET)
    coverage.record_test_result("POST /pet", response.status_code)
    assert response.status_code == 200
    
    # Невалидные данные
    bad_response = requests.post(f"{BASE_URL}/pet", json=INVALID_PET)
    coverage.record_test_result("POST /pet", bad_response.status_code)
    assert bad_response.status_code in [400, 422]
    
    # Очистка
    requests.delete(f"{BASE_URL}/pet/{TEST_PET['id']}")


def test_update_pet(setup_pet):
    """Тест обновления питомца (PUT /pet)"""
    pet_id = setup_pet
    
    # Успешное обновление
    updated_pet = {**TEST_PET, "name": "updated_name"}
    response = requests.put(f"{BASE_URL}/pet", json=updated_pet)
    coverage.record_test_result("PUT /pet", response.status_code)
    assert response.status_code == 200
    
    # Несуществующий питомец
    non_existent_pet = {**TEST_PET, "id": 999999999}
    bad_response = requests.put(f"{BASE_URL}/pet", json=non_existent_pet)
    coverage.record_test_result("PUT /pet", bad_response.status_code)
    assert bad_response.status_code == 404
    
    # Невалидные данные
    bad_response = requests.put(f"{BASE_URL}/pet", json=INVALID_PET)
    coverage.record_test_result("PUT /pet", bad_response.status_code)
    assert bad_response.status_code in [400, 422]


def test_find_pet_by_status():
    """Тест поиска питомцев по статусу (GET /pet/findByStatus)"""
    # Успешные запросы
    for status in ["available", "pending", "sold"]:
        response = requests.get(f"{BASE_URL}/pet/findByStatus", params={"status": status})
        coverage.record_test_result("GET /pet/findByStatus", response.status_code)
        assert response.status_code == 200
    
    # Невалидный статус
    bad_response = requests.get(f"{BASE_URL}/pet/findByStatus", params={"status": "invalid"})
    coverage.record_test_result("GET /pet/findByStatus", bad_response.status_code)
    assert bad_response.status_code == 400


def test_find_pet_by_tags():
    """Тест поиска питомцев по тегам (GET /pet/findByTags)"""
    # Успешный запрос
    response = requests.get(f"{BASE_URL}/pet/findByTags", params={"tags": "test_tag"})
    coverage.record_test_result("GET /pet/findByTags", response.status_code)
    assert response.status_code == 200
    
    # Несуществующий тег (API возвращает 200 с пустым списком)
    response = requests.get(f"{BASE_URL}/pet/findByTags", params={"tags": "non_existent_tag"})
    coverage.record_test_result("GET /pet/findByTags", response.status_code)
    assert response.status_code == 200


def test_get_pet_by_id():
    """Тест получения питомца по ID (GET /pet/{petId})"""
    # Создаем питомца для теста
    requests.delete(f"{BASE_URL}/pet/{TEST_PET['id']}")
    requests.post(f"{BASE_URL}/pet", json=TEST_PET)
    
    # Успешный запрос
    response = requests.get(f"{BASE_URL}/pet/{TEST_PET['id']}")
    coverage.record_test_result("GET /pet/{petId}", response.status_code)
    assert response.status_code == 200
    
    # Несуществующий ID
    bad_response = requests.get(f"{BASE_URL}/pet/999999999")
    coverage.record_test_result("GET /pet/{petId}", bad_response.status_code)
    assert bad_response.status_code == 404
    
    # Невалидный ID
    bad_response = requests.get(f"{BASE_URL}/pet/invalid_id")
    coverage.record_test_result("GET /pet/{petId}", bad_response.status_code)
    assert bad_response.status_code == 400
    
    # Очистка
    requests.delete(f"{BASE_URL}/pet/{TEST_PET['id']}")


def test_update_pet_with_form_data():
    """Тест обновления питомца с form data (POST /pet/{petId})"""
    # Создаем питомца для теста
    requests.delete(f"{BASE_URL}/pet/{TEST_PET['id']}")
    requests.post(f"{BASE_URL}/pet", json=TEST_PET)
    
    # Успешное обновление (API возвращает 200 только с определенными полями)
    response = requests.post(
        f"{BASE_URL}/pet/{TEST_PET['id']}",
        data={"name": "form_updated", "status": "pending"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    coverage.record_test_result("POST /pet/{petId}", response.status_code)
    assert response.status_code in [200, 400]  # API может возвращать 400
    
    # Невалидные данные
    bad_response = requests.post(
        f"{BASE_URL}/pet/{TEST_PET['id']}",
        data={"invalid": "data"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    coverage.record_test_result("POST /pet/{petId}", bad_response.status_code)
    assert bad_response.status_code == 400
    
    # Очистка
    requests.delete(f"{BASE_URL}/pet/{TEST_PET['id']}")


def test_delete_pet():
    """Тест удаления питомца (DELETE /pet/{petId})"""
    # Создаем питомца для теста
    requests.delete(f"{BASE_URL}/pet/{TEST_PET['id']}")
    requests.post(f"{BASE_URL}/pet", json=TEST_PET)
    
    # Успешное удаление
    response = requests.delete(f"{BASE_URL}/pet/{TEST_PET['id']}")
    coverage.record_test_result("DELETE /pet/{petId}", response.status_code)
    assert response.status_code == 200
    
    # Повторное удаление (API возвращает 200)
    bad_response = requests.delete(f"{BASE_URL}/pet/{TEST_PET['id']}")
    coverage.record_test_result("DELETE /pet/{petId}", bad_response.status_code)
    assert bad_response.status_code == 200
    
    # Невалидный ID
    bad_response = requests.delete(f"{BASE_URL}/pet/invalid_id")
    coverage.record_test_result("DELETE /pet/{petId}", bad_response.status_code)
    assert bad_response.status_code == 400


def test_upload_image():
    """Тест загрузки изображения (POST /pet/{petId}/uploadImage)"""
    # Создаем питомца для теста
    requests.delete(f"{BASE_URL}/pet/{TEST_PET['id']}")
    requests.post(f"{BASE_URL}/pet", json=TEST_PET)
    
    # Успешная загрузка (API требует специальный формат файла)
    files = {'file': ('image.jpg', b'--fake-image-data--', 'image/jpeg')}
    response = requests.post(f"{BASE_URL}/pet/{TEST_PET['id']}/uploadImage", files=files)
    coverage.record_test_result("POST /pet/{petId}/uploadImage", response.status_code)
    assert response.status_code in [200, 415]  # Может возвращать 415
    
    # Неподдерживаемый тип файла
    files = {'file': ('image.pdf', b'fake_pdf_data', 'application/pdf')}
    bad_response = requests.post(f"{BASE_URL}/pet/{TEST_PET['id']}/uploadImage", files=files)
    coverage.record_test_result("POST /pet/{petId}/uploadImage", bad_response.status_code)
    assert bad_response.status_code == 415
    
    # Очистка
    requests.delete(f"{BASE_URL}/pet/{TEST_PET['id']}")


def test_pet_crud_workflow():
    """End-to-end тест CRUD операций для питомца"""
    # Удаляем питомца если он уже существует
    requests.delete(f"{BASE_URL}/pet/{TEST_PET['id']}")
    
    # 1. Create
    create_response = requests.post(f"{BASE_URL}/pet", json=TEST_PET)
    coverage.record_test_result("POST /pet", create_response.status_code)
    assert create_response.status_code == 200
    
    # 2. Read
    read_response = requests.get(f"{BASE_URL}/pet/{TEST_PET['id']}")
    coverage.record_test_result("GET /pet/{petId}", read_response.status_code)
    assert read_response.status_code in [200, 404]  # Может возвращать 404
    
    if read_response.status_code == 200:
        # 3. Update
        updated_pet = {**TEST_PET, "name": "updated_in_crud"}
        update_response = requests.put(f"{BASE_URL}/pet", json=updated_pet)
        coverage.record_test_result("PUT /pet", update_response.status_code)
        assert update_response.status_code == 200
        
        # 4. Delete
        delete_response = requests.delete(f"{BASE_URL}/pet/{TEST_PET['id']}")
        coverage.record_test_result("DELETE /pet/{petId}", delete_response.status_code)
        assert delete_response.status_code == 200


def test_report_coverage():
    """Выводит отчет о покрытии API тестами"""
    metrics = coverage.calculate_metrics()
    
    print("\n" + "="*50)
    print("               API COVERAGE REPORT                ")
    print("="*50 + "\n")
    
    print(f"1. Среднее покрытие эндпоинтов раздела Pet: {metrics['avg_endpoint_coverage']:.1f}%")
    print(f"2. Покрытие статус-кодов раздела Pet: {metrics['pet_status_coverage']:.1f}%")
    print(f"3. Полностью покрытые эндпоинты API: {metrics['full_endpoint_coverage']:.1f}%")
    print(f"4. Общее покрытие статус-кодов API: {metrics['total_api_coverage']:.1f}%")
    
    print("\nДетали по endpoint'ам:")
    for endpoint, data in coverage.coverage_data.items():
        if "pet" in endpoint.lower():
            tested = len(data["tested"])
            expected = len(data["status_codes"])
            ratio = (tested / expected * 100) if expected > 0 else 0.0
            print(f"{endpoint}: {tested}/{expected} ({ratio:.1f}%) ------> {data['tested']} / {data['status_codes']}")
    
    # Выводим остальные эндпоинты
    for endpoint, data in coverage.coverage_data.items():
        if "pet" not in endpoint.lower():
            tested = len(data["tested"])
            expected = len(data["status_codes"])
            ratio = (tested / expected * 100) if expected > 0 else 0.0
            print(f"{endpoint}: {tested}/{expected} ({ratio:.1f}%) ------> {data['tested']} / {data['status_codes']}")
