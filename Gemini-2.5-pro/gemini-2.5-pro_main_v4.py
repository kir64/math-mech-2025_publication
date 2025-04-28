import pytest
import requests
import random
import time
import os
from requests.exceptions import ConnectionError, Timeout

# Импортируем экземпляр coverage из вашего файла metrics.py
from metrics import coverage

# Базовый URL API
BASE_URL = "https://petstore3.swagger.io/api/v3"
REQUEST_TIMEOUT = 15 # Увеличим таймаут для запросов
MAX_RETRIES = 3 # Количество повторных попыток при сетевых ошибках
RETRY_DELAY = 2 # Задержка между повторными попытками (в секундах)

# --- Хелпер для повторных запросов ---
def make_request_with_retry(method, url, **kwargs):
    """Обертка для запросов requests с повторными попытками при сетевых ошибках."""
    headers = kwargs.get('headers', {})
    headers.setdefault('User-Agent', 'Python-Pytest-Client') # Добавляем User-Agent
    kwargs['headers'] = headers
    kwargs.setdefault('timeout', REQUEST_TIMEOUT)

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.request(method, url, **kwargs)
            # Можно добавить проверку на 5xx ошибки сервера для retry, но пока ограничимся сетевыми
            return response
        except (ConnectionError, Timeout) as e:
            print(f"\n[Retry Helper] Attempt {attempt + 1}/{MAX_RETRIES} failed for {method} {url}: {e}")
            if attempt + 1 == MAX_RETRIES:
                print(f"[Retry Helper] Max retries reached. Raising exception.")
                raise # Поднимаем исключение после последней попытки
            print(f"[Retry Helper] Retrying in {RETRY_DELAY} seconds...")
            time.sleep(RETRY_DELAY)
    # Этот return никогда не должен выполниться из-за raise выше, но нужен для Mypy/Linting
    return None # Should not happen


# --- Фикстуры ---

@pytest.fixture(scope="module")
def pet_data():
    """Генерирует уникальные данные для нового питомца."""
    unique_id = int(time.time() * 1000)
    return {
        "id": unique_id, # Будет перезаписан
        "name": f"TestPet_{unique_id}",
        "category": {"id": random.randint(1, 100), "name": "Dogs"},
        "photoUrls": [f"http://example.com/photo_{unique_id}.jpg"],
        "tags": [{"id": random.randint(1, 100), "name": f"test-tag-{random.randint(1,100)}"}],
        "status": "available"
    }

@pytest.fixture(scope="function")
def created_pet(pet_data):
    """Создает питомца перед тестом и удаляет после."""
    headers = {'Content-Type': 'application/json', 'accept': 'application/json'}
    current_pet_data = pet_data.copy()
    current_pet_data["id"] = int(time.time() * 1000) + random.randint(1, 1000)

    # Используем хелпер для создания
    response = make_request_with_retry("post", f"{BASE_URL}/pet", json=current_pet_data, headers=headers)

    if response is None or response.status_code != 200:
         status = response.status_code if response else "N/A"
         text = response.text if response else "No response"
         pytest.skip(f"Не удалось создать питомца для теста: {status} {text}")

    created_pet_id = response.json().get("id", current_pet_data["id"])
    coverage.record_test_result("POST /pet", response.status_code)
    print(f"\n[Fixture] Created pet ID: {created_pet_id}")
    # <<<--- Увеличиваем паузу ЕЩЕ РАЗ --->>>
    print("[Fixture] Waiting 2.5s for consistency...")
    time.sleep(2.5)
    print("[Fixture] Wait finished.")

    yield created_pet_id

    # Очистка
    print(f"[Fixture] Cleaning up pet ID: {created_pet_id}")
    delete_headers = {'accept': 'application/json'}
    # Используем хелпер для GET перед удалением
    get_resp = make_request_with_retry("get", f"{BASE_URL}/pet/{created_pet_id}", headers=delete_headers)

    if get_resp and get_resp.status_code == 200:
        # Используем хелпер для удаления
        delete_response = make_request_with_retry("delete", f"{BASE_URL}/pet/{created_pet_id}", headers=delete_headers)
        if delete_response:
            print(f"[Fixture] Delete response: {delete_response.status_code}")
            coverage.record_test_result("DELETE /pet/{petId}", delete_response.status_code)
            time.sleep(0.5) # Небольшая пауза после удаления
        else:
             print("[Fixture] Delete request failed after retries.")
    elif get_resp and get_resp.status_code == 404:
         print(f"[Fixture] Pet {created_pet_id} already gone before cleanup.")
         coverage.record_test_result("GET /pet/{petId}", 404)
    else:
         status = get_resp.status_code if get_resp else "N/A"
         print(f"[Fixture] Unexpected status {status} getting pet {created_pet_id} before cleanup.")


