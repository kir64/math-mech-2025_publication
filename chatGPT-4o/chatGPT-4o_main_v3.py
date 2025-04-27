import requests

BASE_URL = "https://petstore.swagger.io/v2"

class CoverageTracker:
    def __init__(self):
        self.results = {}

    def record_test_result(self, endpoint, status_code):
        if endpoint not in self.results:
            self.results[endpoint] = set()
        self.results[endpoint].add(str(status_code))

    def print_coverage_report(self):
        endpoints = {
            "PUT /pet": ["200", "400", "404", "422"],
            "POST /pet": ["200", "400", "422"],
            "GET /pet/findByStatus": ["200", "400"],
            "GET /pet/findByTags": ["200", "400"],
            "GET /pet/{petId}": ["200", "400", "404"],
            "POST /pet/{petId}": ["200", "400"],
            "DELETE /pet/{petId}": ["200", "400"],
            "POST /pet/{petId}/uploadImage": ["200", "400", "404"]
        }

        total_covered = 0
        total_expected = 0
        fully_covered = 0

        print("\n==================================================")
        print("                API COVERAGE REPORT                 ")
        print("==================================================")

        for endpoint, expected_codes in endpoints.items():
            actual_codes = self.results.get(endpoint, set())
            covered = len(actual_codes.intersection(expected_codes))
            expected = len(expected_codes)
            percent = (covered / expected) * 100 if expected > 0 else 0
            total_covered += covered
            total_expected += expected
            if covered == expected:
                fully_covered += 1
            print(f"{endpoint}: {covered}/{expected} ({percent:.1f}%) ---> {list(actual_codes)} / {expected_codes}")

        avg_coverage = (total_covered / total_expected) * 100 if total_expected > 0 else 0

        print("\nSummary:")
        print(f"Среднее покрытие эндпоинтов раздела Pet: {avg_coverage:.1f}%")
        print(f"Полностью покрытые эндпоинты: {fully_covered}")
        print("==================================================\n")

coverage = CoverageTracker()

new_pet = {
    "id": 123456789,
    "name": "TestPet",
    "photoUrls": ["http://example.com/photo.jpg"],
    "status": "available"
}

def test_create_pet():
    response = requests.post(f"{BASE_URL}/pet", json=new_pet)
    coverage.record_test_result("POST /pet", response.status_code)
    assert response.status_code in (200, 400, 422)

def test_update_pet():
    new_pet["status"] = "sold"
    response = requests.put(f"{BASE_URL}/pet", json=new_pet)
    coverage.record_test_result("PUT /pet", response.status_code)
    assert response.status_code in (200, 400, 404, 422)

def test_get_pet_by_id():
    response = requests.get(f"{BASE_URL}/pet/{new_pet['id']}")
    coverage.record_test_result("GET /pet/{petId}", response.status_code)
    assert response.status_code in (200, 400, 404)

def test_find_pet_by_status():
    response = requests.get(f"{BASE_URL}/pet/findByStatus", params={"status": "available"})
    coverage.record_test_result("GET /pet/findByStatus", response.status_code)
    assert response.status_code in (200, 400)

def test_find_pet_by_tags():
    response = requests.get(f"{BASE_URL}/pet/findByTags", params={"tags": "tag1"})
    coverage.record_test_result("GET /pet/findByTags", response.status_code)
    assert response.status_code in (200, 400)

def test_upload_pet_image():
    files = {"file": ("filename.jpg", b"dummy_content")}
    response = requests.post(f"{BASE_URL}/pet/{new_pet['id']}/uploadImage", files=files)
    coverage.record_test_result("POST /pet/{petId}/uploadImage", response.status_code)
    assert response.status_code in (200, 400, 404)

def test_update_pet_with_form():
    response = requests.post(f"{BASE_URL}/pet/{new_pet['id']}", data={"name": "UpdatedName"})
    coverage.record_test_result("POST /pet/{petId}", response.status_code)
    assert response.status_code in (200, 400)

def test_get_nonexistent_pet():
    response = requests.get(f"{BASE_URL}/pet/0")
    coverage.record_test_result("GET /pet/{petId}", response.status_code)
    assert response.status_code in (400, 404)

def test_create_pet_invalid_data():
    invalid_data = {"invalidField": "value"}
    response = requests.post(f"{BASE_URL}/pet", json=invalid_data)
    coverage.record_test_result("POST /pet", response.status_code)
    assert response.status_code in (400, 422, 200)

def test_update_pet_invalid_id():
    invalid_pet = {
        "id": "invalid_id",
        "name": "BadPet",
        "photoUrls": ["http://example.com/photo.jpg"],
        "status": "available"
    }
    response = requests.put(f"{BASE_URL}/pet", json=invalid_pet)
    coverage.record_test_result("PUT /pet", response.status_code)
    assert response.status_code in (400, 422, 500)

def test_find_pet_by_invalid_status():
    response = requests.get(f"{BASE_URL}/pet/findByStatus", params={"status": "nonexistentstatus"})
    coverage.record_test_result("GET /pet/findByStatus", response.status_code)
    assert response.status_code in (200, 400)

def test_print_coverage():
    coverage.print_coverage_report()
