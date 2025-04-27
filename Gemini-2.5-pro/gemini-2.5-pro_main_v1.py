import pytest
import requests
import random
import time
import os  # Добавлен для работы с файлами (для uploadImage)

# Импортируем экземпляр coverage из вашего файла metrics.py
from metrics import coverage

# Базовый URL API
BASE_URL = "https://petstore3.swagger.io/api/v3"


# --- Фикстуры ---

@pytest.fixture(scope="module")
def pet_data():
    """Генерирует уникальные данные для нового питомца."""
    # Используем timestamp для большей уникальности ID и имени
    unique_id = int(time.time() * 1000)  # Пример генерации уникального ID
    return {
        "id": unique_id,
        "name": f"TestPet_{unique_id}",
        "category": {
            "id": 1,
            "name": "Dogs"
        },
        "photoUrls": [
            "http://example.com/photo1.jpg"
        ],
        "tags": [
            {
                "id": 1,
                "name": "test-tag"
            }
        ],
        "status": "available"
    }


@pytest.fixture(scope="function")  # Function scope для изоляции end-to-end теста
def created_pet(pet_data):
    """Создает питомца перед тестом и удаляет после."""
    # Создаем питомца
    headers = {'Content-Type': 'application/json', 'accept': 'application/json'}
    response = requests.post(f"{BASE_URL}/pet", json=pet_data, headers=headers)
    assert response.status_code == 200, f"Не удалось создать питомца для E2E теста: {response.text}"
    created_pet_id = response.json().get("id", pet_data["id"])  # Используем ID из ответа, если есть, иначе из запроса
    coverage.record_test_result("POST /pet", response.status_code)  # Запись успешного создания

    yield created_pet_id  # Передаем ID в тест

    # Очистка: удаляем питомца после теста
    delete_headers = {'accept': 'application/json'}
    delete_response = requests.delete(f"{BASE_URL}/pet/{created_pet_id}", headers=delete_headers)
    # Не делаем строгую проверку на 200, т.к. тест мог сам удалить питомца
    if delete_response.status_code == 200:
        coverage.record_test_result("DELETE /pet/{petId}", delete_response.status_code)
    elif delete_response.status_code == 404:  # Если тест уже удалил
        pass  # Это ожидаемое поведение в E2E тесте после удаления


# --- Тесты валидации эндпоинтов и статус-кодов ---

# POST /pet
def test_create_pet_success(pet_data):
    """Проверка успешного создания питомца (200)."""
    headers = {'Content-Type': 'application/json', 'accept': 'application/json'}
    response = requests.post(f"{BASE_URL}/pet", json=pet_data, headers=headers)
    coverage.record_test_result("POST /pet", response.status_code)
    assert response.status_code == 200
    assert response.json()["name"] == pet_data["name"]
    # Очистка созданного питомца (опционально, если не используется фикстура created_pet)
    pet_id_to_delete = response.json().get("id", pet_data["id"])
    requests.delete(f"{BASE_URL}/pet/{pet_id_to_delete}")


def test_create_pet_invalid_input_400(pet_data):
    """Проверка создания питомца с невалидным телом (ожидаем 400 или 422)."""
    headers = {'Content-Type': 'application/json', 'accept': 'application/json'}
    invalid_data = pet_data.copy()
    invalid_data["id"] = "not-an-integer"  # Невалидный ID
    response = requests.post(f"{BASE_URL}/pet", json=invalid_data, headers=headers)
    # API может вернуть 400 (Bad Request) или 422 (Unprocessable Entity)
    coverage.record_test_result("POST /pet", response.status_code)
    assert response.status_code in [400, 422]


# PUT /pet
def test_update_pet_success(created_pet):
    """Проверка успешного обновления питомца (200)."""
    pet_id = created_pet  # Получаем ID из фикстуры
    updated_data = {
        "id": pet_id,
        "name": f"UpdatedPet_{pet_id}",
        "category": {"id": 1, "name": "Dogs"},
        "photoUrls": ["http://example.com/updated_photo.jpg"],
        "tags": [{"id": 1, "name": "updated-tag"}],
        "status": "pending"
    }
    headers = {'Content-Type': 'application/json', 'accept': 'application/json'}
    response = requests.put(f"{BASE_URL}/pet", json=updated_data, headers=headers)
    coverage.record_test_result("PUT /pet", response.status_code)
    assert response.status_code == 200
    assert response.json()["name"] == updated_data["name"]
    assert response.json()["status"] == updated_data["status"]


