#ifndef PITA_PAYROLL_ENGINE_HPP
#define PITA_PAYROLL_ENGINE_HPP

#include <cstdint>
#include <map>
#include <string>
#include <vector>

namespace pita::payroll {

using Money = std::int64_t;

struct PayrollPeriod {
    std::string period;
    int daysWorked = 0;
    int year = 0;
    int month = 0;
    std::string startDate;
    std::string endDate;
    std::string status = "OPEN";
};

struct PayrollNovelty {
    std::string code;
    Money amount = 0;
    Money quantity = 1;
    bool isSalary = true;
    bool affectsIbc = true;
};

struct PayrollEmployee {
    std::string employeeId;
    std::string employeeType;
    std::string employmentType;
    Money baseMonthlySalary = 0;
    Money pointValue = 0;
    double categoryScore = 0.0;
    double titleScore = 0.0;
    double experienceScore = 0.0;
    double productivityScore = 0.0;
    double academicManagementScore = 0.0;
    Money hourlyRate = 0;
    Money hoursWorked = 0;
    int continuousServiceDays = 0;
    bool active = true;
    int workedDays = 0;
    std::string hireDate;
    std::string terminationDate;
};

struct PayrollConcept {
    std::string code;
    Money amount = 0;
    bool isSalary = false;
    bool affectsIbc = false;
    std::string origin;
    std::string sourceId;
};

using PayrollLine = PayrollConcept;

struct EmployerContribution {
    std::string code;
    Money amount = 0;
    double rate = 0.0;
};

struct PayrollRules {
    double employeeHealthRate = 0.04;
    double employeePensionRate = 0.04;
    double serviceBonusRate = 0.0833;
    double severanceRate = 0.0833;
    double severanceInterestRate = 0.12;
    double christmasBonusRate = 0.0833;
    double vacationRate = 0.0417;
    double vacationDivisor = 720.0;
    double vacationBonusRate = 0.0556;
    double employerPensionRate = 0.12;
    double employerHealthRate = 0.085;
    double employerHealthExemptRate = 0.0;
    double compensationFundRate = 0.04;
    double senaRate = 0.02;
    double senaExemptRate = 0.0;
    double icbfRate = 0.03;
    double icbfExemptRate = 0.0;
    double nonSalaryLimit = 0.40;
    int serviceBonusYearDays = 360;
    Money serviceBonusTop = 0;
    double serviceBonusRateBelowTop = 0.50;
    double serviceBonusRateAboveTop = 0.35;
    std::string arlRiskClass = "I";
    std::vector<std::pair<std::string, double>> arlRates = {{"I", 0.00522}};
    bool healthExempt = false;
    bool senaExempt = false;
    bool icbfExempt = false;
};

struct PayrollResult {
    std::string employeeId;
    std::string employeeType;
    std::string period;
    int daysWorked = 0;
    Money baseSalary = 0;
    Money salaryAdjustments = 0;
    std::vector<PayrollLine> salaryConcepts;
    std::vector<PayrollLine> nonSalaryConcepts;
    Money grossSalary = 0;
    Money nonSalaryTotal = 0;
    Money ibc = 0;
    Money employeeHealth = 0;
    Money employeePension = 0;
    Money employeeOtherDeductions = 0;
    Money totalEmployeeDeductions = 0;
    Money serviceBonusProvision = 0;
    Money severanceProvision = 0;
    Money severanceInterest = 0;
    Money christmasBonusProvision = 0;
    Money vacationProvision = 0;
    Money vacationBonusProvision = 0;
    Money serviceBonus = 0;
    Money employerPension = 0;
    Money employerHealth = 0;
    Money arl = 0;
    Money compensationFund = 0;
    Money sena = 0;
    Money icbf = 0;
    Money totalEmployerContributions = 0;
    Money netSalary = 0;
    Money totalEmployerCost = 0;
    std::vector<EmployerContribution> employerContributions;
    std::vector<std::string> calculationTrace;
};

struct PayrollConfiguration {
    std::string institutionName = "Universidad Popular del Cesar";
    std::string institutionId;
};

struct Payslip {
    std::string payslipId;
    std::string runId;
    std::string periodId;
    std::string liquidationDate;
    PayrollConfiguration institution;
    PayrollEmployee employee;
    PayrollResult result;
    std::string faculty;
    std::string category;
    std::string title;
    std::string hireDate;
    std::string terminationDate;
    std::string linkageType;
    std::string position;
    std::string arlRiskClass;
    double arlRate = 0.0;
    double healthExemptionRate = 0.0;
    std::string traceId;
};

struct PayrollRun {
    std::string runId;
    std::string periodId;
    std::vector<std::string> employeeIds;
    std::vector<PayrollResult> details;
    Money grossTotal = 0;
    Money employeeDeductionTotal = 0;
    Money employerContributionTotal = 0;
    Money netTotal = 0;
    Money employerCost = 0;
    std::string status = "CALCULATED";
    std::string executedAt;
    std::vector<std::string> auditIds;
    std::string createdAt;
    std::string calculatedAt;
    std::string calculatedBy;
    std::string approvedAt;
    std::string approvedBy;
    std::string closedAt;
    std::string closedBy;
    std::vector<std::string> noveltyIds;
    std::string revisionOf;
};

void validate(const PayrollPeriod& period);
void validate(const PayrollEmployee& employee);
void validate(const PayrollRules& rules);

double totalPoints(const PayrollEmployee& employee);
Money salaryBase(const PayrollEmployee& employee);
PayrollResult calculatePayroll(
    const PayrollEmployee& employee,
    const PayrollPeriod& period,
    const PayrollRules& rules,
    const std::vector<PayrollNovelty>& novelties = {},
    Money otherDeductions = 0);

Payslip generatePayslip(
    const PayrollEmployee& employee,
    const PayrollPeriod& period,
    const PayrollResult& result,
    const PayrollConfiguration& configuration,
    const std::string& runId = "");

}  // namespace pita::payroll

#endif