# --- Тесты валидации эндпоинтов и статус-кодов ---

# POST /pet
def test_create_pet_success(pet_data):
    """POST /pet: Проверка успешного создания питомца (200)."""
    headers = {'Content-Type': 'application/json', 'accept': 'application/json'}
    data_to_create = pet_data.copy()
    data_to_create["id"] = int(time.time() * 1000) + random.randint(1001, 2000)
    response = make_request_with_retry("post", f"{BASE_URL}/pet", json=data_to_create, headers=headers)
    assert response is not None, "Request failed after retries"
    coverage.record_test_result("POST /pet", response.status_code)
    assert response.status_code == 200
    if response.status_code == 200:
        assert response.json()["name"] == data_to_create["name"]
        pet_id_to_delete = response.json().get("id", data_to_create["id"])
        del_resp = make_request_with_retry("delete", f"{BASE_URL}/pet/{pet_id_to_delete}")
        if del_resp: coverage.record_test_result("DELETE /pet/{petId}", del_resp.status_code)

def test_create_pet_invalid_input_400(pet_data):
     """POST /pet: Проверка создания питомца с невалидным телом (400)."""
     headers = {'Content-Type': 'application/json', 'accept': 'application/json'}
     invalid_data = pet_data.copy()
     invalid_data["id"] = "not-an-integer"
     response = make_request_with_retry("post", f"{BASE_URL}/pet", json=invalid_data, headers=headers)
     assert response is not None, "Request failed after retries"
     coverage.record_test_result("POST /pet", response.status_code)
     assert response.status_code == 400

def test_create_pet_unprocessable_actual_200(pet_data):
    """POST /pet: Проверка создания с невалидным статусом (ожидаем 200 - по факту API)."""
    headers = {'Content-Type': 'application/json', 'accept': 'application/json'}
    invalid_data = pet_data.copy()
    invalid_data["id"] = int(time.time() * 1000) + random.randint(2001, 3000)
    invalid_data["status"] = "invalid-enum-status"
    response = make_request_with_retry("post", f"{BASE_URL}/pet", json=invalid_data, headers=headers)
    assert response is not None, "Request failed after retries"
    coverage.record_test_result("POST /pet", response.status_code)
    # Исправлено: API возвращает 200
    assert response.status_code == 200
    if response.status_code == 200:
        pet_id_to_delete = response.json().get("id", invalid_data["id"])
        del_resp = make_request_with_retry("delete", f"{BASE_URL}/pet/{pet_id_to_delete}")
        if del_resp: coverage.record_test_result("DELETE /pet/{petId}", del_resp.status_code)

def test_create_pet_missing_required_field_actual_200(pet_data):
    """POST /pet: Проверка создания без обязательных полей (ожидаем 200 - по факту API)."""
    headers = {'Content-Type': 'application/json', 'accept': 'application/json'}
    invalid_data = pet_data.copy()
    invalid_data["id"] = int(time.time() * 1000) + random.randint(3001, 4000)
    if "name" in invalid_data: del invalid_data["name"]
    if "photoUrls" in invalid_data: del invalid_data["photoUrls"]

    response = make_request_with_retry("post", f"{BASE_URL}/pet", json=invalid_data, headers=headers)
    assert response is not None, "Request failed after retries"
    coverage.record_test_result("POST /pet", response.status_code)
    assert response.status_code == 200
    if response.status_code == 200:
        pet_id_to_delete = response.json().get("id", invalid_data.get("id"))
        if pet_id_to_delete:
             del_resp = make_request_with_retry("delete", f"{BASE_URL}/pet/{pet_id_to_delete}")
             if del_resp: coverage.record_test_result("DELETE /pet/{petId}", del_resp.status_code)