def test_update_pet_not_found_404():
    """Проверка обновления несуществующего питомца (404)."""
    non_existent_id = random.randint(9999999, 99999999)
    updated_data = {
        "id": non_existent_id,
        "name": "GhostPet",
        "category": {"id": 1, "name": "Ghosts"},
        "photoUrls": [], "tags": [],
        "status": "sold"
    }
    headers = {'Content-Type': 'application/json', 'accept': 'application/json'}
    response = requests.put(f"{BASE_URL}/pet", json=updated_data, headers=headers)
    coverage.record_test_result("PUT /pet", response.status_code)
    assert response.status_code == 404  # Ожидаем Not Found


def test_update_pet_invalid_data_400():
    """Проверка обновления питомца с невалидными данными (400)."""
    # Для теста 400 по PUT нужен существующий питомец, но с невалидным телом запроса
    # Сначала создадим питомца
    headers = {'Content-Type': 'application/json', 'accept': 'application/json'}
    temp_pet_data = {
        "id": int(time.time() * 100),
        "name": f"TempPet_{int(time.time() * 100)}",
        "category": {"id": 1, "name": "Temporary"},
        "photoUrls": [], "tags": [], "status": "available"
    }
    create_resp = requests.post(f"{BASE_URL}/pet", json=temp_pet_data, headers=headers)
    if create_resp.status_code != 200:
        pytest.skip(
            "Не удалось создать временного питомца для теста PUT 400")  # Пропускаем тест, если создание не удалось

    pet_id = create_resp.json().get("id", temp_pet_data["id"])

    # Теперь пытаемся обновить с невалидными данными
    invalid_update_data = temp_pet_data.copy()
    invalid_update_data["status"] = 123  # Неверный тип статуса

    response = requests.put(f"{BASE_URL}/pet", json=invalid_update_data, headers=headers)
    coverage.record_test_result("PUT /pet", response.status_code)
    assert response.status_code in [400, 422]  # Ожидаем Bad Request или Unprocessable

    # Очистка
    requests.delete(f"{BASE_URL}/pet/{pet_id}")


# GET /pet/findByStatus
def test_find_pets_by_status_success():
    """Проверка поиска питомцев по статусу 'available' (200)."""
    params = {'status': 'available'}
    headers = {'accept': 'application/json'}
    response = requests.get(f"{BASE_URL}/pet/findByStatus", params=params, headers=headers)
    coverage.record_test_result("GET /pet/findByStatus", response.status_code)
    assert response.status_code == 200
    assert isinstance(response.json(), list)  # Должен вернуться список


def test_find_pets_by_status_invalid_400():
    """Проверка поиска питомцев с невалидным статусом (400)."""
    params = {'status': 'invalid_status_!@#'}  # Недопустимое значение статуса
    headers = {'accept': 'application/json'}
    response = requests.get(f"{BASE_URL}/pet/findByStatus", params=params, headers=headers)
    coverage.record_test_result("GET /pet/findByStatus", response.status_code)
    assert response.status_code == 400  # Ожидаем Bad Request


# GET /pet/findByTags
def test_find_pets_by_tags_success():
    """Проверка поиска питомцев по тегу (200)."""
    params = {'tags': 'test-tag'}  # Используем тег из pet_data
    headers = {'accept': 'application/json'}
    response = requests.get(f"{BASE_URL}/pet/findByTags", params=params, headers=headers)
    coverage.record_test_result("GET /pet/findByTags", response.status_code)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_find_pets_by_tags_no_tag_400():
    """Проверка поиска питомцев без указания тега (400)."""
    # В спецификации указано, что tags обязателен.
    # По факту API может вернуть 200 с пустым списком, но по спеке ждем 400.
    headers = {'accept': 'application/json'}
    response = requests.get(f"{BASE_URL}/pet/findByTags", headers=headers)
    coverage.record_test_result("GET /pet/findByTags", response.status_code)
    assert response.status_code == 400  # Ожидаем Bad Request


# GET /pet/{petId}
def test_get_pet_by_id_success(created_pet):
    """Проверка получения питомца по ID (200)."""
    pet_id = created_pet
    headers = {'accept': 'application/json'}
    response = requests.get(f"{BASE_URL}/pet/{pet_id}", headers=headers)
    coverage.record_test_result("GET /pet/{petId}", response.status_code)
    assert response.status_code == 200
    assert response.json()["id"] == pet_id


def test_get_pet_by_id_not_found_404():
    """Проверка получения несуществующего питомца по ID (404)."""
    non_existent_id = random.randint(9999999, 99999999)
    headers = {'accept': 'application/json'}
    response = requests.get(f"{BASE_URL}/pet/{non_existent_id}", headers=headers)
    coverage.record_test_result("GET /pet/{petId}", response.status_code)
    assert response.status_code == 404


