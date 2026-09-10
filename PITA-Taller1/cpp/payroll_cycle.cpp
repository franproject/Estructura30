#include "payroll_cycle.hpp"

#include <algorithm>
#include <ctime>
#include <ostream>
#include <istream>
#include <sstream>
#include <stdexcept>
#include <iomanip>
#include <cstdio>

namespace pita::payroll {
namespace {

std::vector<std::string> split(const std::string& line, char separator) {
    std::vector<std::string> values;
    std::stringstream stream(line);
    std::string value;
    while (std::getline(stream, value, separator)) values.push_back(value);
    return values;
}

std::string now() {
    const std::time_t current = std::time(nullptr);
    char buffer[32]{};
    std::tm local{};
    const std::tm* localTime = std::localtime(&current);
    if (localTime != nullptr) local = *localTime;
    std::strftime(buffer, sizeof(buffer), "%Y-%m-%dT%H:%M:%S", &local);
    return buffer;
}

bool formulaDefined(NoveltyType type, Money amount) {
    const bool amountType = type == NoveltyType::BONUS || type == NoveltyType::DISCOUNT ||
        type == NoveltyType::GARNISHMENT || type == NoveltyType::ADVANCE ||
        type == NoveltyType::SALARY_ADJUSTMENT;
    return amountType && amount >= 0;
}

int daysBetween(const std::string& startDate, const std::string& endDate) {
    std::tm start{};
    std::tm end{};
    char separator1 = 0;
    char separator2 = 0;
    char separator3 = 0;
    char separator4 = 0;
    std::istringstream startStream(startDate);
    std::istringstream endStream(endDate);
    int startYear = 0, startMonth = 0, startDay = 0;
    int endYear = 0, endMonth = 0, endDay = 0;
    if (!(startStream >> startYear >> separator1 >> startMonth >> separator2 >> startDay) ||
        !(endStream >> endYear >> separator3 >> endMonth >> separator4 >> endDay) ||
        separator1 != '-' || separator2 != '-' || separator3 != '-' || separator4 != '-') {
        throw std::invalid_argument("payroll dates must use YYYY-MM-DD");
    }
    auto validCalendarDate = [](int year, int month, int day) {
        if (year < 2000 || month < 1 || month > 12 || day < 1 || day > 31) return false;
        std::tm value{};
        value.tm_year = year - 1900;
        value.tm_mon = month - 1;
        value.tm_mday = day;
        const std::time_t timestamp = std::mktime(&value);
        if (timestamp == static_cast<std::time_t>(-1)) return false;
        std::tm normalized{};
        const std::tm* localTime = std::localtime(&timestamp);
        if (localTime != nullptr) normalized = *localTime;
        return normalized.tm_year == year - 1900 && normalized.tm_mon == month - 1 && normalized.tm_mday == day;
    };
    if (!validCalendarDate(startYear, startMonth, startDay) ||
        !validCalendarDate(endYear, endMonth, endDay))
        throw std::invalid_argument("invalid payroll calendar date");
    start.tm_year = startYear - 1900;
    start.tm_mon = startMonth - 1;
    start.tm_mday = startDay;
    end.tm_year = endYear - 1900;
    end.tm_mon = endMonth - 1;
    end.tm_mday = endDay;
    const std::time_t startTime = std::mktime(&start);
    const std::time_t endTime = std::mktime(&end);
    if (startTime == static_cast<std::time_t>(-1) || endTime < startTime)
        throw std::invalid_argument("invalid payroll date range");
    return static_cast<int>(std::difftime(endTime, startTime) / (60 * 60 * 24)) + 1;
}

int effectiveDays(const PayrollPeriodRecord& period, const PayrollEmployee& employee) {
    std::string start = period.startDate;
    std::string end = period.endDate;
    if (!employee.hireDate.empty() && employee.hireDate > start) start = employee.hireDate;
    if (!employee.terminationDate.empty() && employee.terminationDate < end) end = employee.terminationDate;
    const int calendarDays = start > end ? 0 : daysBetween(start, end);
    const int workedDays = employee.workedDays > 0 ? employee.workedDays : calendarDays;
    return std::min(workedDays, calendarDays);
}

}  // namespace

PayrollPeriodRecord PayrollCycle::createPeriod(
    const std::string& periodId, int year, int month,
    const std::string& startDate, const std::string& endDate,
    const std::string& responsibleUser) {
    if (periodId.empty() || year < 2000 || month < 1 || month > 12)
        throw std::invalid_argument("invalid payroll period");
    const int periodDays = daysBetween(startDate, endDate);
    if (periodDays <= 0 || periodDays > 360)
        throw std::invalid_argument("payroll period must contain between 1 and 360 days");
    for (const auto& period : periods_) {
        if (period.year == year && period.month == month && period.status != PeriodStatus::CANCELLED)
            throw std::invalid_argument("payroll period already exists");
    }
    PayrollPeriodRecord period{periodId, year, month, startDate, endDate, PeriodStatus::OPEN, now(), "", responsibleUser};
    periods_.push_back(period);
    audit("PayrollPeriod", periodId, "CREATE", responsibleUser);
    return period;
}

void PayrollCycle::registerNovelty(const PayrollNoveltyRecord& novelty) {
    if (novelty.noveltyId.empty() || novelty.periodId.empty() || novelty.employeeId.empty())
        throw std::invalid_argument("novelty identifiers are required");
    PayrollPeriodRecord* period = findPeriod(novelty.periodId);
    if (period == nullptr || period->status == PeriodStatus::CLOSED || period->status == PeriodStatus::CANCELLED)
        throw std::invalid_argument("novelty cannot be added to this period");
    PayrollNoveltyRecord stored = novelty;
    stored.formulaDefined = formulaDefined(stored.type, stored.amount);
    novelties_.push_back(stored);
    audit("PayrollNovelty", stored.noveltyId, "CREATE", stored.createdBy);
}

PayrollRunRecord PayrollCycle::calculateRun(
    const std::string& periodId, const std::vector<PayrollEmployee>& employees,
    const PayrollRules& rules, const std::string& actor, bool allowExisting) {
    PayrollPeriodRecord* period = findPeriod(periodId);
    if (period == nullptr || (period->status != PeriodStatus::OPEN && !allowExisting))
        throw std::invalid_argument("only open periods can be calculated");
    for (const auto& existing : runs_) {
        if (!allowExisting && existing.periodId == periodId && existing.status != RunStatus::CANCELLED)
            throw std::invalid_argument("payroll run already exists for this period");
    }
    PayrollRunRecord run;
    run.runId = "RUN-" + std::to_string(runs_.size() + 1);
    run.periodId = periodId;
    run.executedAt = now();
    run.createdAt = run.executedAt;
    run.calculatedAt = run.executedAt;
    run.calculatedBy = actor;
    for (const auto& employee : employees) {
        if (!employee.active) continue;
        const std::string employeeId = employee.employeeId;
        std::vector<PayrollNovelty> engineNovelties;
        for (const auto& novelty : novelties_) {
            if (novelty.periodId != periodId || novelty.employeeId != employeeId) continue;
            if (!novelty.formulaDefined)
                throw std::invalid_argument("novelty has no defined formula");
            run.noveltyIds.push_back(novelty.noveltyId);
            PayrollNovelty engineNovelty;
            engineNovelty.code = "NOVELTY_" + novelty.noveltyId;
            engineNovelty.amount = novelty.amount;
            engineNovelty.quantity = novelty.quantity;
            engineNovelty.isSalary = novelty.isSalary;
            engineNovelty.affectsIbc = novelty.affectsIbc;
            engineNovelties.push_back(engineNovelty);
        }
        const PayrollResult result = calculatePayroll(employee, PayrollPeriod{periodId, effectiveDays(*period, employee), period->year, period->month, period->startDate, period->endDate, "OPEN"}, rules, engineNovelties);
        run.employeeIds.push_back(employeeId);
        run.details.push_back(result);
        run.grossTotal += result.grossSalary;
        run.employeeDeductionTotal += result.totalEmployeeDeductions;
        run.employerContributionTotal += result.totalEmployerContributions;
        run.netTotal += result.netSalary;
        run.employerCost += result.totalEmployerCost;
    }
    if (run.details.empty())
        throw std::invalid_argument("there are no active employees to liquidate");
    period->status = PeriodStatus::CALCULATED;
    runs_.push_back(run);
    audit("PayrollRun", run.runId, "CALCULATE", actor);
    runs_.back().auditIds.push_back(audits_.back().auditId);
    return runs_.back();
}

PayrollRunRecord PayrollCycle::createCorrectionRun(
    const std::string& periodId, const std::vector<PayrollEmployee>& employees,
    const PayrollRules& rules, const std::string& actor, const std::string& reason) {
    PayrollPeriodRecord* period = findPeriod(periodId);
    if (period == nullptr) throw std::invalid_argument("payroll period does not exist");
    PayrollRunRecord* previous = nullptr;
    for (auto& candidate : runs_) {
        if (candidate.periodId == periodId) previous = &candidate;
    }
    if (previous == nullptr) throw std::invalid_argument("there is no prior payroll run to correct");
    const std::string previousRunId = previous->runId;
    const PeriodStatus originalStatus = period->status;
    period->status = PeriodStatus::OPEN;
    PayrollRunRecord corrected;
    try {
        corrected = calculateRun(periodId, employees, rules, actor, true);
    } catch (...) {
        period->status = originalStatus;
        throw;
    }
    period->status = originalStatus;
    corrected.revisionOf = previousRunId;
    audit("PayrollRun", corrected.runId, "CORRECT", actor, reason);
    runs_.back().revisionOf = previousRunId;
    runs_.back().auditIds.push_back(audits_.back().auditId);
    return runs_.back();
}

void PayrollCycle::approveRun(const std::string& runId, const std::string& actor) {
    PayrollRunRecord* run = findRun(runId);
    if (run == nullptr || run->status != RunStatus::CALCULATED)
        throw std::invalid_argument("only calculated runs can be approved");
    PayrollPeriodRecord* period = findPeriod(run->periodId);
    if (period == nullptr || period->status != PeriodStatus::CALCULATED)
        throw std::invalid_argument("period must be calculated before approval");
    run->status = RunStatus::APPROVED;
    run->approvedAt = now();
    run->approvedBy = actor;
    period->status = PeriodStatus::APPROVED;
    audit("PayrollRun", runId, "APPROVE", actor);
    run->auditIds.push_back(audits_.back().auditId);
}

void PayrollCycle::closeRun(const std::string& runId, const std::string& actor) {
    PayrollRunRecord* run = findRun(runId);
    if (run == nullptr || run->status != RunStatus::APPROVED)
        throw std::invalid_argument("only approved runs can be closed");
    PayrollPeriodRecord* period = findPeriod(run->periodId);
    if (period == nullptr) throw std::invalid_argument("period does not exist");
    run->status = RunStatus::CLOSED;
    run->closedAt = now();
    run->closedBy = actor;
    period->status = PeriodStatus::CLOSED;
    period->closedAt = now();
    audit("PayrollRun", runId, "CLOSE", actor);
    run->auditIds.push_back(audits_.back().auditId);
}

PayrollPeriodRecord* PayrollCycle::findPeriod(const std::string& periodId) {
    const auto iterator = std::find_if(periods_.begin(), periods_.end(), [&](const auto& item) { return item.periodId == periodId; });
    return iterator == periods_.end() ? nullptr : &*iterator;
}

PayrollRunRecord* PayrollCycle::findRun(const std::string& runId) {
    const auto iterator = std::find_if(runs_.begin(), runs_.end(), [&](const auto& item) { return item.runId == runId; });
    return iterator == runs_.end() ? nullptr : &*iterator;
}

void PayrollCycle::audit(const std::string& entityType, const std::string& entityId,
                         const std::string& action, const std::string& actor,
                         const std::string& reason) {
    audits_.push_back({"AUD-" + std::to_string(audits_.size() + 1), entityType, entityId,
                       action, now(), actor, reason, "TRACE-" + std::to_string(audits_.size() + 1)});
}

void PayrollCycle::clear() {
    periods_.clear();
    runs_.clear();
    novelties_.clear();
    audits_.clear();
}

void savePayrollCycleSections(std::ostream& output, const PayrollCycle& cycle) {
    output << "#PAYROLL_PERIODS\n";
    for (const auto& period : cycle.periods()) {
        output << period.periodId << '|' << period.year << '|' << period.month << '|'
               << period.startDate << '|' << period.endDate << '|' << static_cast<int>(period.status)
               << '|' << period.createdAt << '|' << period.closedAt << '|' << period.responsibleUser << '\n';
    }
    output << "#FIN_PAYROLL_PERIODS\n#PAYROLL_NOVELTIES\n";
    for (const auto& novelty : cycle.novelties()) {
        output << novelty.noveltyId << '|' << novelty.periodId << '|' << novelty.employeeId << '|'
               << static_cast<int>(novelty.type) << '|' << novelty.startDate << '|' << novelty.endDate << '|'
               << novelty.quantity << '|' << novelty.amount << '|' << novelty.status << '|'
               << novelty.formulaDefined << '|' << novelty.isSalary << '|' << novelty.affectsIbc << '\n';
    }
    output << "#FIN_PAYROLL_NOVELTIES\n#PAYROLL_RUNS\n";
    for (const auto& run : cycle.runs()) {
        output << run.runId << '|' << run.periodId << '|' << static_cast<int>(run.status) << '|'
               << run.executedAt << '|' << run.grossTotal << '|' << run.employeeDeductionTotal << '|'
               << run.employerContributionTotal << '|' << run.netTotal << '|' << run.employerCost << '|';
        for (std::size_t index = 0; index < run.employeeIds.size(); ++index) {
            if (index > 0) output << ',';
            output << run.employeeIds[index];
        }
        output << '|' << run.createdAt << '|' << run.calculatedAt << '|' << run.calculatedBy
               << '|' << run.approvedAt << '|' << run.approvedBy << '|' << run.closedAt
               << '|' << run.closedBy << '|' << run.revisionOf << '|';
        for (std::size_t index = 0; index < run.noveltyIds.size(); ++index) {
            if (index > 0) output << ',';
            output << run.noveltyIds[index];
        }
        output << '\n';
        for (const auto& detail : run.details) {
            output << "DETAIL|" << run.runId << '|' << detail.employeeId << '|' << detail.employeeType << '|'
                   << detail.period << '|' << detail.daysWorked << '|' << detail.baseSalary << '|'
                   << detail.grossSalary << '|' << detail.ibc << '|' << detail.totalEmployeeDeductions << '|'
                   << detail.netSalary << '|' << detail.totalEmployerContributions << '|'
                   << detail.totalEmployerCost << '|' << detail.salaryAdjustments << '|'
                   << detail.nonSalaryTotal << '|' << detail.employeeHealth << '|'
                   << detail.employeePension << '|' << detail.employeeOtherDeductions << '|'
                   << detail.serviceBonusProvision << '|' << detail.severanceProvision << '|'
                   << detail.severanceInterest << '|' << detail.christmasBonusProvision << '|'
                   << detail.vacationProvision << '|' << detail.vacationBonusProvision << '|'
                   << detail.serviceBonus << '|' << detail.employerPension << '|'
                   << detail.employerHealth << '|' << detail.arl << '|'
                   << detail.compensationFund << '|' << detail.sena << '|' << detail.icbf << '\n';
            for (const auto& concepto : detail.salaryConcepts) {
                output << "CONCEPT|" << run.runId << '|' << detail.employeeId << "|S|"
                       << concepto.code << '|' << concepto.amount << '|' << concepto.isSalary << '|'
                       << concepto.affectsIbc << '|' << concepto.origin << '|' << concepto.sourceId << '\n';
            }
            for (const auto& concepto : detail.nonSalaryConcepts) {
                output << "CONCEPT|" << run.runId << '|' << detail.employeeId << "|N|"
                       << concepto.code << '|' << concepto.amount << '|' << concepto.isSalary << '|'
                       << concepto.affectsIbc << '|' << concepto.origin << '|' << concepto.sourceId << '\n';
            }
            for (const auto& trace : detail.calculationTrace)
                output << "TRACE|" << run.runId << '|' << detail.employeeId << '|' << trace << '\n';
        }
    }
    output << "#FIN_PAYROLL_RUNS\n#PAYROLL_AUDIT\n";
    for (const auto& audit : cycle.audits()) {
        output << audit.auditId << '|' << audit.entityType << '|' << audit.entityId << '|'
               << audit.action << '|' << audit.timestamp << '|' << audit.actor << '|' << audit.traceId << '\n';
    }
    output << "#FIN_PAYROLL_AUDIT\n";
}

// Constantes de tamano minimo de campos por seccion
constexpr int PAYROLL_SECTION_MIN_FIELDS_PERIODS             = 9;
constexpr int PAYROLL_SECTION_MIN_FIELDS_NOVELTIES           = 12;
constexpr int PAYROLL_SECTION_MIN_FIELDS_RUN_CONCEPT         = 10;
constexpr int PAYROLL_SECTION_MIN_FIELDS_RUN_TRACE           = 4;
constexpr int PAYROLL_SECTION_MIN_FIELDS_RUN_DETAIL          = 13;
constexpr int PAYROLL_SECTION_MIN_FIELDS_RUN_DETAIL_EXTENDED = 31;
constexpr int PAYROLL_SECTION_MIN_FIELDS_RUNS                = 10;
constexpr int PAYROLL_SECTION_MIN_FIELDS_RUNS_EXTENDED       = 19;
constexpr int PAYROLL_SECTION_MIN_FIELDS_AUDIT               = 7;

void loadPayrollCycleSections(std::istream& input, PayrollCycle& cycle) {
    cycle.clear();
    std::string line;
    std::string section;
    PayrollRunRecord* currentRun = nullptr;
    while (std::getline(input, line)) {
        if (line.empty()) continue;
        if (line.front() == '#') {
            section = line;
            currentRun = nullptr;
            continue;
        }
        const auto fields = split(line, '|');
        try {
            if (section == "#PAYROLL_PERIODS" && static_cast<int>(fields.size()) >= PAYROLL_SECTION_MIN_FIELDS_PERIODS) {
                cycle.periods_.push_back({fields[0], std::stoi(fields[1]), std::stoi(fields[2]), fields[3], fields[4],
                    static_cast<PeriodStatus>(std::stoi(fields[5])), fields[6], fields[7], fields[8]});
            } else if (section == "#PAYROLL_NOVELTIES" && static_cast<int>(fields.size()) >= PAYROLL_SECTION_MIN_FIELDS_NOVELTIES) {
                cycle.novelties_.push_back({fields[0], fields[1], fields[2], static_cast<NoveltyType>(std::stoi(fields[3])),
                    fields[4], fields[5], std::stoll(fields[6]), std::stoll(fields[7]), "", fields[8], "",
                    std::stoi(fields[9]) != 0, std::stoi(fields[10]) != 0, std::stoi(fields[11]) != 0});
            } else if (section == "#PAYROLL_RUNS" && static_cast<int>(fields.size()) >= PAYROLL_SECTION_MIN_FIELDS_RUN_CONCEPT && fields[0] == "CONCEPT") {
                if (currentRun == nullptr) continue;
                auto detail = std::find_if(currentRun->details.begin(), currentRun->details.end(),
                    [&](const auto& item) { return item.employeeId == fields[2]; });
                if (detail == currentRun->details.end() || static_cast<int>(fields.size()) < PAYROLL_SECTION_MIN_FIELDS_RUN_CONCEPT) continue;
                PayrollLine concepto{fields[4], std::stoll(fields[5]), std::stoi(fields[6]) != 0,
                    std::stoi(fields[7]) != 0, fields[8], fields[9]};
                (fields[3] == "S" ? detail->salaryConcepts : detail->nonSalaryConcepts).push_back(concepto);
            } else if (section == "#PAYROLL_RUNS" && static_cast<int>(fields.size()) >= PAYROLL_SECTION_MIN_FIELDS_RUN_TRACE && fields[0] == "TRACE") {
                if (currentRun == nullptr) continue;
                auto detail = std::find_if(currentRun->details.begin(), currentRun->details.end(),
                    [&](const auto& item) { return item.employeeId == fields[2]; });
                if (detail != currentRun->details.end()) detail->calculationTrace.push_back(fields[3]);
            } else if (section == "#PAYROLL_RUNS" && static_cast<int>(fields.size()) >= PAYROLL_SECTION_MIN_FIELDS_RUN_DETAIL && fields[0] == "DETAIL") {
                if (currentRun == nullptr) continue;
                PayrollResult detail;
                detail.employeeId = fields[2];
                detail.employeeType = fields[3];
                detail.period = fields[4];
                detail.daysWorked = std::stoi(fields[5]);
                detail.baseSalary = std::stoll(fields[6]);
                detail.grossSalary = std::stoll(fields[7]);
                detail.ibc = std::stoll(fields[8]);
                detail.totalEmployeeDeductions = std::stoll(fields[9]);
                detail.netSalary = std::stoll(fields[10]);
                detail.totalEmployerContributions = std::stoll(fields[11]);
                detail.totalEmployerCost = std::stoll(fields[12]);
                if (static_cast<int>(fields.size()) >= PAYROLL_SECTION_MIN_FIELDS_RUN_DETAIL_EXTENDED) {
                    detail.salaryAdjustments = std::stoll(fields[13]);
                    detail.nonSalaryTotal = std::stoll(fields[14]);
                    detail.employeeHealth = std::stoll(fields[15]);
                    detail.employeePension = std::stoll(fields[16]);
                    detail.employeeOtherDeductions = std::stoll(fields[17]);
                    detail.serviceBonusProvision = std::stoll(fields[18]);
                    detail.severanceProvision = std::stoll(fields[19]);
                    detail.severanceInterest = std::stoll(fields[20]);
                    detail.christmasBonusProvision = std::stoll(fields[21]);
                    detail.vacationProvision = std::stoll(fields[22]);
                    detail.vacationBonusProvision = std::stoll(fields[23]);
                    detail.serviceBonus = std::stoll(fields[24]);
                    detail.employerPension = std::stoll(fields[25]);
                    detail.employerHealth = std::stoll(fields[26]);
                    detail.arl = std::stoll(fields[27]);
                    detail.compensationFund = std::stoll(fields[28]);
                    detail.sena = std::stoll(fields[29]);
                    detail.icbf = std::stoll(fields[30]);
                }
                currentRun->details.push_back(detail);
            } else if (section == "#PAYROLL_RUNS" && static_cast<int>(fields.size()) >= PAYROLL_SECTION_MIN_FIELDS_RUNS) {
                PayrollRunRecord run;
                run.runId = fields[0];
                run.periodId = fields[1];
                run.status = static_cast<RunStatus>(std::stoi(fields[2]));
                run.executedAt = fields[3];
                run.grossTotal = std::stoll(fields[4]);
                run.employeeDeductionTotal = std::stoll(fields[5]);
                run.employerContributionTotal = std::stoll(fields[6]);
                run.netTotal = std::stoll(fields[7]);
                run.employerCost = std::stoll(fields[8]);
                for (const auto& employeeId : split(fields[9], ',')) {
                    if (!employeeId.empty()) run.employeeIds.push_back(employeeId);
                }
                if (static_cast<int>(fields.size()) >= PAYROLL_SECTION_MIN_FIELDS_RUNS_EXTENDED) {
                    run.createdAt = fields[10];
                    run.calculatedAt = fields[11];
                    run.calculatedBy = fields[12];
                    run.approvedAt = fields[13];
                    run.approvedBy = fields[14];
                    run.closedAt = fields[15];
                    run.closedBy = fields[16];
                    run.revisionOf = fields[17];
                    for (const auto& noveltyId : split(fields[18], ',')) {
                        if (!noveltyId.empty()) run.noveltyIds.push_back(noveltyId);
                    }
                }
                cycle.runs_.push_back(run);
                currentRun = &cycle.runs_.back();
            } else if (section == "#PAYROLL_AUDIT" && static_cast<int>(fields.size()) >= PAYROLL_SECTION_MIN_FIELDS_AUDIT) {
                cycle.audits_.push_back({fields[0], fields[1], fields[2], fields[3], fields[4], fields[5], "", fields[6]});
            }
        } catch (const std::exception&) {
            // Ignore malformed formal records while preserving the legacy file load.
        }
    }
}

}  // namespace pita::payroll
