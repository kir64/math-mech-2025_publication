import pytest
import requests
import time
from metrics import coverage

BASE_URL = "https://petstore3.swagger.io/api/v3"


# Хелперы с улучшенной обработкой ошибок
def create_pet_with_retry(pet_data):
    for _ in range(3):
        response = requests.post(f"{BASE_URL}/pet", json=pet_data)
        if response.status_code == 200:
            return response.json()["id"]
        time.sleep(1)
    return None


def delete_pet_with_retry(pet_id):
    for _ in range(3):
        response = requests.delete(f"{BASE_URL}/pet/{pet_id}")
        if response.status_code == 200:
            return True
        time.sleep(1)
    return False


@pytest.fixture
def test_pet():
    pet_data = {
        "id": int(time.time()),  # Уникальный ID на основе времени
        "name": "TestPet",
        "photoUrls": ["https://example.com/photo.jpg"],
        "status": "available",
        "category": {"id": 1, "name": "Dogs"}
    }
    pet_id = create_pet_with_retry(pet_data)
    yield pet_id
    if pet_id:
        delete_pet_with_retry(pet_id)


# 1. Тесты для POST /pet --------------------------------------------------------
def test_post_pet_success():
    pet_data = {
        "name": "NewPet",
        "photoUrls": ["https://example.com/photo.jpg"]
    }
    response = requests.post(f"{BASE_URL}/pet", json=pet_data)
    assert response.status_code in [200, 201], f"Unexpected status {response.status_code}"
    coverage.record_test_result("POST /pet", response.status_code)
    delete_pet_with_retry(response.json().get("id"))


def test_post_pet_invalid_data():
    response = requests.post(f"{BASE_URL}/pet", json={"invalid": "data"})
    assert response.status_code in [400, 415, 500], "Validation error expected"
    coverage.record_test_result("POST /pet", response.status_code)


# 2. Тесты для PUT /pet ---------------------------------------------------------
def test_put_pet_success(test_pet):
    update_data = {
        "id": test_pet,
        "name": "UpdatedPet",
        "status": "sold",
        "photoUrls": ["https://new-url.com/photo.jpg"]
    }
    response = requests.put(f"{BASE_URL}/pet", json=update_data)
    assert response.status_code in [200, 204], "Update failed"
    coverage.record_test_result("PUT /pet", response.status_code)


def test_put_pet_not_found():
    response = requests.put(f"{BASE_URL}/pet", json={"id": 999999999})
    assert response.status_code in [404, 400], "Should handle invalid ID"
    coverage.record_test_result("PUT /pet", response.status_code)


# 3. Тесты для GET /pet/{petId} -------------------------------------------------
def test_get_pet_success(test_pet):
    response = requests.get(f"{BASE_URL}/pet/{test_pet}")
    assert response.status_code == 200, "Pet should exist"
    coverage.record_test_result("GET /pet/{petId}", 200)


def test_get_pet_invalid_id():
    response = requests.get(f"{BASE_URL}/pet/invalid_id")
    assert response.status_code in [400, 404], "Invalid ID handling"
    coverage.record_test_result("GET /pet/{petId}", response.status_code)


# 4. Тесты для DELETE /pet/{petId} ----------------------------------------------
def test_delete_pet_success(test_pet):
    response = requests.delete(f"{BASE_URL}/pet/{test_pet}")
    assert response.status_code == 200, "Delete should succeed"

    # Проверка действительно удаления
    for _ in range(3):
        verify_resp = requests.get(f"{BASE_URL}/pet/{test_pet}")
        if verify_resp.status_code == 404:
            break
        time.sleep(1)
    assert verify_resp.status_code == 404, "Pet still exists after delete"

    coverage.record_test_result("DELETE /pet/{petId}", 200)
    coverage.record_test_result("GET /pet/{petId}", 404)


# 5. Тесты для GET /pet/findByStatus --------------------------------------------
@pytest.mark.parametrize("status", ["available", "pending", "sold", "invalid"])
def test_find_by_status(status):
    response = requests.get(f"{BASE_URL}/pet/findByStatus", params={"status": status})
    if status == "invalid":
        assert response.status_code in [400, 500], "Invalid status handling"
    else:
        assert response.status_code == 200, "Valid status should work"
    coverage.record_test_result("GET /pet/findByStatus", response.status_code)


# 6. Тесты для POST /pet/{petId}/uploadImage ------------------------------------
def test_upload_image_success(test_pet):
    files = {'file': ('image.jpg', b'content', 'image/jpeg')}
    response = requests.post(
        f"{BASE_URL}/pet/{test_pet}/uploadImage",
        files=files,
        headers={"Content-Type": "multipart/form-data"}
    )
    assert response.status_code in [200, 201], "Image upload failed"
    coverage.record_test_result("POST /pet/{petId}/uploadImage", response.status_code)


# End-to-End тест ---------------------------------------------------------------
def test_full_lifecycle():
    # Создание
    pet_data = {
        "name": "LifecyclePet",
        "photoUrls": ["https://lifecycle.com/photo.jpg"],
        "status": "available"
    }
    create_resp = requests.post(f"{BASE_URL}/pet", json=pet_data)
    assert create_resp.status_code in [200, 201]
    pet_id = create_resp.json().get("id")

    # Чтение
    get_resp = requests.get(f"{BASE_URL}/pet/{pet_id}")
    assert get_resp.status_code == 200

    # Обновление
    update_data = {"id": pet_id, "status": "pending"}
    requests.put(f"{BASE_URL}/pet", json=update_data)

    # Удаление
    delete_resp = requests.delete(f"{BASE_URL}/pet/{pet_id}")
    assert delete_resp.status_code == 200

    # Верификация
    for _ in range(3):
        verify_resp = requests.get(f"{BASE_URL}/pet/{pet_id}")
        if verify_resp.status_code == 404:
            break
        time.sleep(1)
    assert verify_resp.status_code == 404

# Фикстура для отчетности (без изменений)