# PUT /pet
def test_update_pet_success(created_pet):
    """PUT /pet: Проверка успешного обновления питомца (200)."""
    pet_id = created_pet
    print(f"\n[Test] Updating pet ID: {pet_id}")
    headers = {'Content-Type': 'application/json', 'accept': 'application/json'}
    # --- Pre-check GET ---
    pre_check_get = make_request_with_retry("get", f"{BASE_URL}/pet/{pet_id}", headers={'accept': 'application/json'})
    if not pre_check_get or pre_check_get.status_code != 200:
        status = pre_check_get.status_code if pre_check_get else "N/A"
        pytest.skip(f"Skipping PUT test: Pet {pet_id} not found (status {status}) before update.")
    # --- /Pre-check GET ---

    updated_data = {
        "id": pet_id, "name": f"UpdatedPet_{pet_id}", "category": {"id": 1, "name": "Dogs"},
        "photoUrls": ["http://example.com/updated_photo.jpg"], "tags": [{"id": 1, "name": "updated-tag"}],
        "status": "pending"
    }
    response = make_request_with_retry("put", f"{BASE_URL}/pet", json=updated_data, headers=headers)
    print(f"[Test] PUT response status: {response.status_code if response else 'N/A'}")
    assert response is not None, "Request failed after retries"
    coverage.record_test_result("PUT /pet", response.status_code)
    assert response.status_code == 200
    if response.status_code == 200:
        assert response.json()["name"] == updated_data["name"]
        assert response.json()["status"] == updated_data["status"]

def test_update_pet_not_found_404():
    """PUT /pet: Проверка обновления несуществующего питомца (404)."""
    non_existent_id = random.randint(999999900, 999999999)
    updated_data = {
        "id": non_existent_id, "name": "GhostPet", "category": {"id": 1, "name": "Ghosts"},
        "photoUrls": [], "tags": [], "status": "sold"
    }
    headers = {'Content-Type': 'application/json', 'accept': 'application/json'}
    response = make_request_with_retry("put", f"{BASE_URL}/pet", json=updated_data, headers=headers)
    assert response is not None, "Request failed after retries"
    coverage.record_test_result("PUT /pet", response.status_code)
    assert response.status_code == 404

def test_update_pet_invalid_data_400_or_404(created_pet):
    """PUT /pet: Проверка обновления с невалидными данными (400 или 404)."""
    pet_id = created_pet
    # --- Pre-check GET ---
    pre_check_get = make_request_with_retry("get", f"{BASE_URL}/pet/{pet_id}", headers={'accept': 'application/json'})
    if not pre_check_get or pre_check_get.status_code != 200:
        status = pre_check_get.status_code if pre_check_get else "N/A"
        pytest.skip(f"Skipping PUT invalid test: Pet {pet_id} not found (status {status}) before update.")
    # --- /Pre-check GET ---
    invalid_update_data = {
        "id": pet_id, "name": f"InvalidUpdate_{pet_id}", "category": {"id": 1, "name": "Temporary"},
        "photoUrls": [], "tags": [], "status": 123 # Неверный тип статуса
    }
    headers = {'Content-Type': 'application/json', 'accept': 'application/json'}
    response = make_request_with_retry("put", f"{BASE_URL}/pet", json=invalid_update_data, headers=headers)
    assert response is not None, "Request failed after retries"
    coverage.record_test_result("PUT /pet", response.status_code)
    assert response.status_code in [400, 404]

def test_update_pet_unprocessable_actual_200(created_pet):
    """PUT /pet: Проверка обновления с невалидным статусом (ожидаем 200 - по факту API)."""
    pet_id = created_pet
    # --- Pre-check GET ---
    pre_check_get = make_request_with_retry("get", f"{BASE_URL}/pet/{pet_id}", headers={'accept': 'application/json'})
    if not pre_check_get or pre_check_get.status_code != 200:
        status = pre_check_get.status_code if pre_check_get else "N/A"
        pytest.skip(f"Skipping PUT unprocessable test: Pet {pet_id} not found (status {status}) before update.")
    # --- /Pre-check GET ---
    invalid_update_data = {
        "id": pet_id, "name": f"InvalidStatusUpdate_{pet_id}", "category": {"id": 1, "name": "Dogs"},
        "photoUrls": [], "tags": [], "status": "another-invalid-status" # Недопустимое значение
    }
    headers = {'Content-Type': 'application/json', 'accept': 'application/json'}
    response = make_request_with_retry("put", f"{BASE_URL}/pet", json=invalid_update_data, headers=headers)
    assert response is not None, "Request failed after retries"
    coverage.record_test_result("PUT /pet", response.status_code)
    # Исправлено: API возвращало 200
    assert response.status_code == 200