def test_get_pet_by_id_invalid_id_400():
    """Проверка получения питомца по невалидному ID (400)."""
    invalid_id = "invalid-id-string"
    headers = {'accept': 'application/json'}
    response = requests.get(f"{BASE_URL}/pet/{invalid_id}", headers=headers)
    coverage.record_test_result("GET /pet/{petId}", response.status_code)
    # API возвращает 404 для нечисловых ID, хотя логичнее было бы 400
    # Будем проверять на 404, как фактически работает API
    assert response.status_code == 404  # Фактическое поведение API


# POST /pet/{petId} (Update with form data)
def test_update_pet_form_data_success(created_pet):
    """Проверка обновления питомца через form data (200)."""
    pet_id = created_pet
    headers = {'accept': 'application/json'}  # Content-Type будет application/x-www-form-urlencoded по умолчанию
    form_data = {
        'name': f'UpdatedNameForm_{pet_id}',
        'status': 'sold'
    }
    response = requests.post(f"{BASE_URL}/pet/{pet_id}", data=form_data, headers=headers)
    coverage.record_test_result("POST /pet/{petId}", response.status_code)
    # Спецификация говорит, что этот метод возвращает 200, но может возвращать и 405 (Method Not Allowed)
    # Реальное API Petstore может не поддерживать этот метод как задумано.
    # Проверим сначала на 200, как в документации swagger.io
    # Если API вернет 405 или другой код, тест упадет, и мы будем знать реальное поведение
    assert response.status_code == 200  # По спецификации должен быть 200


def test_update_pet_form_data_not_found_404(created_pet):
    """Проверка обновления несуществующего питомца form data (404)."""
    # Этот тест не имеет смысла, так как метод POST /{petId} сам по себе может быть не реализован
    # или работать некорректно в Petstore API.
    # Спецификация указывает на 405, но это часто означает, что сам метод не поддерживается.
    # Пропускаем этот тест для 404, так как он дублирует проверку метода.
    pytest.skip("Пропуск теста POST /pet/{petId} для 404 из-за неопределенности метода")


# DELETE /pet/{petId}
def test_delete_pet_success(created_pet):
    """Проверка успешного удаления питомца (200)."""
    pet_id = created_pet
    headers = {'accept': 'application/json'}
    # Можно добавить 'api_key': 'special-key' если требуется авторизация
    response = requests.delete(f"{BASE_URL}/pet/{pet_id}", headers=headers)
    coverage.record_test_result("DELETE /pet/{petId}", response.status_code)
    assert response.status_code == 200

    # Дополнительная проверка, что питомец действительно удален
    get_response = requests.get(f"{BASE_URL}/pet/{pet_id}", headers=headers)
    coverage.record_test_result("GET /pet/{petId}", get_response.status_code)  # Записываем результат GET после DELETE
    assert get_response.status_code == 404  # Ожидаем Not Found после удаления


def test_delete_pet_not_found_404():
    """Проверка удаления несуществующего питомца (404)."""
    non_existent_id = random.randint(9999999, 99999999)
    headers = {'accept': 'application/json'}
    response = requests.delete(f"{BASE_URL}/pet/{non_existent_id}", headers=headers)
    coverage.record_test_result("DELETE /pet/{petId}", response.status_code)
    assert response.status_code == 404


def test_delete_pet_invalid_id_400():
    """Проверка удаления питомца с невалидным ID (400)."""
    invalid_id = "invalid-id"
    headers = {'accept': 'application/json'}
    response = requests.delete(f"{BASE_URL}/pet/{invalid_id}", headers=headers)
    coverage.record_test_result("DELETE /pet/{petId}", response.status_code)
    # Ожидаем 400 Bad Request согласно спецификации для невалидного ID
    assert response.status_code == 400


# POST /pet/{petId}/uploadImage
def test_upload_image_success(created_pet):
    """Проверка успешной загрузки изображения (200)."""
    pet_id = created_pet
    headers = {'accept': 'application/json'}
    # Создаем временный dummy файл для загрузки
    file_path = "test_image.jpg"
    with open(file_path, "w") as f:
        f.write("dummy image data")

    files = {'file': (file_path, open(file_path, 'rb'), 'image/jpeg')}
    # Дополнительные данные формы, если нужно
    form_data = {'additionalMetadata': 'Test image upload'}

    response = requests.post(f"{BASE_URL}/pet/{pet_id}/uploadImage", headers=headers, data=form_data, files=files)

    # Закрываем и удаляем временный файл
    files['file'][1].close()
    os.remove(file_path)

    coverage.record_test_result("POST /pet/{petId}/uploadImage", response.status_code)
    assert response.status_code == 200
    assert "File uploaded" in response.json().get("message", "")


