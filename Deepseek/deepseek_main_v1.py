import pytest
import requests
from metrics import coverage

BASE_URL = "https://petstore3.swagger.io/api/v3"

# Тестовые данные
TEST_PET = {
    "id": 123456789,
    "name": "doggie",
    "category": {"id": 1, "name": "Dogs"},
    "photoUrls": ["string"],
    "tags": [{"id": 0, "name": "string"}],
    "status": "available"
}

INVALID_PET = {
    "id": "invalid_id",  # Неправильный тип ID
    "name": 123,  # Неправильный тип имени
    "status": "invalid_status"  # Неправильный статус
}


@pytest.fixture
def setup_pet():
    """Фикстура для создания тестового питомца и его удаления после теста"""
    # Создаем питомца
    response = requests.post(f"{BASE_URL}/pet", json=TEST_PET)
    assert response.status_code == 200
    pet_id = response.json()["id"]

    yield pet_id

    # Удаляем питомца после теста
    requests.delete(f"{BASE_URL}/pet/{pet_id}")


def test_add_pet():
    """Тест добавления питомца (POST /pet)"""
    response = requests.post(f"{BASE_URL}/pet", json=TEST_PET)
    coverage.record_test_result("POST /pet", response.status_code)
    assert response.status_code == 200
    assert response.json()["name"] == TEST_PET["name"]

    # Негативный тест с невалидными данными
    bad_response = requests.post(f"{BASE_URL}/pet", json=INVALID_PET)
    coverage.record_test_result("POST /pet", bad_response.status_code)
    assert bad_response.status_code in [400, 422]


def test_update_pet(setup_pet):
    """Тест обновления питомца (PUT /pet)"""
    pet_id = setup_pet
    updated_pet = {**TEST_PET, "name": "updated_doggie"}

    # Успешное обновление
    response = requests.put(f"{BASE_URL}/pet", json=updated_pet)
    coverage.record_test_result("PUT /pet", response.status_code)
    assert response.status_code == 200
    assert response.json()["name"] == "updated_doggie"

    # Негативный тест - обновление несуществующего питомца
    non_existent_pet = {**TEST_PET, "id": 999999999}
    bad_response = requests.put(f"{BASE_URL}/pet", json=non_existent_pet)
    coverage.record_test_result("PUT /pet", bad_response.status_code)
    assert bad_response.status_code == 404

    # Негативный тест с невалидными данными
    bad_response = requests.put(f"{BASE_URL}/pet", json=INVALID_PET)
    coverage.record_test_result("PUT /pet", bad_response.status_code)
    assert bad_response.status_code in [400, 422]


def test_find_pet_by_status():
    """Тест поиска питомцев по статусу (GET /pet/findByStatus)"""
    # Успешный запрос
    response = requests.get(f"{BASE_URL}/pet/findByStatus", params={"status": "available"})
    coverage.record_test_result("GET /pet/findByStatus", response.status_code)
    assert response.status_code == 200
    assert isinstance(response.json(), list)

    # Негативный тест - невалидный статус
    bad_response = requests.get(f"{BASE_URL}/pet/findByStatus", params={"status": "invalid"})
    coverage.record_test_result("GET /pet/findByStatus", bad_response.status_code)
    assert bad_response.status_code == 400


def test_find_pet_by_tags():
    """Тест поиска питомцев по тегам (GET /pet/findByTags)"""
    # Успешный запрос
    response = requests.get(f"{BASE_URL}/pet/findByTags", params={"tags": "string"})
    coverage.record_test_result("GET /pet/findByTags", response.status_code)
    assert response.status_code == 200
    assert isinstance(response.json(), list)

    # Негативный тест - невалидные теги
    bad_response = requests.get(f"{BASE_URL}/pet/findByTags", params={"tags": "invalid,tags"})
    coverage.record_test_result("GET /pet/findByTags", bad_response.status_code)
    assert bad_response.status_code == 400


def test_get_pet_by_id(setup_pet):
    """Тест получения питомца по ID (GET /pet/{petId})"""
    pet_id = setup_pet

    # Успешный запрос
    response = requests.get(f"{BASE_URL}/pet/{pet_id}")
    coverage.record_test_result("GET /pet/{petId}", response.status_code)
    assert response.status_code == 200
    assert response.json()["id"] == pet_id

    # Негативный тест - несуществующий ID
    bad_response = requests.get(f"{BASE_URL}/pet/999999999")
    coverage.record_test_result("GET /pet/{petId}", bad_response.status_code)
    assert bad_response.status_code == 404

    # Негативный тест - невалидный ID
    bad_response = requests.get(f"{BASE_URL}/pet/invalid_id")
    coverage.record_test_result("GET /pet/{petId}", bad_response.status_code)
    assert bad_response.status_code == 400


