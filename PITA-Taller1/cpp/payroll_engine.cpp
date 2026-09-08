#include "payroll_engine.hpp"

#include <algorithm>
#include <cmath>
#include <ctime>
#include <stdexcept>

namespace pita::payroll {
namespace {

constexpr double DAYS_IN_YEAR = 360.0;

std::string timestamp() {
    const std::time_t current = std::time(nullptr);
    std::tm local{};
    const std::tm* localTime = std::localtime(&current);
    if (localTime != nullptr) local = *localTime;
    char buffer[32]{};
    std::strftime(buffer, sizeof(buffer), "%Y-%m-%dT%H:%M:%S", &local);
    return buffer;
}

Money roundPeso(double value) {
    return static_cast<Money>(std::llround(value));
}

Money multiply(Money value, Money quantity) {
    return value * quantity;
}

double arlRate(const PayrollRules& rules) {
    for (const auto& configured : rules.arlRates) {
        if (configured.first == rules.arlRiskClass) return configured.second;
    }
    throw std::invalid_argument("ARL risk class has no configured rate");
}

void validateRate(double value, const char* name) {
    if (value < 0.0) throw std::invalid_argument(std::string(name) + " cannot be negative");
}

}  // namespace

void validate(const PayrollPeriod& period) {
    if (period.period.empty()) throw std::invalid_argument("period is required");
    if (period.daysWorked < 0 || period.daysWorked > 360)
        throw std::invalid_argument("daysWorked must be between 0 and 360");
}

void validate(const PayrollEmployee& employee) {
    if (employee.employeeId.empty()) throw std::invalid_argument("employeeId is required");
    if (employee.employeeType != "Professor" && employee.employeeType != "Administrative")
        throw std::invalid_argument("unsupported employeeType");
    for (const auto value : {employee.baseMonthlySalary, employee.pointValue, employee.hourlyRate, employee.hoursWorked}) {
        if (value < 0) throw std::invalid_argument("employee monetary values cannot be negative");
    }
    for (const auto value : {employee.categoryScore, employee.titleScore, employee.experienceScore,
                             employee.productivityScore, employee.academicManagementScore}) {
        validateRate(value, "academic score");
    }
    if (employee.continuousServiceDays < 0)
        throw std::invalid_argument("continuousServiceDays cannot be negative");
}

void validate(const PayrollRules& rules) {
    for (const auto configured : {
             rules.employeeHealthRate, rules.employeePensionRate, rules.serviceBonusRate,
             rules.severanceRate, rules.severanceInterestRate, rules.christmasBonusRate,
             rules.vacationRate, rules.vacationBonusRate, rules.employerPensionRate,
             rules.employerHealthRate, rules.employerHealthExemptRate, rules.compensationFundRate,
             rules.senaRate, rules.senaExemptRate, rules.icbfRate, rules.icbfExemptRate,
             rules.serviceBonusRateBelowTop, rules.serviceBonusRateAboveTop}) {
        if (configured < 0.0) throw std::invalid_argument("payroll rate cannot be negative");
    }
    if (rules.vacationDivisor <= 0.0) throw std::invalid_argument("vacationDivisor must be positive");
    if (rules.serviceBonusYearDays <= 0) throw std::invalid_argument("serviceBonusYearDays must be positive");
    if (rules.nonSalaryLimit < 0.0 || rules.nonSalaryLimit > 1.0)
        throw std::invalid_argument("nonSalaryLimit must be between 0 and 1");
    arlRate(rules);
}

double totalPoints(const PayrollEmployee& employee) {
    return employee.categoryScore + employee.titleScore + employee.experienceScore +
           employee.productivityScore + employee.academicManagementScore;
}

Money salaryBase(const PayrollEmployee& employee) {
    if (employee.employeeType == "Professor") {
        if (employee.baseMonthlySalary > 0) return employee.baseMonthlySalary;
        if (employee.employmentType == "catedratico" && employee.hourlyRate > 0)
            return employee.hourlyRate * employee.hoursWorked;
        return roundPeso(totalPoints(employee) * static_cast<double>(employee.pointValue));
    }
    return employee.baseMonthlySalary;
}

PayrollResult calculatePayroll(
    const PayrollEmployee& employee,
    const PayrollPeriod& period,
    const PayrollRules& rules,
    const std::vector<PayrollNovelty>& novelties,
    Money otherDeductions) {
    validate(employee);
    validate(period);
    validate(rules);
    if (otherDeductions < 0) throw std::invalid_argument("otherDeductions cannot be negative");

    const Money base = salaryBase(employee);
    Money salaryAdjustments = 0;
    Money nonSalaryTotal = 0;
    Money nonSalaryIbcBase = 0;
    std::vector<PayrollLine> salaryConcepts{{"SALARY_BASE", base, true, true, "PayrollEngine", "SALARY_BASE"}};
    std::vector<PayrollLine> nonSalaryConcepts;

    for (const auto& novelty : novelties) {
        if (novelty.code.empty() || novelty.amount < 0 || novelty.quantity < 0)
            throw std::invalid_argument("invalid payroll novelty");
        const Money amount = multiply(novelty.amount, novelty.quantity);
        PayrollLine line{novelty.code, amount, novelty.isSalary, novelty.affectsIbc, "PayrollNovelty", novelty.code};
        if (novelty.isSalary) {
            salaryAdjustments += amount;
            salaryConcepts.push_back(line);
        } else {
            nonSalaryTotal += amount;
            if (novelty.affectsIbc) nonSalaryIbcBase += amount;
            nonSalaryConcepts.push_back(line);
        }
    }

    const Money constitutiveSalary = base + salaryAdjustments;
    const Money grossSalary = constitutiveSalary + nonSalaryTotal;
    const Money allowedNonSalary = roundPeso(static_cast<double>(grossSalary) * rules.nonSalaryLimit);
    const Money excessNonSalary = std::max<Money>(0, nonSalaryTotal - allowedNonSalary);
    const Money ibc = constitutiveSalary + nonSalaryIbcBase + excessNonSalary;

    const Money employeeHealth = roundPeso(static_cast<double>(ibc) * (rules.healthExempt ? 0.0 : rules.employeeHealthRate));
    const Money employeePension = roundPeso(static_cast<double>(ibc) * rules.employeePensionRate);
    const Money totalEmployeeDeductions = employeeHealth + employeePension + otherDeductions;

    const double adjustedBase = static_cast<double>(constitutiveSalary) * period.daysWorked / DAYS_IN_YEAR;
    const Money serviceBonusProvision = roundPeso(adjustedBase * rules.serviceBonusRate);
    const Money severanceProvision = roundPeso(adjustedBase * rules.severanceRate);
    const Money severanceInterest = roundPeso(static_cast<double>(severanceProvision) * period.daysWorked * rules.severanceInterestRate / DAYS_IN_YEAR);
    const Money christmasBonusProvision = roundPeso(adjustedBase * rules.christmasBonusRate);
    const Money vacationProvision = roundPeso(static_cast<double>(constitutiveSalary) * period.daysWorked * rules.vacationRate / rules.vacationDivisor);
    const Money vacationBonusProvision = roundPeso(adjustedBase * rules.vacationBonusRate);

    Money serviceBonus = 0;
    if (employee.continuousServiceDays >= rules.serviceBonusYearDays) {
        const double rate = employee.baseMonthlySalary <= rules.serviceBonusTop
            ? rules.serviceBonusRateBelowTop : rules.serviceBonusRateAboveTop;
        serviceBonus = roundPeso(static_cast<double>(employee.baseMonthlySalary) * rate);
    }

    const Money employerPension = roundPeso(static_cast<double>(ibc) * rules.employerPensionRate);
    const Money employerHealth = roundPeso(static_cast<double>(ibc) * (rules.healthExempt ? rules.employerHealthExemptRate : rules.employerHealthRate));
    const Money arl = roundPeso(static_cast<double>(ibc) * arlRate(rules));
    const Money compensationFund = roundPeso(static_cast<double>(ibc) * rules.compensationFundRate);
    const Money sena = roundPeso(static_cast<double>(ibc) * (rules.senaExempt ? rules.senaExemptRate : rules.senaRate));
    const Money icbf = roundPeso(static_cast<double>(ibc) * (rules.icbfExempt ? rules.icbfExemptRate : rules.icbfRate));
    const Money totalEmployerContributions = employerPension + employerHealth + arl + compensationFund + sena + icbf;
    const Money legalBenefits = serviceBonusProvision + severanceProvision + severanceInterest + christmasBonusProvision + vacationProvision + vacationBonusProvision;

    PayrollResult result;
    result.employeeId = employee.employeeId;
    result.employeeType = employee.employeeType;
    result.period = period.period;
    result.daysWorked = period.daysWorked;
    result.baseSalary = base;
    result.salaryAdjustments = salaryAdjustments;
    result.salaryConcepts = std::move(salaryConcepts);
    result.nonSalaryConcepts = std::move(nonSalaryConcepts);
    result.grossSalary = grossSalary;
    result.nonSalaryTotal = nonSalaryTotal;
    result.ibc = ibc;
    result.employeeHealth = employeeHealth;
    result.employeePension = employeePension;
    result.employeeOtherDeductions = otherDeductions;
    result.totalEmployeeDeductions = totalEmployeeDeductions;
    result.serviceBonusProvision = serviceBonusProvision;
    result.severanceProvision = severanceProvision;
    result.severanceInterest = severanceInterest;
    result.christmasBonusProvision = christmasBonusProvision;
    result.vacationProvision = vacationProvision;
    result.vacationBonusProvision = vacationBonusProvision;
    result.serviceBonus = serviceBonus;
    result.employerPension = employerPension;
    result.employerHealth = employerHealth;
    result.arl = arl;
    result.compensationFund = compensationFund;
    result.sena = sena;
    result.icbf = icbf;
    result.totalEmployerContributions = totalEmployerContributions;
    result.employerContributions = {
        {"EMPLOYER_PENSION", employerPension, rules.employerPensionRate},
        {"EMPLOYER_HEALTH", employerHealth, rules.healthExempt ? rules.employerHealthExemptRate : rules.employerHealthRate},
        {"ARL", arl, arlRate(rules)},
        {"COMPENSATION_FUND", compensationFund, rules.compensationFundRate},
        {"SENA", sena, rules.senaExempt ? rules.senaExemptRate : rules.senaRate},
        {"ICBF", icbf, rules.icbfExempt ? rules.icbfExemptRate : rules.icbfRate},
    };
    result.netSalary = grossSalary + serviceBonus - totalEmployeeDeductions;
    result.totalEmployerCost = grossSalary + serviceBonus + legalBenefits + totalEmployerContributions;
    result.calculationTrace = {
        "netSalary=grossSalary+serviceBonus-totalEmployeeDeductions",
        "ibc=constitutiveSalary+nonSalaryIbcBase+excessNonSalaryOver40Percent",
        "totalEmployerCost=grossSalary+serviceBonus+legalBenefits+totalEmployerContributions",
    };
    return result;
}

Payslip generatePayslip(
    const PayrollEmployee& employee,
    const PayrollPeriod& period,
    const PayrollResult& result,
    const PayrollConfiguration& configuration,
    const std::string& runId) {
    validate(employee);
    validate(period);
    if (result.employeeId != employee.employeeId || result.period != period.period)
        throw std::invalid_argument("PayrollResult does not belong to employee and period");
    Payslip payslip;
    payslip.payslipId = "PS-" + employee.employeeId + "-" + period.period;
    payslip.runId = runId;
    payslip.periodId = period.period;
    payslip.liquidationDate = timestamp();
    payslip.institution = configuration;
    payslip.employee = employee;
    payslip.result = result;
    payslip.arlRiskClass = "I";
    payslip.traceId = runId + ":" + employee.employeeId;
    return payslip;
}

}  // namespace pita::payroll