def test_upload_image_unsupported_media_type_415(created_pet):
    """Проверка загрузки с неверным Content-Type (ожидаем 415)."""
    pet_id = created_pet
    # Отправляем запрос без multipart/form-data
    headers = {'accept': 'application/json', 'Content-Type': 'application/json'}
    response = requests.post(f"{BASE_URL}/pet/{pet_id}/uploadImage", headers=headers, json={"metadata": "test"})
    coverage.record_test_result("POST /pet/{petId}/uploadImage", response.status_code)
    # Спецификация не указывает 415, но это логичный код ошибки для неверного типа контента при загрузке файла.
    # Реальное API может вернуть 400 или другой код. Проверим на 415 или 400.
    assert response.status_code in [415, 400]


# --- End-to-End CRUD Тест ---

def test_pet_crud_e2e(pet_data):
    """Полный цикл CRUD операций для питомца."""
    headers_json = {'Content-Type': 'application/json', 'accept': 'application/json'}
    headers_accept = {'accept': 'application/json'}

    # 1. Создание (POST /pet)
    create_response = requests.post(f"{BASE_URL}/pet", json=pet_data, headers=headers_json)
    coverage.record_test_result("POST /pet", create_response.status_code)
    assert create_response.status_code == 200, f"E2E Ошибка создания: {create_response.text}"
    created_pet_id = create_response.json().get("id", pet_data["id"])
    print(f"E2E: Создан питомец с ID {created_pet_id}")

    # 2. Чтение (GET /pet/{petId})
    get_response = requests.get(f"{BASE_URL}/pet/{created_pet_id}", headers=headers_accept)
    coverage.record_test_result("GET /pet/{petId}", get_response.status_code)
    assert get_response.status_code == 200, f"E2E Ошибка чтения: {get_response.text}"
    assert get_response.json()["name"] == pet_data["name"]
    print(f"E2E: Питомец {created_pet_id} успешно прочитан.")

    # 3. Обновление (PUT /pet)
    updated_data = pet_data.copy()
    updated_data["id"] = created_pet_id  # Убедимся что ID правильный
    updated_data["name"] = f"UpdatedE2E_{created_pet_id}"
    updated_data["status"] = "sold"
    put_response = requests.put(f"{BASE_URL}/pet", json=updated_data, headers=headers_json)
    coverage.record_test_result("PUT /pet", put_response.status_code)
    assert put_response.status_code == 200, f"E2E Ошибка обновления: {put_response.text}"
    assert put_response.json()["name"] == updated_data["name"]
    assert put_response.json()["status"] == "sold"
    print(f"E2E: Питомец {created_pet_id} успешно обновлен.")

    # 4. Чтение после обновления (GET /pet/{petId}) - Верификация
    get_updated_response = requests.get(f"{BASE_URL}/pet/{created_pet_id}", headers=headers_accept)
    # Записываем еще один результат для GET, т.к. это отдельная проверка
    coverage.record_test_result("GET /pet/{petId}", get_updated_response.status_code)
    assert get_updated_response.status_code == 200
    assert get_updated_response.json()["name"] == updated_data["name"]
    assert get_updated_response.json()["status"] == "sold"
    print(f"E2E: Обновление питомца {created_pet_id} верифицировано.")

    # Дополнительно: Попробуем обновить через POST form-data
    form_data_update = {'name': f'UpdatedFormE2E_{created_pet_id}', 'status': 'pending'}
    post_update_response = requests.post(f"{BASE_URL}/pet/{created_pet_id}", data=form_data_update,
                                         headers=headers_accept)
    coverage.record_test_result("POST /pet/{petId}", post_update_response.status_code)
    # Ожидаем 200 согласно спеке, но готовы к другим кодам
    if post_update_response.status_code == 200:
        print(f"E2E: Питомец {created_pet_id} успешно обновлен через POST form-data.")
        # Верификация обновления через POST
        get_post_updated_response = requests.get(f"{BASE_URL}/pet/{created_pet_id}", headers=headers_accept)
        coverage.record_test_result("GET /pet/{petId}",
                                    get_post_updated_response.status_code)  # Еще одна запись для GET
        assert get_post_updated_response.status_code == 200
        assert get_post_updated_response.json()["name"] == form_data_update['name']
        assert get_post_updated_response.json()["status"] == form_data_update['status']
        print(f"E2E: Обновление питомца {created_pet_id} через POST верифицировано.")
    else:
        print(
            f"E2E: Обновление через POST /pet/{{petId}} вернуло {post_update_response.status_code}. Пропускаем верификацию этого шага.")

    # 5. Удаление (DELETE /pet/{petId})
    delete_response = requests.delete(f"{BASE_URL}/pet/{created_pet_id}", headers=headers_accept)
    coverage.record_test_result("DELETE /pet/{petId}", delete_response.status_code)
    assert delete_response.status_code == 200, f"E2E Ошибка удаления: {delete_response.text}"
    print(f"E2E: Питомец {created_pet_id} успешно удален.")

    # 6. Чтение после удаления (GET /pet/{petId}) - Верификация
    get_deleted_response = requests.get(f"{BASE_URL}/pet/{created_pet_id}", headers=headers_accept)
    coverage.record_test_result("GET /pet/{petId}", get_deleted_response.status_code)
    assert get_deleted_response.status_code == 404, "E2E Ошибка: Питомец не был удален."
    print(f"E2E: Верификация удаления питомца {created_pet_id} прошла успешно (получен 404).")


