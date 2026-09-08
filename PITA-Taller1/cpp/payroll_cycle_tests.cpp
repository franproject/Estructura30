#include "payroll_cycle.hpp"

#include <cassert>
#include <sstream>
#include <stdexcept>

using namespace pita::payroll;

int main() {
    PayrollCycle cycle;
    const PayrollPeriodRecord period = cycle.createPeriod(
        "2026-09", 2026, 9, "2026-09-01", "2026-09-30", "user-1");

    PayrollNoveltyRecord novelty;
    novelty.noveltyId = "N-1";
    novelty.periodId = period.periodId;
    novelty.employeeId = "A1";
    novelty.type = NoveltyType::BONUS;
    novelty.startDate = "2026-09-01";
    novelty.amount = 100000;
    novelty.isSalary = false;
    novelty.affectsIbc = false;
    novelty.status = "APPROVED";
    cycle.registerNovelty(novelty);

    PayrollEmployee employee;
    employee.employeeId = "A1";
    employee.employeeType = "Administrative";
    employee.employmentType = "planta";
    employee.baseMonthlySalary = 1000000;
    employee.active = true;

    const PayrollRunRecord run = cycle.calculateRun(period.periodId, {employee}, PayrollRules{}, "user-1");
    assert(run.employeeIds.size() == 1);
    assert(run.details.size() == 1);
    cycle.approveRun(run.runId, "user-1");
    cycle.closeRun(run.runId, "user-1");
    assert(cycle.periods().front().status == PeriodStatus::CLOSED);

    bool rejected = false;
    try {
        cycle.calculateRun(period.periodId, {employee}, PayrollRules{}, "user-1");
    } catch (const std::invalid_argument&) {
        rejected = true;
    }
    assert(rejected);
    assert(cycle.audits().size() >= 4);

    std::stringstream serialized;
    savePayrollCycleSections(serialized, cycle);
    PayrollCycle loaded;
    loadPayrollCycleSections(serialized, loaded);
    assert(loaded.periods().size() == 1);
    assert(loaded.runs().size() == 1);
    assert(loaded.runs().front().details.size() == 1);
    assert(loaded.runs().front().details.front().employeeHealth == run.details.front().employeeHealth);
    assert(!loaded.runs().front().details.front().salaryConcepts.empty());
    assert(!loaded.runs().front().details.front().calculationTrace.empty());
    assert(loaded.novelties().size() == 1);
    assert(loaded.audits().size() >= 4);
    return 0;
}