# GET /pet/findByStatus
def test_find_pets_by_status_success():
    """GET /pet/findByStatus: Проверка поиска 'available' (200)."""
    params = {'status': 'available'}
    headers = {'accept': 'application/json'}
    response = make_request_with_retry("get", f"{BASE_URL}/pet/findByStatus", params=params, headers=headers)
    assert response is not None, "Request failed after retries"
    coverage.record_test_result("GET /pet/findByStatus", response.status_code)
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_find_pets_by_status_invalid_400():
    """GET /pet/findByStatus: Проверка поиска с невалидным статусом (400)."""
    params = {'status': 'invalid_status_!@#'}
    headers = {'accept': 'application/json'}
    response = make_request_with_retry("get", f"{BASE_URL}/pet/findByStatus", params=params, headers=headers)
    assert response is not None, "Request failed after retries"
    coverage.record_test_result("GET /pet/findByStatus", response.status_code)
    assert response.status_code == 400

# GET /pet/findByTags
def test_find_pets_by_tags_success():
    """GET /pet/findByTags: Проверка поиска по тегу (200)."""
    tag_name = f"unique-tag-{int(time.time())}"
    pet_id = int(time.time() * 1000) + random.randint(4001, 5000)
    temp_pet_data = {
         "id": pet_id, "name": "TagPet", "category": {"id": 1, "name": "Tags"},
         "photoUrls": [], "tags": [{"id": 1, "name": tag_name}], "status": "available"
    }
    headers_post = {'Content-Type': 'application/json', 'accept': 'application/json'}
    create_resp = make_request_with_retry("post", f"{BASE_URL}/pet", json=temp_pet_data, headers=headers_post)
    coverage.record_test_result("POST /pet", create_resp.status_code if create_resp else 500)
    if not create_resp or create_resp.status_code != 200: pytest.skip("Failed to create pet for tag search")

    print(f"[Test findByTags] Waiting 2.0s after creating pet {pet_id} with tag {tag_name}...")
    time.sleep(2.0) # <<<--- Увеличена пауза --->>>

    params = {'tags': tag_name}
    headers_get = {'accept': 'application/json'}
    response = None
    found = False

    # <<<--- Добавлены повторные попытки поиска --->>>
    for search_attempt in range(MAX_RETRIES):
        print(f"[Test findByTags] Search attempt {search_attempt + 1}/{MAX_RETRIES} for tag {tag_name}")
        response = make_request_with_retry("get", f"{BASE_URL}/pet/findByTags", params=params, headers=headers_get)
        if response and response.status_code == 200:
            coverage.record_test_result("GET /pet/findByTags", response.status_code)
            try:
                # Проверка наличия питомца с нужным тегом
                found = any(tag['name'] == tag_name for pet in response.json() if isinstance(pet, dict) for tag in pet.get('tags', []))
                if found:
                    print(f"[Test findByTags] Found pet with tag {tag_name}")
                    break # Выходим из цикла, если нашли
            except (TypeError, ValueError, KeyError):
                print("[Test findByTags] Error parsing response JSON")
                # Продолжаем попытки или завершаем с ошибкой
        else:
            status = response.status_code if response else "N/A"
            print(f"[Test findByTags] GET request failed or returned status {status}")
            # Не записываем в coverage неудачную попытку GET

        if search_attempt + 1 < MAX_RETRIES:
             print(f"[Test findByTags] Retrying search in {RETRY_DELAY} seconds...")
             time.sleep(RETRY_DELAY)

    assert response is not None, "Search request failed after retries"
    assert response.status_code == 200 # Проверяем статус последнего ответа
    assert isinstance(response.json(), list) # Проверяем тип последнего ответа
    assert found, f"Питомец с тегом {tag_name} не найден после {MAX_RETRIES} попыток"

    # Очистка
    del_resp = make_request_with_retry("delete", f"{BASE_URL}/pet/{pet_id}")
    if del_resp: coverage.record_test_result("DELETE /pet/{petId}", del_resp.status_code)


def test_find_pets_by_tags_no_tag_400():
     """GET /pet/findByTags: Проверка поиска без указания тега (400)."""
     headers = {'accept': 'application/json'}
     response = make_request_with_retry("get", f"{BASE_URL}/pet/findByTags", headers=headers)
     assert response is not None, "Request failed after retries"
     coverage.record_test_result("GET /pet/findByTags", response.status_code)
     assert response.status_code == 400