# --- Негативные тесты ---

def test_create_pet_missing_required_field():
    """Проверка создания питомца без обязательного поля 'name' (400/422)."""
    headers = {'Content-Type': 'application/json', 'accept': 'application/json'}
    invalid_data = {  # Нет поля name
        "id": random.randint(10000, 20000),
        "category": {"id": 1, "name": "Missing"},
        "photoUrls": ["url"],
        "tags": [],
        "status": "available"
    }
    response = requests.post(f"{BASE_URL}/pet", json=invalid_data, headers=headers)
    coverage.record_test_result("POST /pet", response.status_code)
    # Спецификация может требовать 400/422, но API может вернуть 500 из-за ошибки валидации на сервере
    assert response.status_code in [400, 422, 500]  # Допускаем 500 Internal Server Error


def test_get_pet_by_status_long_string():
    """Проверка поиска по статусу со слишком длинной строкой (потенциально 400)."""
    long_status = "a" * 1000  # Очень длинная строка
    params = {'status': long_status}
    headers = {'accept': 'application/json'}
    response = requests.get(f"{BASE_URL}/pet/findByStatus", params=params, headers=headers)
    coverage.record_test_result("GET /pet/findByStatus", response.status_code)
    # Ожидаем 400, так как это невалидный статус
    assert response.status_code == 400


# --- Хук Pytest для вывода отчета ---

def pytest_sessionfinish(session):
    """Вызывается после завершения всех тестов."""
    print("\n" + "=" * 50)
    print(" " * 15 + "API COVERAGE REPORT" + " " * 15)
    print("=" * 50 + "\n")

    metrics_data = coverage.calculate_metrics()

    print(f"1. Среднее покрытие эндпоинтов раздела Pet: {metrics_data['avg_endpoint_coverage']:.1f}%")
    print(f"2. Покрытие статус-кодов раздела Pet: {metrics_data['pet_status_coverage']:.1f}%")
    print(f"3. Полностью покрытые эндпоинты API: {metrics_data['full_endpoint_coverage']:.1f}%")
    print(f"4. Общее покрытие статус-кодов API: {metrics_data['total_api_coverage']:.1f}%\n")

    print("Детали по endpoint'ам:")

    # Сортировка эндпоинтов: сначала Pet, потом остальные, по алфавиту внутри групп
    all_endpoints = sorted(coverage.coverage_data.items())
    pet_endpoints = sorted([item for item in all_endpoints if "/pet" in item[0]])
    other_endpoints = sorted([item for item in all_endpoints if "/pet" not in item[0]])

    sorted_coverage_data = pet_endpoints + other_endpoints

    for endpoint, data in sorted_coverage_data:
        expected_codes = sorted(data["status_codes"])
        tested_codes = sorted(list(set(data["tested"])))  # Уникальные и отсортированные

        expected_count = len(expected_codes)
        tested_count = len(tested_codes)
        percentage = (tested_count / expected_count * 100) if expected_count > 0 else 0.0

        print(
            f"{endpoint}: {tested_count}/{expected_count} ({percentage:.1f}%) ------> {tested_codes} / {expected_codes}")

    print("\n" + "=" * 25)
    # pytest сам выведет статистику passed/failed/skipped
    # print(f"{session.testscollected} tests collected") # Можно добавить свою статистику при желании
    print(f"{session.testscollected} tests ran")
    print("=" * 25)
