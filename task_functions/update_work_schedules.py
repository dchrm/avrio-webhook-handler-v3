import logging
from services.karbon_services import Entities
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from typing import Literal

# Udpate work schedule
def update_work_schedule(bearer_token: str, access_key: str, work_item_data: dict):
    """
    Takes a work item, checks to see if it has a work schedule, 
    then updates the work schedule if the work item start date has changed.
    """
    work_schedule_key = work_item_data["WorkScheduleKey"]

    # if there is no work schedule key for the work, do nothing
    logging.info(f"Checking to see if the work item '{work_item_data['Title']} ({work_item_data['WorkItemKey']})' has a work schedule.")
    if not work_schedule_key:
        logging.info("No schedule exists. Returning to main handler.")
        return
    logging.info("Work schedule exists.")

    # set the endpoint for interacting with the existing work shceudle
    work_schedule_endpoint = f"WorkSchedules/{work_schedule_key}"
    # get the existign work schedule
    try:
        logging.info(f"Requesting work schedule '{work_schedule_key}'")
        existing_work_schedule_data = Entities(bearer_token,access_key).get(work_schedule_endpoint)
        logging.info("Successfully retrieved existing work schedule.")
    except Exception as e:
        logging.error(f"Failed to retreive work schedule with the follwoing error:")
        logging.error(e)
    

    # check if work item start date is on the recurring pattern
    try:
        logging.info("Checking if the start date of the work item matches the pattern of the work shchedule.")
        work_item_start_date_is_unchanged = does_date_recur(
            existing_work_schedule_data['ScheduleStartDate'],
            existing_work_schedule_data['RecurrenceFrequency'],
            existing_work_schedule_data['CustomFrequencyMultiple'],
            work_item_data['StartDate']
        )
    except Exception as e:
        logging.error(f"Failed to check dates with the following error:")
        logging.error(e)

    if work_item_start_date_is_unchanged:
        logging.info("The work item is on the current work schedule. No further action taken.")
        return
    else:
        logging.info("The work item start date has been changed.")
        # copy work schedule
        new_work_schedule_data = existing_work_schedule_data
        # update new work schedule with the start date from the current work item
        new_work_schedule_data['ScheduleStartDate'] = work_item_data['StartDate']
        # add the current work item key to create the new work schedule
        new_work_schedule_data['CreatedFromWorkItemKey'] = work_item_data['WorkItemKey']
        # add an end date to the current work schedule (set to current work start date)
        existing_work_schedule_data['ScheduleEndDate'] = work_item_data['StartDate']
        # end the current work schedule on current work item start date
        try:
            logging.info("Trying to end the current work schedule.")
            Entities(bearer_token,access_key).put(endpoint=existing_work_schedule_data['work_schedule_endpoint'],data=existing_work_schedule_data)
            logging.info("Successfully ended the current work schedule.")
        except Exception as e:
            logging.error("Failed to add end date to existing work schedule with the follwoing error:")
            logging.error(e)
        # add the new work schedule
        try:
            logging.info("Trying to add new work schedule.")
            new_work_schedule_response = Entities(bearer_token,access_key).post('WorkSchedules',new_work_schedule_data)
            logging.info("Successfully added new work schedule.")
        except Exception as e:
            logging.error("Failed to add new work schedule with the following error:")
            logging.error(e)

def add_months(start_date: date, months: int):
    """
    Add a specified number of months to a date, handling month and year rollovers.

    Args:
        start_date (datetime): The starting date.
        months (int): The number of months to add.

    Returns:
        datetime: The resulting date after adding the specified number of months.
    """
    month = start_date.month - 1 + months
    year = start_date.year + month // 12
    month = month % 12 + 1
    day = min(start_date.day, [31,
        29 if year % 4 == 0 and not year % 100 == 0 or year % 400 == 0 else 28,
        31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month-1])
    return start_date.replace(year=year, month=month, day=day)

def does_date_recur(
        work_schedule_start_date: datetime, 
        interval_type: Literal['days', 'weeks', 'months', 'years'], 
        interval_value: int, 
        work_item_start_date: datetime
    ) -> bool:
    """
    Check if a given date recurs based on a specified recurrence pattern.

    Args:
        work_schedule_start_date (datetime): The starting date of the recurrence.
        recurrence_pattern (dict): A dictionary containing 'interval_type' (Must be 'days', 'weeks', 'months' or 'years') and 'interval_value'.
            Example:
            recurrence_pattern = {
                'interval_type': 'weeks',  # Options: 'days', 'weeks', 'months', 'years'
                'interval_value': 2  # Every other week
            }
        work_item_start_date (datetime): The date to check against the recurrence pattern.

    Returns:
        bool: True if the work_item_start_date matches a recurring date, False otherwise.
    """
    current_date = work_schedule_start_date
    
    logging.info(f"Starting recurrence check from {work_schedule_start_date} with interval type '{interval_type}' and value {interval_value}")
    
    while current_date <= work_item_start_date:
        logging.debug(f"Current date: {current_date}")
        
        if current_date == work_item_start_date:
            logging.info(f"Date {work_item_start_date} matches the recurrence pattern.")
            return True
        
        if interval_type == 'days':
            current_date += timedelta(days=interval_value)
        elif interval_type == 'weeks':
            current_date += timedelta(weeks=interval_value)
        elif interval_type == 'months':
            current_date = current_date.date()
            current_date = add_months(current_date, interval_value)
        elif interval_type == 'years':
            current_date = current_date.replace(year=current_date.year + interval_value)
        else:
            logging.error(f"Unsupported interval type: {interval_type}")
            raise ValueError(f"Unsupported interval type: {interval_type}")

    logging.info(f"Date {work_item_start_date} does not match the recurrence pattern.")
    return False

# Example usage:
if __name__ == "__main__":
    start_date = datetime(2024, 1, 1)
    recurrence_pattern = {
        'interval_type': 'weeks',  # Options: 'days', 'weeks', 'months', 'years'
        'interval_value': 2  # Every other week
    }
    check_date = datetime(2024, 1, 15)

    is_recurring = does_date_recur(start_date, recurrence_pattern, check_date)

    print("Does the date recur:", is_recurring)
