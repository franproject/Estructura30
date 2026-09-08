"""Payroll model.

The payroll acts as a calculator that receives a Professor or an Administrative
and computes their salary without duplicating all of the same fields in both entities.

The rule is kept configurable in this module so the salary logic remains easy to
modify without scattering hard-coded literals across the application.
"""


class Payroll:
    """Base class for handling payroll calculations."""

    PAYROLL_RULES = {
        "professor_point_components": (
            "category_score",
            "title_score",
            "experience_score",
            "productivity_score",
            "academic_management_score",
        ),
        "professor_deduction_components": (
            "health_discount",
            "pension_discount",
        ),
        "professor_benefit_components": (
            "severance_provision",
            "bonus_provision",
            "vacation_provision",
        ),
        "administrative_deduction_components": (
            "health_discount",
            "pension_discount",
        ),
        "administrative_benefit_components": (
            "severance_provision",
            "holiday_bonus",
            "vacation_provision",
        ),
    }

    def __init__(self, description=""):
        self.description = description
        self.validate()

    def validate(self):
        if not isinstance(self.description, str):
            raise TypeError("description must be a string")
        return True

    def _sum_numeric_fields(self, employee, field_names):
        total = 0.0
        for field_name in field_names:
            if hasattr(employee, field_name):
                value = getattr(employee, field_name)
                if isinstance(value, (int, float)):
                    total += float(value)
        return total

    def calculateProfessorPoints(self, professor):
        """Sums the configured academic scoring components for the professor."""
        if professor is None:
            raise ValueError("professor cannot be null")
        points = self._sum_numeric_fields(professor, self.PAYROLL_RULES["professor_point_components"])
        professor.total_points = points
        return float(points)

    def calculateProfessorSalary(self, professor):
        """Uses the salary already stored in the model when present; otherwise falls back to points × point value."""
        if professor is None:
            raise ValueError("professor cannot be null")
        if isinstance(professor.base_monthly_salary, (int, float)) and float(professor.base_monthly_salary) > 0:
            return float(professor.base_monthly_salary)
        if isinstance(professor.point_value, (int, float)) and float(professor.point_value) > 0:
            return float(self.calculateProfessorPoints(professor) * professor.point_value)
        return 0.0

    def calculateAdministrativeSalary(self, administrative):
        """Returns the base monthly salary stored in the administrative record."""
        if administrative is None:
            raise ValueError("administrative cannot be null")
        if isinstance(administrative.base_salary, (int, float)):
            return float(administrative.base_salary)
        return 0.0

    def calculateDeductions(self, employee):
        """Returns the configured deduction amount for the employee."""
        if employee is None:
            raise ValueError("employee cannot be null")
        if hasattr(employee, "health_discount") or hasattr(employee, "pension_discount"):
            if hasattr(employee, "health_discount") and hasattr(employee, "pension_discount"):
                return float(employee.health_discount) + float(employee.pension_discount)
        return 0.0

    def calculateBenefits(self, employee):
        """Returns the configured benefit amount for the employee."""
        if employee is None:
            raise ValueError("employee cannot be null")
        if hasattr(employee, "severance_provision") or hasattr(employee, "bonus_provision") or hasattr(employee, "vacation_provision") or hasattr(employee, "holiday_bonus"):
            components = []
            if hasattr(employee, "severance_provision"):
                components.append("severance_provision")
            if hasattr(employee, "bonus_provision"):
                components.append("bonus_provision")
            if hasattr(employee, "vacation_provision"):
                components.append("vacation_provision")
            if hasattr(employee, "holiday_bonus"):
                components.append("holiday_bonus")
            return self._sum_numeric_fields(employee, tuple(components))
        return 0.0

    def generatePayrollReport(self, employee):
        """Generates a salary breakdown report for either a professor or an administrative employee."""
        if employee is None:
            raise ValueError("employee cannot be null")

        if hasattr(employee, "category_score"):
            points = self.calculateProfessorPoints(employee)
            base_salary = self.calculateProfessorSalary(employee)
            deductions = self.calculateDeductions(employee)
            benefits = self.calculateBenefits(employee)
            net_salary = base_salary - deductions + benefits
            return {
                "employee_type": "Professor",
                "employee_id": getattr(employee, "professor_id", 0),
                "points": points,
                "base_salary": base_salary,
                "deductions": deductions,
                "benefits": benefits,
                "net_salary": net_salary,
            }

        if hasattr(employee, "base_salary"):
            base_salary = self.calculateAdministrativeSalary(employee)
            deductions = self.calculateDeductions(employee)
            benefits = self.calculateBenefits(employee)
            net_salary = base_salary - deductions + benefits
            return {
                "employee_type": "Administrative",
                "employee_id": getattr(employee, "administrative_id", 0),
                "points": 0.0,
                "base_salary": base_salary,
                "deductions": deductions,
                "benefits": benefits,
                "net_salary": net_salary,
            }

        raise TypeError("Unsupported employee type for payroll calculation")

    def generate_payroll_report(self, employee):
        """Pythonic alias for the payroll report generator."""
        return self.generatePayrollReport(employee)

    def to_dict(self):
        return {"description": self.description}

    @classmethod
    def from_dict(cls, data):
        if data is None:
            raise ValueError("Payroll data cannot be null")
        return cls(description=data.get("description", ""))
