# conftest.py
import pytest
from metrics import coverage

def pytest_sessionfinish(session, exitstatus):
    try:
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
    except Exception as e:
        print(f"Ошибка при выводе метрик: {str(e)}")