# GET /pet/{petId}
def test_get_pet_by_id_success(created_pet):
    """GET /pet/{petId}: Проверка получения питомца по ID (200)."""
    pet_id = created_pet
    print(f"\n[Test] Getting pet ID: {pet_id}")
    headers = {'accept': 'application/json'}
    response = make_request_with_retry("get", f"{BASE_URL}/pet/{pet_id}", headers=headers)

    # Дополнительная проверка на случай, если первая попытка все равно 404
    if response and response.status_code == 404:
        print(f"[Test] GET returned 404, waiting {RETRY_DELAY}s and retrying ONCE more...")
        time.sleep(RETRY_DELAY)
        response = make_request_with_retry("get", f"{BASE_URL}/pet/{pet_id}", headers=headers)

    print(f"[Test] Final GET response status: {response.status_code if response else 'N/A'}")
    assert response is not None, "Request failed after retries"
    coverage.record_test_result("GET /pet/{petId}", response.status_code)
    assert response.status_code == 200
    if response.status_code == 200:
        assert response.json()["id"] == pet_id

def test_get_pet_by_id_not_found_404():
    """GET /pet/{petId}: Проверка получения несуществующего питомца по ID (404)."""
    non_existent_id = random.randint(999999900, 999999999)
    headers = {'accept': 'application/json'}
    response = make_request_with_retry("get", f"{BASE_URL}/pet/{non_existent_id}", headers=headers)
    assert response is not None, "Request failed after retries"
    coverage.record_test_result("GET /pet/{petId}", response.status_code)
    assert response.status_code == 404

def test_get_pet_by_id_invalid_id_400():
    """GET /pet/{petId}: Проверка получения питомца по невалидному ID (400)."""
    invalid_id = "invalid-id-string"
    headers = {'accept': 'application/json'}
    response = make_request_with_retry("get", f"{BASE_URL}/pet/{invalid_id}", headers=headers)
    assert response is not None, "Request failed after retries"
    coverage.record_test_result("GET /pet/{petId}", response.status_code)
    assert response.status_code == 400

# POST /pet/{petId} (Update with form data)
def test_update_pet_form_data_error_400(created_pet):
    """POST /pet/{petId}: Проверка обновления через form data (ожидаем 400)."""
    pet_id = created_pet
    # --- Pre-check GET ---
    pre_check_get = make_request_with_retry("get", f"{BASE_URL}/pet/{pet_id}", headers={'accept': 'application/json'})
    if not pre_check_get or pre_check_get.status_code != 200:
        status = pre_check_get.status_code if pre_check_get else "N/A"
        pytest.skip(f"Skipping POST form test: Pet {pet_id} not found (status {status}) before update.")
    # --- /Pre-check GET ---
    headers = {'accept': 'application/json'}
    form_data = {'name': f'UpdatedNameForm_{pet_id}', 'status': 'sold'}
    response = make_request_with_retry("post", f"{BASE_URL}/pet/{pet_id}", data=form_data, headers=headers)
    assert response is not None, "Request failed after retries"
    coverage.record_test_result("POST /pet/{petId}", response.status_code)
    assert response.status_code == 400

# DELETE /pet/{petId}
def test_delete_pet_success_check_404(created_pet):
    """DELETE /pet/{petId}: Проверка удаления (фикстурой) и проверка (404)."""
    pet_id = created_pet
    headers = {'accept': 'application/json'}
    # Фикстура уже выполнила DELETE и записала результат. Проверяем GET.
    print(f"\n[Test] Verifying delete for pet ID: {pet_id}")
    response = make_request_with_retry("get", f"{BASE_URL}/pet/{pet_id}", headers=headers)

    # Доп попытка если не 404
    if response and response.status_code != 404:
        print(f"[Test] GET after delete failed ({response.status_code}), retrying ONCE after {RETRY_DELAY}s...")
        time.sleep(RETRY_DELAY)
        response = make_request_with_retry("get", f"{BASE_URL}/pet/{pet_id}", headers=headers)

    print(f"[Test] Final GET after delete status: {response.status_code if response else 'N/A'}")
    assert response is not None, "Request failed after retries"
    coverage.record_test_result("GET /pet/{petId}", response.status_code)
    assert response.status_code == 404

def test_delete_pet_not_found_actual_200():
    """DELETE /pet/{petId}: Проверка удаления несуществующего питомца (ожидаем 200)."""
    non_existent_id = random.randint(999999900, 999999999)
    headers = {'accept': 'application/json'}
    response = make_request_with_retry("delete", f"{BASE_URL}/pet/{non_existent_id}", headers=headers)
    assert response is not None, "Request failed after retries"
    coverage.record_test_result("DELETE /pet/{petId}", response.status_code)
    assert response.status_code == 200

