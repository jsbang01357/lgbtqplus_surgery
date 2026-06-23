import unittest
import datetime
from unittest.mock import patch

from app.surgery_status import compute_case_status

class SurgeryStatusTests(unittest.TestCase):

    @patch("app.surgery_status.get_now")
    def test_1_cancelled_case(self, mock_get_now):
        KST = datetime.timezone(datetime.timedelta(hours=9))
        mock_get_now.return_value = datetime.datetime(2026, 6, 23, 12, 0, tzinfo=KST)
        
        # 1. 취소된 케이스는 취소 상태 반환
        case = {
            "patient_code": "P-0001",
            "surgery_date": "2026-07-03",
            "is_cancelled": True,
            "surgery_status": "예정",
            "prep": {
                "lab_completed_date": "2026-06-15"
            }
        }
        res = compute_case_status(case)
        self.assertEqual(res["status"], "취소")
        self.assertEqual(res["status_auto"], "취소")
        self.assertEqual(res["missing_items"], [])

    @patch("app.surgery_status.get_now")
    def test_2_today_surgery(self, mock_get_now):
        KST = datetime.timezone(datetime.timedelta(hours=9))
        mock_get_now.return_value = datetime.datetime(2026, 6, 23, 12, 0, tzinfo=KST)
        
        # 2. 오늘 수술은 진행중 상태 반환
        case = {
            "patient_code": "P-0001",
            "surgery_date": "2026-06-23",
            "is_cancelled": False,
            "surgery_status": "예정",
            "prep": {
                "lab_completed_date": "2026-06-15"
            }
        }
        res = compute_case_status(case)
        self.assertEqual(res["status"], "진행중")
        self.assertEqual(res["status_auto"], "진행중")
        self.assertEqual(res["missing_items"], [])

    @patch("app.surgery_status.get_now")
    def test_3_missing_lab_date(self, mock_get_now):
        KST = datetime.timezone(datetime.timedelta(hours=9))
        mock_get_now.return_value = datetime.datetime(2026, 6, 23, 12, 0, tzinfo=KST)
        
        # 3. 검사일이 없으면 확인필요 상태 반환
        case = {
            "patient_code": "P-0001",
            "surgery_date": "2026-07-03",
            "calendar_status": "연동완료",
            "is_cancelled": False,
            "surgery_status": "예정",
            "prep": {
                "lab_date": "",
                "lab_completed_date": "",
                "premed_status": "완료",
                "cooperation_status": "불필요",
                "admission_guidance_done": True,
                "documents_checked": True
            }
        }
        res = compute_case_status(case)
        self.assertEqual(res["status"], "확인필요")
        self.assertIn("검사일 누락", res["missing_items"])

    @patch("app.surgery_status.get_now")
    def test_4_lab_older_than_8_weeks(self, mock_get_now):
        KST = datetime.timezone(datetime.timedelta(hours=9))
        mock_get_now.return_value = datetime.datetime(2026, 6, 23, 12, 0, tzinfo=KST)
        
        # 4. 검사일이 수술일 기준 8주 초과면 확인필요 상태 반환
        case = {
            "patient_code": "P-0001",
            "surgery_date": "2026-07-03",
            "calendar_status": "연동완료",
            "is_cancelled": False,
            "surgery_status": "예정",
            "prep": {
                "lab_completed_date": "2026-05-01",  # older than 8 weeks (63 days before surgery_date)
                "premed_status": "완료",
                "cooperation_status": "불필요",
                "admission_guidance_done": True,
                "documents_checked": True
            }
        }
        res = compute_case_status(case)
        self.assertEqual(res["status"], "확인필요")
        self.assertIn("검사의뢰 8주 초과", res["missing_items"])

    @patch("app.surgery_status.get_now")
    def test_5_missing_premed(self, mock_get_now):
        KST = datetime.timezone(datetime.timedelta(hours=9))
        mock_get_now.return_value = datetime.datetime(2026, 6, 23, 12, 0, tzinfo=KST)
        
        # 5. 프리메드 미완료면 확인필요 상태 반환 (수술일 14일 이내일 때)
        case = {
            "patient_code": "P-0001",
            "surgery_date": "2026-06-30",  # 7 days in the future
            "calendar_status": "연동완료",
            "is_cancelled": False,
            "surgery_status": "예정",
            "prep": {
                "lab_completed_date": "2026-06-15",
                "premed_status": "미완료",
                "cooperation_status": "불필요",
                "admission_guidance_done": True,
                "documents_checked": True
            }
        }
        res = compute_case_status(case)
        self.assertEqual(res["status"], "확인필요")
        self.assertIn("프리메드 미완료", res["missing_items"])

    @patch("app.surgery_status.get_now")
    def test_6_missing_admission_guidance(self, mock_get_now):
        KST = datetime.timezone(datetime.timedelta(hours=9))
        mock_get_now.return_value = datetime.datetime(2026, 6, 23, 12, 0, tzinfo=KST)
        
        # 6. 입원 안내 미완료면 확인필요 상태 반환 (수술일 14일 이내일 때)
        case = {
            "patient_code": "P-0001",
            "surgery_date": "2026-06-30",  # 7 days in the future
            "calendar_status": "연동완료",
            "is_cancelled": False,
            "surgery_status": "예정",
            "prep": {
                "lab_completed_date": "2026-06-15",
                "premed_status": "완료",
                "cooperation_status": "불필요",
                "admission_guidance_done": False,
                "documents_checked": True
            }
        }
        res = compute_case_status(case)
        self.assertEqual(res["status"], "확인필요")
        self.assertIn("입원안내 미완료", res["missing_items"])

    @patch("app.surgery_status.get_now")
    def test_7_missing_documents_check(self, mock_get_now):
        KST = datetime.timezone(datetime.timedelta(hours=9))
        mock_get_now.return_value = datetime.datetime(2026, 6, 23, 12, 0, tzinfo=KST)
        
        # 7. 서류 확인 미완료면 확인필요 상태 반환 (수술일 14일 이내일 때)
        case = {
            "patient_code": "P-0001",
            "surgery_date": "2026-06-30",  # 7 days in the future
            "calendar_status": "연동완료",
            "is_cancelled": False,
            "surgery_status": "예정",
            "prep": {
                "lab_completed_date": "2026-06-15",
                "premed_status": "완료",
                "cooperation_status": "불필요",
                "admission_guidance_done": True,
                "documents_checked": False
            }
        }
        res = compute_case_status(case)
        self.assertEqual(res["status"], "확인필요")
        self.assertIn("서류확인 미완료", res["missing_items"])

    @patch("app.surgery_status.get_now")
    def test_8_missing_cooperation(self, mock_get_now):
        KST = datetime.timezone(datetime.timedelta(hours=9))
        mock_get_now.return_value = datetime.datetime(2026, 6, 23, 12, 0, tzinfo=KST)
        
        # 8. 협진이 진행중이거나 예정이면 확인필요 상태 반환 (수술일 14일 이내일 때)
        case = {
            "patient_code": "P-0001",
            "surgery_date": "2026-06-30",  # 7 days in the future
            "calendar_status": "연동완료",
            "is_cancelled": False,
            "surgery_status": "예정",
            "prep": {
                "lab_completed_date": "2026-06-15",
                "premed_status": "완료",
                "cooperation_status": "진행중",
                "admission_guidance_done": True,
                "documents_checked": True
            }
        }
        res = compute_case_status(case)
        self.assertEqual(res["status"], "확인필요")
        self.assertIn("협진 진행중", res["missing_items"])

    @patch("app.surgery_status.get_now")
    def test_10_calendar_not_synced_is_ok(self, mock_get_now):
        KST = datetime.timezone(datetime.timedelta(hours=9))
        mock_get_now.return_value = datetime.datetime(2026, 6, 23, 12, 0, tzinfo=KST)
        
        # 10. 캘린더 미연동은 "확인필요" 격상 기준이 아님 (준비완료 상태 유지)
        case = {
            "patient_code": "P-0001",
            "surgery_date": "2026-07-03",
            "calendar_status": "미연동",
            "is_cancelled": False,
            "surgery_status": "예정",
            "prep": {
                "lab_completed_date": "2026-06-15",
                "premed_status": "완료",
                "cooperation_status": "불필요",
                "admission_guidance_done": True,
                "documents_checked": True
            }
        }
        res = compute_case_status(case)
        self.assertEqual(res["status"], "준비완료")

    @patch("app.surgery_status.get_now")
    def test_11_calendar_error(self, mock_get_now):
        KST = datetime.timezone(datetime.timedelta(hours=9))
        mock_get_now.return_value = datetime.datetime(2026, 6, 23, 12, 0, tzinfo=KST)
        
        # 11. 캘린더 오류는 즉시 확인필요 상태 반환
        case = {
            "patient_code": "P-0001",
            "surgery_date": "2026-07-03",
            "calendar_status": "오류",
            "is_cancelled": False,
            "surgery_status": "예정",
            "prep": {
                "lab_completed_date": "2026-06-15",
                "premed_status": "완료",
                "cooperation_status": "불필요",
                "admission_guidance_done": True,
                "documents_checked": True
            }
        }
        res = compute_case_status(case)
        self.assertEqual(res["status"], "확인필요")
        self.assertIn("캘린더 연동 오류", res["missing_items"])

    @patch("app.surgery_status.get_now")
    def test_12_all_required_items_complete(self, mock_get_now):
        KST = datetime.timezone(datetime.timedelta(hours=9))
        mock_get_now.return_value = datetime.datetime(2026, 6, 23, 12, 0, tzinfo=KST)
        
        # 12. 모든 필수 항목 완료 시 준비완료 상태 반환
        case = {
            "patient_code": "P-0001",
            "surgery_date": "2026-07-03",
            "calendar_status": "연동완료",
            "is_cancelled": False,
            "surgery_status": "예정",
            "prep": {
                "lab_completed_date": "2026-06-15",
                "premed_status": "완료",
                "cooperation_status": "불필요",
                "admission_guidance_done": True,
                "documents_checked": True
            }
        }
        res = compute_case_status(case)
        self.assertEqual(res["status"], "준비완료")
        self.assertEqual(res["status_auto"], "준비완료")
        self.assertEqual(res["missing_items"], [])

    @patch("app.surgery_status.get_now")
    def test_future_missing_prep_is_not_warning(self, mock_get_now):
        KST = datetime.timezone(datetime.timedelta(hours=9))
        mock_get_now.return_value = datetime.datetime(2026, 6, 23, 12, 0, tzinfo=KST)
        
        # 수술일이 14일 이상 남았을 때는(D-22), prep 항목들이 완료되지 않았어도
        # missing_items에는 포함되지만, status는 준비완료 상태로 남아있어야 함.
        case = {
            "patient_code": "P-0001",
            "surgery_date": "2026-07-15",  # 22 days in the future
            "calendar_status": "연동완료",
            "is_cancelled": False,
            "surgery_status": "예정",
            "prep": {
                "lab_completed_date": "2026-06-15",
                "premed_status": "미완료",
                "cooperation_status": "진행중",
                "admission_guidance_done": False,
                "documents_checked": False
            }
        }
        res = compute_case_status(case)
        self.assertEqual(res["status"], "준비완료")
        self.assertEqual(res["status_auto"], "준비완료")
        self.assertIn("프리메드 미완료", res["missing_items"])
        self.assertIn("협진 진행중", res["missing_items"])


if __name__ == "__main__":
    unittest.main()
