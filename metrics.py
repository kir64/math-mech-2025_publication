import requests
from collections import defaultdict


class CoverageMetrics:
    def __init__(self):
        # Инициализация структуры для хранения данных о покрытии
        self.coverage_data = defaultdict(lambda: {
            "status_codes": [],
            "tested": []
        })

        # Загружаем спецификацию API
        self._load_api_specification()

    def _load_api_specification(self):
        """Загружает спецификацию API и инициализирует ожидаемые статус-коды"""
        try:
            api_spec = requests.get("https://petstore3.swagger.io/api/v3/openapi.json").json()
            paths = api_spec.get("paths", {})

            for endpoint, methods in paths.items():
                for method, details in methods.items():
                    if method.lower() in ['get', 'post', 'put', 'delete', 'patch']:
                        key = f"{method.upper()} {endpoint}"
                        responses = details.get("responses", {})
                        self.coverage_data[key]["status_codes"] = [str(code) for code in responses.keys() if code != 'default']
        except Exception as e:
            print(f"Warning: Could not load API spec - {str(e)}")
            # Fallback к базовым значениям если не удалось загрузить спецификацию
            self._initialize_default_coverage()

    def _initialize_default_coverage(self):
        """Инициализирует значения по умолчанию"""
        self.coverage_data = {
            "POST /pet": {"status_codes": ["200", "405"], "tested": []},
            "PUT /pet": {"status_codes": ["200", "400", "404", "405"], "tested": []},
            "GET /pet/findByStatus": {"status_codes": ["200", "400"], "tested": []},
            "GET /pet/findByTags": {"status_codes": ["200", "400"], "tested": []},
            "GET /pet/{petId}": {"status_codes": ["200", "400", "404"], "tested": []},
            "POST /pet/{petId}": {"status_codes": ["405"], "tested": []},
            "DELETE /pet/{petId}": {"status_codes": ["200", "400", "404"], "tested": []},
            "POST /pet/{petId}/uploadImage": {"status_codes": ["200"], "tested": []}
        }

    def record_test_result(self, endpoint: str, status_code: int):
        """Записывает результат теста"""
        status_str = str(status_code)
        if endpoint in self.coverage_data:
            if status_str not in self.coverage_data[endpoint]["tested"]:
                self.coverage_data[endpoint]["tested"].append(status_str)

    def calculate_metrics(self):
        metrics = {
            "avg_endpoint_coverage": 0.0,
            "pet_status_coverage": 0.0,
            "total_api_coverage": 0.0,
            "full_endpoint_coverage": 0.0
        }

        if not self.coverage_data:
            return metrics

        pet_data = {
            "count": 0,
            "ratio_sum": 0.0,
            "tested": 0,
            "expected": 0
        }

        all_data = {
            "tested": 0,
            "expected": 0,
            "fully_tested": 0
        }

        for endpoint, data in self.coverage_data.items():
            expected = len(data["status_codes"])
            tested = len(data["tested"])
            ratio = tested / expected if expected > 0 else 0.0

            # Общие данные
            all_data["tested"] += tested
            all_data["expected"] += expected
            if tested == expected and expected > 0:
                all_data["fully_tested"] += 1

            # Данные по Pet
            if "pet" in endpoint.lower():
                pet_data["count"] += 1
                pet_data["ratio_sum"] += ratio
                pet_data["tested"] += tested
                pet_data["expected"] += expected

        # Расчет метрик
        if pet_data["count"] > 0:
            metrics["avg_endpoint_coverage"] = (pet_data["ratio_sum"] / pet_data["count"]) * 100
            metrics["pet_status_coverage"] = (pet_data["tested"] / pet_data["expected"]) * 100

        if all_data["expected"] > 0:
            metrics["total_api_coverage"] = (all_data["tested"] / all_data["expected"]) * 100

        metrics["full_endpoint_coverage"] = (all_data["fully_tested"] / len(self.coverage_data)) * 100

        return metrics


# Глобальный экземпляр для использования в тестах
coverage = CoverageMetrics()