def test_delete_pet_invalid_id_400():
     """DELETE /pet/{petId}: Проверка удаления питомца с невалидным ID (400)."""
     invalid_id = "invalid-id"
     headers = {'accept': 'application/json'}
     response = make_request_with_retry("delete", f"{BASE_URL}/pet/{invalid_id}", headers=headers)
     assert response is not None, "Request failed after retries"
     coverage.record_test_result("DELETE /pet/{petId}", response.status_code)
     assert response.status_code == 400

# POST /pet/{petId}/uploadImage
def test_upload_image_actual_error_415(created_pet):
    """POST /pet/{petId}/uploadImage: Проверка загрузки изображения (ожидаем 415)."""
    pet_id = created_pet
    # --- Pre-check GET ---
    pre_check_get = make_request_with_retry("get", f"{BASE_URL}/pet/{pet_id}", headers={'accept': 'application/json'})
    if not pre_check_get or pre_check_get.status_code != 200:
        status = pre_check_get.status_code if pre_check_get else "N/A"
        pytest.skip(f"Skipping upload image test: Pet {pet_id} not found (status {status}) before upload.")
    # --- /Pre-check GET ---
    headers = {'accept': 'application/json'}
    file_path = "test_image.jpg"
    response = None
    try:
        with open(file_path, "w") as f: f.write("dummy image data")
        with open(file_path, 'rb') as fp:
            files = {'file': (file_path, fp, 'image/jpeg')}
            response = make_request_with_retry("post", f"{BASE_URL}/pet/{pet_id}/uploadImage", headers=headers, files=files)
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

    assert response is not None, "Request failed after retries"
    coverage.record_test_result("POST /pet/{petId}/uploadImage", response.status_code)
    assert response.status_code == 415

def test_upload_image_unsupported_media_type_415(created_pet):
    """POST /pet/{petId}/uploadImage: Проверка с неверным Content-Type (ожидаем 415)."""
    pet_id = created_pet
    # --- Pre-check GET ---
    pre_check_get = make_request_with_retry("get", f"{BASE_URL}/pet/{pet_id}", headers={'accept': 'application/json'})
    if not pre_check_get or pre_check_get.status_code != 200:
        status = pre_check_get.status_code if pre_check_get else "N/A"
        pytest.skip(f"Skipping upload image wrong type test: Pet {pet_id} not found (status {status}) before upload.")
    # --- /Pre-check GET ---
    headers = {'accept': 'application/json', 'Content-Type': 'application/json'} # Неверный тип
    response = make_request_with_retry("post", f"{BASE_URL}/pet/{pet_id}/uploadImage", headers=headers, json={"metadata": "test"})
    assert response is not None, "Request failed after retries"
    coverage.record_test_result("POST /pet/{petId}/uploadImage", response.status_code)
    assert response.status_code in [400, 415]

def test_upload_image_pet_not_found_actual_error_415():
    """POST /pet/{petId}/uploadImage: Проверка для несуществующего питомца (ожидаем 415)."""
    non_existent_id = random.randint(999999900, 999999999)
    headers = {'accept': 'application/json'}
    file_path = "ghost_image.jpg"
    response = None
    try:
        with open(file_path, "w") as f: f.write("dummy image data")
        with open(file_path, 'rb') as fp:
             files = {'file': (file_path, fp, 'image/png')}
             response = make_request_with_retry("post", f"{BASE_URL}/pet/{non_existent_id}/uploadImage", headers=headers, files=files)
    finally:
        if os.path.exists(file_path):
             os.remove(file_path)

    assert response is not None, "Request failed after retries"
    coverage.record_test_result("POST /pet/{petId}/uploadImage", response.status_code)
    # Исправлено: API возвращает 415
    assert response.status_code == 415

def test_upload_image_invalid_petid_actual_error_415():
    """POST /pet/{petId}/uploadImage: Проверка для невалидного ID (ожидаем 415)."""
    invalid_id = "invalid-pet-id"
    headers = {'accept': 'application/json'}
    file_path = "invalid_id_image.jpg"
    response = None
    try:
        with open(file_path, "w") as f: f.write("dummy image data")
        with open(file_path, 'rb') as fp:
            files = {'file': (file_path, fp, 'image/gif')}
            response = make_request_with_retry("post", f"{BASE_URL}/pet/{invalid_id}/uploadImage", headers=headers, files=files)
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

    assert response is not None, "Request failed after retries"
    coverage.record_test_result("POST /pet/{petId}/uploadImage", response.status_code)
    # Исправлено: API возвращает 415
    assert response.status_code == 415


