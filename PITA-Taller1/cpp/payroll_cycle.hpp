#ifndef PITA_PAYROLL_CYCLE_HPP
#define PITA_PAYROLL_CYCLE_HPP

#include "payroll_engine.hpp"

#include <iosfwd>
#include <string>
#include <vector>

namespace pita::payroll {

enum class PeriodStatus { OPEN, CALCULATED, APPROVED, CLOSED, CANCELLED };
enum class RunStatus { CALCULATED, APPROVED, CLOSED, CANCELLED };

enum class NoveltyType {
    INCOME, TERMINATION, INCAPACITY, LICENSE, VACATION, ABSENCE,
    ADDITIONAL_HOURS, BONUS, DISCOUNT, GARNISHMENT, ADVANCE, SALARY_ADJUSTMENT
};

struct PayrollNoveltyRecord {
    std::string noveltyId;
    std::string periodId;
    std::string employeeId;
    NoveltyType type = NoveltyType::BONUS;
    std::string startDate;
    std::string endDate;
    Money quantity = 1;
    Money amount = 0;
    std::string description;
    std::string status = "DRAFT";
    std::string createdBy;
    bool formulaDefined = false;
    bool isSalary = true;
    bool affectsIbc = true;
};

struct PayrollPeriodRecord {
    std::string periodId;
    int year = 0;
    int month = 0;
    std::string startDate;
    std::string endDate;
    PeriodStatus status = PeriodStatus::OPEN;
    std::string createdAt;
    std::string closedAt;
    std::string responsibleUser;
};

struct PayrollAuditRecord {
    std::string auditId;
    std::string entityType;
    std::string entityId;
    std::string action;
    std::string timestamp;
    std::string actor;
    std::string reason;
    std::string traceId;
};

struct PayrollRunRecord {
    std::string runId;
    std::string periodId;
    std::vector<std::string> employeeIds;
    std::vector<PayrollResult> details;
    Money grossTotal = 0;
    Money employeeDeductionTotal = 0;
    Money employerContributionTotal = 0;
    Money netTotal = 0;
    Money employerCost = 0;
    RunStatus status = RunStatus::CALCULATED;
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

class PayrollCycle {
public:
    PayrollPeriodRecord createPeriod(
        const std::string& periodId, int year, int month,
        const std::string& startDate, const std::string& endDate,
        const std::string& responsibleUser = "");

    void registerNovelty(const PayrollNoveltyRecord& novelty);
    PayrollRunRecord calculateRun(
        const std::string& periodId,
        const std::vector<PayrollEmployee>& employees,
        const PayrollRules& rules,
        const std::string& actor = "",
        bool allowExisting = false);
    PayrollRunRecord createCorrectionRun(
        const std::string& periodId,
        const std::vector<PayrollEmployee>& employees,
        const PayrollRules& rules,
        const std::string& actor = "",
        const std::string& reason = "");
    void approveRun(const std::string& runId, const std::string& actor = "");
    void closeRun(const std::string& runId, const std::string& actor = "");

    const std::vector<PayrollPeriodRecord>& periods() const { return periods_; }
    const std::vector<PayrollRunRecord>& runs() const { return runs_; }
    const std::vector<PayrollNoveltyRecord>& novelties() const { return novelties_; }
    const std::vector<PayrollAuditRecord>& audits() const { return audits_; }
    void clear();

private:
    friend void loadPayrollCycleSections(std::istream& input, PayrollCycle& cycle);
    PayrollPeriodRecord* findPeriod(const std::string& periodId);
    PayrollRunRecord* findRun(const std::string& runId);
    void audit(const std::string& entityType, const std::string& entityId,
               const std::string& action, const std::string& actor,
               const std::string& reason = "");

    std::vector<PayrollPeriodRecord> periods_;
    std::vector<PayrollRunRecord> runs_;
    std::vector<PayrollNoveltyRecord> novelties_;
    std::vector<PayrollAuditRecord> audits_;
};

void savePayrollCycleSections(std::ostream& output, const PayrollCycle& cycle);
void loadPayrollCycleSections(std::istream& input, PayrollCycle& cycle);

}  // namespace pita::payroll

#endif
