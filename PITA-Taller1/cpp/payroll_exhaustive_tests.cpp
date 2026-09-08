#include "payroll_cycle.hpp"

#include <cassert>
#include <stdexcept>

using namespace pita::payroll;

static PayrollEmployee professor(const std::string& type = "planta") {
    PayrollEmployee employee;
    employee.employeeId = "P1";
    employee.employeeType = "Professor";
    employee.employmentType = type;
    employee.baseMonthlySalary = 1000000;
    employee.active = true;
    return employee;
}

static PayrollPeriod period(int days = 30) { return PayrollPeriod{"2026-09", days}; }

static void throws_invalid(void (*operation)()) {
    bool thrown = false;
    try { operation(); } catch (const std::invalid_argument&) { thrown = true; }
    assert(thrown);
}

int main() {
    const PayrollRules rules{};
    const PayrollEmployee base = professor();
    const PayrollResult standard = calculatePayroll(base, period(), rules);

    assert(standard.baseSalary == 1000000); // 1, 2, 4, 5
    assert(calculatePayroll(professor("ocasional"), period(), rules).baseSalary == 1000000);
    PayrollEmployee catedratico = professor("catedratico");
    catedratico.baseMonthlySalary = 0; catedratico.hourlyRate = 25000; catedratico.hoursWorked = 40;
    assert(calculatePayroll(catedratico, period(), rules).baseSalary == 1000000); // 3
    PayrollEmployee administrative = base; administrative.employeeType = "Administrative";
    assert(calculatePayroll(administrative, period(), rules).baseSalary == 1000000); // 4

    PayrollEmployee points = professor();
    points.baseMonthlySalary = 0; points.pointValue = 1000;
    points.categoryScore = 10; points.titleScore = 5; points.experienceScore = 3;
    points.productivityScore = 4; points.academicManagementScore = 2;
    assert(calculatePayroll(points, period(), rules).baseSalary == 24000); // 6
    PayrollEmployee noPoints = professor(); noPoints.baseMonthlySalary = 0;
    assert(calculatePayroll(noPoints, period(), rules).baseSalary == 0); // 7

    const PayrollNovelty salaryBonus{"SALARY_BONUS", 100000, 1, true, true};
    const PayrollNovelty nonSalary400{"NON_SALARY", 400000, 1, false, false};
    const PayrollNovelty nonSalary1000{"NON_SALARY", 1000000, 1, false, false};
    const PayrollResult deductions = calculatePayroll(base, period(), rules, {}, 12345);
    assert(deductions.totalEmployeeDeductions == 92345); // 8
    assert(calculatePayroll(base, period(), rules, {salaryBonus}).grossSalary == 1100000); // 9
    assert(calculatePayroll(base, period(), rules, {nonSalary400}).ibc == 1000000); // 10, 11
    assert(calculatePayroll(base, period(), rules, {nonSalary1000}).ibc == 1200000); // 12

    assert(standard.serviceBonusProvision == 6942); // 13
    assert(standard.severanceProvision == 6942); // 14
    assert(standard.severanceInterest == 69); // 15
    assert(standard.christmasBonusProvision == 6942); // 16
    assert(standard.vacationProvision == 1738); // 17
    assert(standard.vacationBonusProvision == 4633); // 18
    PayrollEmployee senior = base; senior.continuousServiceDays = 360;
    PayrollRules serviceRules = rules; serviceRules.serviceBonusTop = 2000000;
    assert(calculatePayroll(senior, period(), serviceRules).serviceBonus == 500000); // 19

    assert(standard.employerPension == 120000); // 20
    assert(standard.employerHealth == 85000); // 21
    PayrollRules exempt = rules; exempt.healthExempt = true; exempt.senaExempt = true; exempt.icbfExempt = true;
    const PayrollResult exemptResult = calculatePayroll(base, period(), exempt);
    assert(exemptResult.employeeHealth == 0 && exemptResult.employerHealth == 0); // 22
    assert(standard.arl == 5220); // 23
    assert(standard.compensationFund == 40000); // 24
    assert(standard.sena == 20000); // 25
    assert(standard.icbf == 30000); // 26

    PayrollEmployee rounded = base; rounded.baseMonthlySalary = 1234567;
    const PayrollResult roundedResult = calculatePayroll(rounded, period(), rules);
    assert(roundedResult.employeeHealth == 49383 && roundedResult.employeePension == 49383); // 27
    assert(calculatePayroll(base, period(15), rules).serviceBonusProvision == 3471); // 28
    assert(calculatePayroll(base, period(10), rules).serviceBonusProvision == 2314); // 29
    assert(calculatePayroll(base, period(20), rules).serviceBonusProvision == 4628); // 30

    PayrollCycle datesCycle;
    const PayrollPeriodRecord datesPeriod = datesCycle.createPeriod(
        "2026-09-DATES", 2026, 9, "2026-09-01", "2026-09-30");
    PayrollEmployee hired = base; hired.hireDate = "2026-09-21";
    const PayrollRunRecord hiredRun = datesCycle.calculateRun(datesPeriod.periodId, {hired}, rules);
    assert(hiredRun.details.front().daysWorked == 10);
    PayrollCycle retiredCycle;
    const PayrollPeriodRecord retiredPeriod = retiredCycle.createPeriod(
        "2026-09-RETIRE", 2026, 9, "2026-09-01", "2026-09-30");
    PayrollEmployee retired = base; retired.terminationDate = "2026-09-20";
    const PayrollRunRecord retiredRun = retiredCycle.calculateRun(retiredPeriod.periodId, {retired}, rules);
    assert(retiredRun.details.front().daysWorked == 20);

    PayrollCycle cycle;
    const PayrollPeriodRecord formalPeriod = cycle.createPeriod("2026-09", 2026, 9, "2026-09-01", "2026-09-30");
    PayrollEmployee inactive = base; inactive.active = false;
    bool rejected = false;
    try { cycle.calculateRun(formalPeriod.periodId, {inactive}, rules); } catch (const std::invalid_argument&) { rejected = true; }
    assert(rejected); // 33
    const PayrollRunRecord run = cycle.calculateRun(formalPeriod.periodId, {base}, rules, "calculator");
    bool duplicate = false;
    try { cycle.calculateRun(formalPeriod.periodId, {base}, rules); } catch (const std::invalid_argument&) { duplicate = true; }
    assert(duplicate); // 32
    cycle.approveRun(run.runId, "approver");
    cycle.closeRun(run.runId, "closer");
    bool closed = false;
    try { cycle.calculateRun(formalPeriod.periodId, {base}, rules); } catch (const std::invalid_argument&) { closed = true; }
    assert(closed); // 31
    assert(!cycle.runs().front().calculatedBy.empty());
    assert(!cycle.runs().front().approvedBy.empty());
    assert(!cycle.runs().front().closedBy.empty());

    PayrollEmployee missing = base; missing.employeeId = "";
    bool missingRejected = false;
    try { calculatePayroll(missing, period(), rules); } catch (const std::invalid_argument&) { missingRejected = true; }
    assert(missingRejected); // 34
    PayrollEmployee negative = base; negative.baseMonthlySalary = -1;
    bool negativeRejected = false;
    try { calculatePayroll(negative, period(), rules); } catch (const std::invalid_argument&) { negativeRejected = true; }
    assert(negativeRejected); // 35
    PayrollRules invalid = rules; invalid.nonSalaryLimit = 1.1;
    bool configRejected = false;
    try { calculatePayroll(base, period(), invalid); } catch (const std::invalid_argument&) { configRejected = true; }
    assert(configRejected); // 36

    assert(standard.grossSalary == 1000000);
    assert(standard.ibc == 1000000);
    assert(standard.totalEmployeeDeductions == 80000);
    assert(standard.totalEmployerContributions == 300220);
    assert(standard.netSalary == 920000);
    assert(standard.totalEmployerCost == 1327486);
    return 0;
}