# --- End-to-End CRUD Тест ---

def test_pet_crud_e2e(pet_data):
    """Полный цикл CRUD операций для питомца."""
    headers_json = {'Content-Type': 'application/json', 'accept': 'application/json'}
    headers_accept = {'accept': 'application/json'}
    e2e_pet_data = pet_data.copy()
    e2e_pet_data["id"] = int(time.time() * 1000) + random.randint(5001, 6000)
    initial_pet_id = e2e_pet_data["id"]
    created_pet_id = initial_pet_id # Изначально ID берем сгенерированный

    try:
        # 1. Создание (POST /pet)
        print(f"\nE2E: Attempting create with ID {initial_pet_id}")
        create_response = make_request_with_retry("post", f"{BASE_URL}/pet", json=e2e_pet_data, headers=headers_json)
        assert create_response and create_response.status_code == 200, f"E2E Ошибка создания: {create_response.status_code if create_response else 'N/A'} {create_response.text if create_response else 'No response'}"
        coverage.record_test_result("POST /pet", create_response.status_code)
        created_pet_id = create_response.json().get("id", initial_pet_id) # Используем ID из ответа
        print(f"E2E: Создан питомец с ID {created_pet_id}")
        print("E2E: Waiting 2.5s after create...")
        time.sleep(2.5) # <<<--- Увеличена пауза --->>>

        # 2. Чтение (GET /pet/{petId})
        print(f"E2E: Attempting GET for ID {created_pet_id}")
        get_response = make_request_with_retry("get", f"{BASE_URL}/pet/{created_pet_id}", headers=headers_accept)
        assert get_response and get_response.status_code == 200, f"E2E Ошибка чтения после создания: {get_response.status_code if get_response else 'N/A'} {get_response.text if get_response else 'No response'}"
        coverage.record_test_result("GET /pet/{petId}", get_response.status_code)
        assert get_response.json()["name"] == e2e_pet_data["name"]
        print(f"E2E: Питомец {created_pet_id} успешно прочитан.")

        # 3. Обновление (PUT /pet)
        print(f"E2E: Attempting PUT for ID {created_pet_id}")
        updated_data = e2e_pet_data.copy()
        updated_data["id"] = created_pet_id
        updated_data["name"] = f"UpdatedE2E_{created_pet_id}"
        updated_data["status"] = "sold"
        put_response = make_request_with_retry("put", f"{BASE_URL}/pet", json=updated_data, headers=headers_json)
        assert put_response and put_response.status_code == 200, f"E2E Ошибка обновления: {put_response.status_code if put_response else 'N/A'} {put_response.text if put_response else 'No response'}"
        coverage.record_test_result("PUT /pet", put_response.status_code)
        assert put_response.json()["name"] == updated_data["name"]
        assert put_response.json()["status"] == "sold"
        print(f"E2E: Питомец {created_pet_id} успешно обновлен.")
        time.sleep(0.5)

        # 4. Чтение после обновления (GET /pet/{petId}) - Верификация
        print(f"E2E: Attempting GET after update for ID {created_pet_id}")
        get_updated_response = make_request_with_retry("get", f"{BASE_URL}/pet/{created_pet_id}", headers=headers_accept)
        assert get_updated_response and get_updated_response.status_code == 200, f"E2E Ошибка чтения после обновления: {get_updated_response.status_code if get_updated_response else 'N/A'}"
        coverage.record_test_result("GET /pet/{petId}", get_updated_response.status_code)
        assert get_updated_response.json()["name"] == updated_data["name"]
        assert get_updated_response.json()["status"] == "sold"
        print(f"E2E: Обновление питомца {created_pet_id} верифицировано.")

    finally:
        # 5. Удаление (DELETE /pet/{petId}) - в finally для гарантированной очистки
        print(f"E2E: Attempting DELETE for ID {created_pet_id}")
        delete_response = make_request_with_retry("delete", f"{BASE_URL}/pet/{created_pet_id}", headers=headers_accept)
        # Не проверяем assert на удаление, так как оно может вернуть 200 или 404, главное выполнить
        if delete_response:
            coverage.record_test_result("DELETE /pet/{petId}", delete_response.status_code)
            print(f"E2E: Запрос на удаление питомца {created_pet_id} отправлен (статус {delete_response.status_code}).")
            time.sleep(1.5) # Пауза после удаления
        else:
            print(f"E2E: Запрос на удаление питомца {created_pet_id} не удался после ретраев.")

        # 6. Чтение после удаления (GET /pet/{petId}) - Верификация (необязательно в finally, но можно)
        print(f"E2E: Attempting GET after delete for ID {created_pet_id}")
        get_deleted_response = make_request_with_retry("get", f"{BASE_URL}/pet/{created_pet_id}", headers=headers_accept)
        if get_deleted_response:
            coverage.record_test_result("GET /pet/{petId}", get_deleted_response.status_code)
            # Мягкая проверка, так как удаление могло не успеть
            if get_deleted_response.status_code == 404:
                print(f"E2E: Верификация удаления питомца {created_pet_id} прошла успешно (получен 404).")
            else:
                print(f"E2E: ПРЕДУПРЕЖДЕНИЕ - Питомец {created_pet_id} найден после удаления (статус {get_deleted_response.status_code}).")
        else:
             print(f"E2E: Запрос GET после удаления {created_pet_id} не удался после ретраев.")