def test_update_pet_with_form_data(setup_pet):
    """Тест обновления питомца с form data (POST /pet/{petId})"""
    pet_id = setup_pet

    # Успешное обновление
    response = requests.post(
        f"{BASE_URL}/pet/{pet_id}",
        data={"name": "form_updated", "status": "pending"}
    )
    coverage.record_test_result("POST /pet/{petId}", response.status_code)
    assert response.status_code == 200

    # Негативный тест - невалидные данные
    bad_response = requests.post(
        f"{BASE_URL}/pet/{pet_id}",
        data={"name": 123, "status": "invalid"}
    )
    coverage.record_test_result("POST /pet/{petId}", bad_response.status_code)
    assert bad_response.status_code == 400


def test_delete_pet(setup_pet):
    """Тест удаления питомца (DELETE /pet/{petId})"""
    pet_id = setup_pet

    # Успешное удаление
    response = requests.delete(f"{BASE_URL}/pet/{pet_id}")
    coverage.record_test_result("DELETE /pet/{petId}", response.status_code)
    assert response.status_code == 200

    # Негативный тест - повторное удаление
    bad_response = requests.delete(f"{BASE_URL}/pet/{pet_id}")
    coverage.record_test_result("DELETE /pet/{petId}", bad_response.status_code)
    assert bad_response.status_code == 404

    # Негативный тест - невалидный ID
    bad_response = requests.delete(f"{BASE_URL}/pet/invalid_id")
    coverage.record_test_result("DELETE /pet/{petId}", bad_response.status_code)
    assert bad_response.status_code == 400


def test_upload_image(setup_pet):
    """Тест загрузки изображения (POST /pet/{petId}/uploadImage)"""
    pet_id = setup_pet

    # Успешная загрузка (мок файла)
    files = {'file': ('image.jpg', b'fake_image_data', 'image/jpeg')}
    response = requests.post(f"{BASE_URL}/pet/{pet_id}/uploadImage", files=files)
    coverage.record_test_result("POST /pet/{petId}/uploadImage", response.status_code)
    assert response.status_code == 200

    # Негативный тест - не поддерживаемый тип файла
    files = {'file': ('image.pdf', b'fake_pdf_data', 'application/pdf')}
    bad_response = requests.post(f"{BASE_URL}/pet/{pet_id}/uploadImage", files=files)
    coverage.record_test_result("POST /pet/{petId}/uploadImage", bad_response.status_code)
    assert bad_response.status_code == 415


def test_pet_crud_workflow():
    """End-to-end тест CRUD операций для питомца"""
    # 1. Создание питомца (Create)
    create_response = requests.post(f"{BASE_URL}/pet", json=TEST_PET)
    coverage.record_test_result("POST /pet", create_response.status_code)
    assert create_response.status_code == 200
    pet_id = create_response.json()["id"]

    # 2. Чтение питомца (Read)
    read_response = requests.get(f"{BASE_URL}/pet/{pet_id}")
    coverage.record_test_result("GET /pet/{petId}", read_response.status_code)
    assert read_response.status_code == 200
    assert read_response.json()["name"] == TEST_PET["name"]

    # 3. Обновление питомца (Update)
    updated_pet = {**TEST_PET, "name": "updated_name"}
    update_response = requests.put(f"{BASE_URL}/pet", json=updated_pet)
    coverage.record_test_result("PUT /pet", update_response.status_code)
    assert update_response.status_code == 200

    # Проверяем обновление
    read_updated_response = requests.get(f"{BASE_URL}/pet/{pet_id}")
    assert read_updated_response.json()["name"] == "updated_name"

    # 4. Удаление питомца (Delete)
    delete_response = requests.delete(f"{BASE_URL}/pet/{pet_id}")
    coverage.record_test_result("DELETE /pet/{petId}", delete_response.status_code)
    assert delete_response.status_code == 200

    # Проверяем удаление
    read_deleted_response = requests.get(f"{BASE_URL}/pet/{pet_id}")
    assert read_deleted_response.status_code == 404


def test_report_coverage():
    """Выводит отчет о покрытии API тестами"""
    metrics = coverage.calculate_metrics()

    print("\n" + "=" * 50)
    print("               API COVERAGE REPORT                ")
    print("=" * 50 + "\n")

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
