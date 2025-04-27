# main.py

import pytest
import requests
from metrics import coverage

BASE_URL = "https://petstore3.swagger.io/api/v3"

# Фикстура для создания тестового питомца
@pytest.fixture
def new_pet():
    pet_data = {
        "id": 123456789,
        "name": "TestPet",
        "photoUrls": ["http://example.com/photo.jpg"],
        "status": "available"
    }
    response = requests.post(f"{BASE_URL}/pet", json=pet_data)
    coverage.record_test_result("POST /pet", response.status_code)
    return pet_data

# =============== Позитивные проверки эндпоинтов PET ===============

def test_create_pet(new_pet):
    assert new_pet["name"] == "TestPet"

def test_update_pet(new_pet):
    updated_pet = new_pet.copy()
    updated_pet["name"] = "UpdatedTestPet"
    response = requests.put(f"{BASE_URL}/pet", json=updated_pet)
    coverage.record_test_result("PUT /pet", response.status_code)
    assert response.status_code == 200

def test_get_pet_by_id(new_pet):
    response = requests.get(f"{BASE_URL}/pet/{new_pet['id']}")
    coverage.record_test_result("GET /pet/{petId}", response.status_code)
    assert response.status_code == 200
    assert response.json()["name"] == "TestPet"

def test_find_pet_by_status():
    response = requests.get(f"{BASE_URL}/pet/findByStatus", params={"status": "available"})
    coverage.record_test_result("GET /pet/findByStatus", response.status_code)
    assert response.status_code == 200

def test_find_pet_by_tags():
    response = requests.get(f"{BASE_URL}/pet/findByTags", params={"tags": ["tag1"]})
    coverage.record_test_result("GET /pet/findByTags", response.status_code)
    assert response.status_code == 200

def test_upload_pet_image(new_pet):
    files = {"file": ("filename.jpg", b"dummy_content")}
    response = requests.post(f"{BASE_URL}/pet/{new_pet['id']}/uploadImage", files=files)
    coverage.record_test_result("POST /pet/{petId}/uploadImage", response.status_code)
    assert response.status_code in (200, 400, 404)

def test_delete_pet(new_pet):
    response = requests.delete(f"{BASE_URL}/pet/{new_pet['id']}")
    coverage.record_test_result("DELETE /pet/{petId}", response.status_code)
    assert response.status_code == 200

# =============== Негативные проверки ===============

def test_get_nonexistent_pet():
    response = requests.get(f"{BASE_URL}/pet/0")
    coverage.record_test_result("GET /pet/{petId}", response.status_code)
    assert response.status_code == 404

def test_create_pet_invalid_data():
    invalid_pet = {
        "name": None  # Не должно быть None
    }
    response = requests.post(f"{BASE_URL}/pet", json=invalid_pet)
    coverage.record_test_result("POST /pet", response.status_code)
    assert response.status_code in (400, 422, 500)

def test_update_pet_invalid_id():
    invalid_pet = {
        "id": "invalid_id",
        "name": "Test",
        "photoUrls": [],
        "status": "available"
    }
    response = requests.put(f"{BASE_URL}/pet", json=invalid_pet)
    coverage.record_test_result("PUT /pet", response.status_code)
    assert response.status_code in (400, 422, 500)

# =============== Вывод покрытия ===============

def test_print_coverage():
    metrics = coverage.calculate_metrics()
    print("\n" + "="*50)
    print(" " * 15 + "API COVERAGE REPORT")
    print("="*50)
    print()
    print(f"1. Среднее покрытие эндпоинтов раздела Pet: {metrics['avg_endpoint_coverage']:.1f}%")
    print(f"2. Покрытие статус-кодов раздела Pet: {metrics['pet_status_coverage']:.1f}%")
    print(f"3. Полностью покрытые эндпоинты API: {metrics['full_endpoint_coverage']:.1f}%")
    print(f"4. Общее покрытие статус-кодов API: {metrics['total_api_coverage']:.1f}%")
    print()
    print("Детали по endpoint'ам:")

    for endpoint, data in coverage.coverage_data.items():
        tested = data["tested"]
        expected = data["status_codes"]
        ratio = (len(tested) / len(expected) * 100) if expected else 0.0
        print(f"{endpoint}: {len(tested)}/{len(expected)} ({ratio:.1f}%) ------> {tested} / {expected}")

    print("\n" + "="*25)