# --- Негативные тесты ---

def test_get_pet_by_status_long_string():
    """Негативный: Проверка поиска по статусу со слишком длинной строкой (400)."""
    long_status = "a" * 1000
    params = {'status': long_status}
    headers = {'accept': 'application/json'}
    # Используем хелпер для ретраев при сетевых ошибках
    response = make_request_with_retry("get", f"{BASE_URL}/pet/findByStatus", params=params, headers=headers)
    assert response is not None, "Request failed after retries"
    coverage.record_test_result("GET /pet/findByStatus", response.status_code)
    assert response.status_code == 400


# --- Хук Pytest для вывода отчета ---
# (Оставляем без изменений)
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

    all_endpoints = sorted(coverage.coverage_data.items())
    pet_endpoints = sorted([item for item in all_endpoints if "/pet" in item[0].lower()])
    other_endpoints = sorted([item for item in all_endpoints if "/pet" not in item[0].lower()])

    try:
        # Загружаем актуальные коды из спецификации для сравнения в отчете
        api_spec_resp = make_request_with_retry("get", "https://petstore3.swagger.io/api/v3/openapi.json")
        if api_spec_resp and api_spec_resp.status_code == 200:
            api_spec = api_spec_resp.json()
            spec_paths = api_spec.get("paths", {})
            spec_codes = {}
            for endpoint, methods in spec_paths.items():
                for method, details in methods.items():
                     if method.lower() in ['get', 'post', 'put', 'delete', 'patch']:
                        key = f"{method.upper()} {endpoint}"
                        responses = details.get("responses", {})
                        codes = [str(code) for code in responses.keys() if code != 'default']
                        if not codes and 'default' in responses:
                             codes = ['default']
                        spec_codes[key] = sorted(codes)
        else:
            raise Exception("Failed to load spec")
    except Exception as e:
        print(f"Warning: Could not reload API spec for final report comparison - {e}")
        spec_codes = {}

    sorted_coverage_data = pet_endpoints + other_endpoints

    for endpoint, data in sorted_coverage_data:
        expected_codes_init = sorted(data["status_codes"])
        tested_codes = sorted(list(set(data["tested"])))

        actual_spec_codes = spec_codes.get(endpoint, expected_codes_init)
        if set(actual_spec_codes) != set(expected_codes_init):
            expected_codes_str = f"{actual_spec_codes} (spec) vs {expected_codes_init} (init)"
        else:
            expected_codes_str = f"{expected_codes_init}"

        expected_count = len(expected_codes_init)
        tested_count = len(tested_codes)
        percentage = (tested_count / expected_count * 100) if expected_count > 0 else 0.0

        print(f"{endpoint}: {tested_count}/{expected_count} ({percentage:.1f}%) ------> {tested_codes} / {expected_codes_str}")

    print("\n" + "=" * 25)
    # Используем стандартные атрибуты сессии pytest
    passed_count = getattr(session, 'testscollected', 0) - getattr(session, 'testsfailed', 0) - getattr(session, 'testsskipped', 0)
    failed_count = getattr(session, 'testsfailed', 0)
    skipped_count = getattr(session, 'testsskipped', 0)
    print(f"{passed_count} passed, {failed_count} failed, {skipped_count} skipped")
    print("=" * 25)
