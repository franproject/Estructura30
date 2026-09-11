import os
import tempfile
import unittest
from datetime import date

from models.administrative import Administrative
from models.payroll_novelty import PayrollNovelty, PayrollNoveltyStatus, PayrollNoveltyType
from persistence.file_manager import (
    load_payroll_audit,
    load_payroll_novelties,
    load_payroll_periods,
    load_payroll_runs,
    save_payroll_audit,
    save_payroll_novelties,
    save_payroll_periods,
    save_payroll_runs,
)
from services.payroll_cycle import PayrollCycleService
from services.payroll_engine import PayrollRules


class PayrollCycleTests(unittest.TestCase):
    def test_full_lifecycle_and_persistence(self):
        service = PayrollCycleService()
        period = service.create_period(2026, 9, "2026-09-01", "2026-09-30", "user-1")
        novelty = PayrollNovelty(
            novelty_id="N-1", period_id=period.period_id, employee_id="7",
            novelty_type=PayrollNoveltyType.BONUS, start_date="2026-09-01",
            amount="100000", is_salary=False, affects_ibc=False,
            status=PayrollNoveltyStatus.APPROVED,
        )
        service.register_novelty(novelty, "user-1")
        employee = Administrative(administrative_id=7, full_name="Maria", base_salary=1000000, active=True)
        run = service.calculate_run(period.period_id, [employee], PayrollRules(), "user-1")
        self.assertEqual(period.status.value, "CALCULATED")
        self.assertEqual(run.employee_ids, ["7"])
        self.assertEqual(run.details[0]["employee_id"], "7")
        self.assertTrue(run.audit_ids)
        service.approve_run(run.run_id, "user-1")
        service.close_run(run.run_id, "user-1")
        self.assertEqual(period.status.value, "CLOSED")
        self.assertEqual(run.status.value, "CLOSED")
        with self.assertRaises(ValueError):
            service.calculate_run(period.period_id, [employee], PayrollRules(), "user-1")

        with tempfile.TemporaryDirectory() as directory:
            paths = {name: os.path.join(directory, name) for name in (
                "periods.json", "runs.json", "novelties.json", "audit.json"
            )}
            self.assertTrue(save_payroll_periods([period], paths["periods.json"]))
            self.assertTrue(save_payroll_runs([run], paths["runs.json"]))
            self.assertTrue(save_payroll_novelties([novelty], paths["novelties.json"]))
            self.assertTrue(save_payroll_audit(service.audits, paths["audit.json"]))
            self.assertEqual(load_payroll_periods(paths["periods.json"])[0].status.value, "CLOSED")
            self.assertEqual(load_payroll_runs(paths["runs.json"])[0].run_id, run.run_id)
            self.assertEqual(load_payroll_runs(paths["runs.json"])[0].details[0]["employee_id"], "7")
            self.assertEqual(load_payroll_novelties(paths["novelties.json"])[0].novelty_id, "N-1")
            self.assertGreaterEqual(len(load_payroll_audit(paths["audit.json"])), 4)

    def test_undefined_formula_is_not_invented(self):
        service = PayrollCycleService()
        period = service.create_period(2026, 10, "2026-10-01", "2026-10-31")
        novelty = PayrollNovelty(
            novelty_id="N-2", period_id=period.period_id, employee_id="7",
            novelty_type=PayrollNoveltyType.INCAPACITY, start_date="2026-10-01",
            status=PayrollNoveltyStatus.APPROVED,
        )
        service.register_novelty(novelty)
        employee = Administrative(administrative_id=7, full_name="Maria", base_salary=1000000, active=True)
        with self.assertRaises(ValueError):
            service.calculate_run(period.period_id, [employee], PayrollRules())


if __name__ == "__main__":
    unittest.main()
