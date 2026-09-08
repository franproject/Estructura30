#include "payroll_engine.hpp"

#include <iostream>

using namespace pita::payroll;

int main() {
    PayrollEmployee employee;
    employee.employeeId = "PARITY";
    employee.employeeType = "Professor";
    employee.employmentType = "planta";
    employee.baseMonthlySalary = 1234567;
    employee.active = true;
    PayrollPeriod period{"2026-09", 30};
    PayrollNovelty salaryBonus{"SALARY_BONUS", 111111, 1, true, true};
    PayrollNovelty nonSalary{"NON_SALARY", 222222, 1, false, false};
    const PayrollResult result = calculatePayroll(employee, period, PayrollRules{}, {salaryBonus, nonSalary});
    const Money benefits = result.serviceBonusProvision + result.severanceProvision + result.severanceInterest +
        result.christmasBonusProvision + result.vacationProvision + result.vacationBonusProvision;
    std::cout << result.grossSalary << ',' << result.ibc << ',' << result.totalEmployeeDeductions << ','
              << benefits << ',' << result.totalEmployerContributions << ',' << result.netSalary << ','
              << result.totalEmployerCost;
    return 0;
}
