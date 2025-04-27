import requests

BASE_URL = "https://petstore.swagger.io/v2"


class CoverageTracker:
    def __init__(self):
        self.test_results = {}

    def record_test_result(self, endpoint, status_code):
        if endpoint not in self.test_results:
            self.test_results[endpoint] = set()
        self.test_results[endpoint].add(str(status_code))

    def print_coverage_report(self):
        print("\n" + "=" * 50)
        print("                API COVERAGE REPORT                 ")
        print("=" * 50)

        pet_endpoints = {k: v for k, v in self.test_results.items() if
                         k.startswith(('GET /pet', 'POST /pet', 'PUT /pet', 'DELETE /pet'))}
        all_endpoints = self.test_results

        def calculate_coverage(endpoint, actual_codes, expected_codes):
            return len(actual_codes.intersection(expected_codes)) / len(expected_codes) * 100

        expected_codes_per_endpoint = {
            "PUT /pet": {"200", "400", "404", "422"},
            "POST /pet": {"200", "400", "422"},
            "GET /pet/findByStatus": {"200", "400"},
            "GET /pet/findByTags": {"200", "400"},
            "GET /pet/{petId}": {"200", "400", "404"},
            "POST /pet/{petId}": {"200", "400"},
            "DELETE /pet/{petId}": {"200", "400"},
            "POST /pet/{petId}/uploadImage": {"200", "400", "404"},
        }

        total_covered = 0
        total_expected = 0
        fully_covered = 0

        for endpoint, expected_statuses in expected_codes_per_endpoint.items():
            actual_statuses = all_endpoints.get(endpoint, set())
            covered = len(actual_statuses.intersection(expected_statuses))
            expected = len(expected_statuses)
            total_covered += covered
            total_expected += expected

            percent_coverage = (covered / expected) * 100
            print(
                f"{endpoint}: {covered}/{expected} ({percent_coverage:.1f}%) ---> {sorted(actual_statuses)} / {sorted(expected_statuses)}")
            if percent_coverage == 100.0:
                fully_covered += 1

        avg_endpoint_coverage = (sum(
            (len(all_endpoints.get(ep, set()).intersection(expected)) / len(expected))
            for ep, expected in expected_codes_per_endpoint.items()
        ) / len(expected_codes_per_endpoint)) * 100

        print("\nSummary:")
        print(f"Среднее покрытие эндпоинтов раздела Pet: {avg_endpoint_coverage:.1f}%")
        print(f"Полностью покрытые эндпоинты: {fully_covered}")
        print(f"Общее покрытие статус-кодов: {(total_covered / total_expected) * 100:.1f}%")
        print("=" * 50)


coverage = CoverageTracker()

import pytest


@pytest.fixture(scope="module")
def new_pet():
    pet_data = {
        "id": 123456789,
        "name": "TestPet",
        "photoUrls": ["http://example.com/photo.jpg"],
        "status": "available"
    }
    response = requests.post(f"{BASE_URL}/pet", json=pet_data)
    coverage.record_test_result("POST /pet", response.status_code)
    assert response.status_code == 200
    return pet_data


def test_create_pet(new_pet):
    assert new_pet["name"] == "TestPet"


def test_update_pet(new_pet):
    updated_pet = new_pet.copy()
    updated_pet["status"] = "sold"
    response = requests.put(f"{BASE_URL}/pet", json=updated_pet)
    coverage.record_test_result("PUT /pet", response.status_code)
    assert response.status_code == 200


def test_get_pet_by_id(new_pet):
    response = requests.get(f"{BASE_URL}/pet/{new_pet['id']}")
    coverage.record_test_result("GET /pet/{petId}", response.status_code)
    assert response.status_code == 200


def test_find_pet_by_status():
    response = requests.get(f"{BASE_URL}/pet/findByStatus", params={"status": "available"})
    coverage.record_test_result("GET /pet/findByStatus", response.status_code)
    assert response.status_code == 200


def test_find_pet_by_tags():
    response = requests.get(f"{BASE_URL}/pet/findByTags", params={"tags": "tag1"})
    coverage.record_test_result("GET /pet/findByTags", response.status_code)
    assert response.status_code == 200 or response.status_code == 400


def test_upload_pet_image(new_pet):
    files = {"file": ("filename.jpg", b"dummy_content", "image/jpeg")}
    response = requests.post(f"{BASE_URL}/pet/{new_pet['id']}/uploadImage", files=files)
    coverage.record_test_result("POST /pet/{petId}/uploadImage", response.status_code)
    assert response.status_code in (200, 400, 404)


def test_update_pet_with_form(new_pet):
    data = {
        "name": "UpdatedTestPet",
        "status": "pending"
    }
    response = requests.post(f"{BASE_URL}/pet/{new_pet['id']}", data=data)
    coverage.record_test_result("POST /pet/{petId}", response.status_code)
    assert response.status_code in (200, 400)


def test_get_nonexistent_pet(new_pet):
    # Удаляем pet
    delete_response = requests.delete(f"{BASE_URL}/pet/{new_pet['id']}")
    coverage.record_test_result("DELETE /pet/{petId}", delete_response.status_code)
    assert delete_response.status_code in (200, 400)

    # Проверяем что pet больше не существует
    get_response = requests.get(f"{BASE_URL}/pet/{new_pet['id']}")
    coverage.record_test_result("GET /pet/{petId}", get_response.status_code)
    assert get_response.status_code == 404


def test_create_pet_invalid_data():
    response = requests.post(f"{BASE_URL}/pet", json={"invalidField": "value"})
    coverage.record_test_result("POST /pet", response.status_code)
    assert response.status_code in (400, 422)


def test_update_pet_invalid_id():
    invalid_pet = {
        "id": "invalid_id",
        "name": "BadPet",
        "photoUrls": ["http://example.com/photo.jpg"],
        "status": "available"
    }
    response = requests.put(f"{BASE_URL}/pet", json=invalid_pet)
    coverage.record_test_result("PUT /pet", response.status_code)
    assert response.status_code in (400, 422)


def test_find_pet_by_invalid_status():
    response = requests.get(f"{BASE_URL}/pet/findByStatus", params={"status": "nonexistent"})
    coverage.record_test_result("GET /pet/findByStatus", response.status_code)
    assert response.status_code in (400, 200)


def test_print_coverage():
    coverage.print_coverage_report()
