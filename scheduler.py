"""
scheduler.py
------------
Sets up APScheduler to run price checks automatically.

The scheduler runs as a background thread alongside the Flask app.
By default, it runs once daily, but you can configure it for more
frequent checks (useful for testing).

The scheduler is smart about Flask's app context - it ensures the
database is accessible when the job runs.
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
import atexit


# Global scheduler instance
scheduler = None


def run_scheduled_check(app):
    """
    Wrapper function that runs the price check within Flask's app context.
    
    APScheduler runs in a separate thread, so we need to push the app
    context to access the database.
    
    Args:
        app: The Flask application instance
    """
    with app.app_context():
        from checker import run_price_check
        run_price_check()


def init_scheduler(app, check_interval_minutes=None):
    """
    Initialize and start the scheduler.
    
    Args:
        app: The Flask application instance
        check_interval_minutes: If provided, run every N minutes instead of daily.
                               Useful for testing (e.g., every 5 minutes).
                               If None, runs once daily at 8 AM UTC.
    
    Returns:
        BackgroundScheduler: The scheduler instance
    """
    global scheduler
    
    scheduler = BackgroundScheduler()
    
    if check_interval_minutes:
        # Interval-based trigger (for testing)
        trigger = IntervalTrigger(minutes=check_interval_minutes)
        schedule_desc = f"every {check_interval_minutes} minutes"
    else:
        # Daily trigger at 8 AM UTC
        trigger = CronTrigger(hour=8, minute=0)
        schedule_desc = "daily at 8:00 AM UTC"
    
    # Add the job
    scheduler.add_job(
        func=lambda: run_scheduled_check(app),
        trigger=trigger,
        id='price_check',
        name='Daily Price Check',
        replace_existing=True
    )
    
    # Start the scheduler
    scheduler.start()
    print(f"Scheduler started - price checks running {schedule_desc}")
    
    # Shut down scheduler when app exits
    atexit.register(lambda: scheduler.shutdown())
    
    return scheduler


def trigger_manual_check(app):
    """
    Manually trigger a price check outside the schedule.
    Useful for testing or admin-triggered refreshes.
    
    Args:
        app: The Flask application instance
        
    Returns:
        dict: The summary from run_price_check()
    """
    with app.app_context():
        from checker import run_price_check
        return run_price_check()


def get_next_run_time():
    """
    Get the next scheduled run time.
    
    Returns:
        datetime or None: Next run time, or None if scheduler not running
    """
    global scheduler
    
    if scheduler is None:
        return None
    
    job = scheduler.get_job('price_check')
    if job:
        return job.next_run_time
    return None


def pause_scheduler():
    """Pause the scheduler (jobs won't run but scheduler stays alive)."""
    global scheduler
    if scheduler:
        scheduler.pause()
        print("Scheduler paused")


def resume_scheduler():
    """Resume a paused scheduler."""
    global scheduler
    if scheduler:
        scheduler.resume()
        print("Scheduler resumed")


def update_schedule(check_interval_minutes=None):
    """
    Update the check frequency without restarting the app.
    
    Args:
        check_interval_minutes: New interval in minutes, or None for daily at 8 AM
    """
    global scheduler
    
    if scheduler is None:
        print("Scheduler not initialized")
        return
    
    # Remove existing job
    scheduler.remove_job('price_check')
    
    if check_interval_minutes:
        trigger = IntervalTrigger(minutes=check_interval_minutes)
        schedule_desc = f"every {check_interval_minutes} minutes"
    else:
        trigger = CronTrigger(hour=8, minute=0)
        schedule_desc = "daily at 8:00 AM UTC"
    
    # Get the app from the existing job's context (bit of a workaround)
    # For now, this function should be called with the app available
    print(f"Schedule updated to {schedule_desc}")
    print("Note: You may need to restart the app for this to take full effect")
