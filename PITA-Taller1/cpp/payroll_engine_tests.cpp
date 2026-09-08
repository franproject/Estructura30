#include "payroll_engine.hpp"

#include <cassert>

using namespace pita::payroll;

int main() {
    PayrollPeriod period{"2026-09", 30};
    PayrollEmployee professor;
    professor.employeeId = "P1";
    professor.employeeType = "Professor";
    professor.employmentType = "planta";
    professor.pointValue = 1000;
    professor.categoryScore = 10;
    professor.titleScore = 5;
    professor.experienceScore = 3;
    professor.productivityScore = 4;
    professor.academicManagementScore = 2;

    const PayrollResult professorResult = calculatePayroll(professor, period, PayrollRules{});
    assert(professorResult.baseSalary == 24000);
    assert(professorResult.serviceBonusProvision == 167);
    assert(professorResult.severanceProvision == 167);

    PayrollEmployee administrative;
    administrative.employeeId = "A1";
    administrative.employeeType = "Administrative";
    administrative.employmentType = "planta";
    administrative.baseMonthlySalary = 1000000;
    const PayrollNovelty nonSalary{"BONUS", 1000000, 1, false, false};
    const PayrollResult administrativeResult = calculatePayroll(
        administrative, period, PayrollRules{}, {nonSalary});
    assert(administrativeResult.grossSalary == 2000000);
    assert(administrativeResult.ibc == 1200000);
    assert(administrativeResult.employeeHealth == 48000);

    PayrollEmployee knownCase;
    knownCase.employeeId = "KNOWN-1";
    knownCase.employeeType = "Administrative";
    knownCase.employmentType = "planta";
    knownCase.baseMonthlySalary = 1000000;
    const PayrollPeriod knownPeriod{"2026-09", 30};
    const PayrollResult knownResult = calculatePayroll(knownCase, knownPeriod, PayrollRules{});
    assert(knownResult.employeeHealth == 40000);
    assert(knownResult.employeePension == 40000);
    assert(knownResult.serviceBonusProvision == 6942);
    assert(knownResult.severanceProvision == 6942);
    assert(knownResult.netSalary == 920000);
    assert(knownResult.totalEmployerContributions == 300220);

    const Payslip payslip = generatePayslip(
        knownCase, knownPeriod, knownResult, PayrollConfiguration{}, "RUN-KNOWN");
    assert(payslip.result.netSalary == knownResult.netSalary);
    assert(payslip.traceId == "RUN-KNOWN:KNOWN-1");

    return 0;
}
