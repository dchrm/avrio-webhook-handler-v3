from task_functions.update_work_schedules import does_date_recur
from datetime import datetime

if __name__ == "__main__":
    start_date = datetime(2024, 1, 1)
    interval_type = 'years' # Options: 'days', 'weeks', 'months', 'years'
    interval_value = 1  # Every other week
    check_date = datetime(2025, 1, 2)

    is_recurring = does_date_recur(start_date,interval_type,interval_value,check_date)

    print("Does the date recur:", is_recurring)