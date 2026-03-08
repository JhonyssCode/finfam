from datetime import date
import calendar
import logging
from flask import current_app

def register_jobs(app):
    """
    Register APScheduler background jobs.
    """
    from .__init__ import scheduler
    
    # Run everyday at 1:00 AM
    scheduler.add_job(
        id='process_recurring_bills',
        func=process_recurring_bills,
        args=[app],
        trigger='cron',
        hour=1,
        minute=0,
        replace_existing=True
    )
    
def process_recurring_bills(app):
    """
    Background job checking for bills that need to spawn a next cycle.
    """
    from .models import db, Bill
    
    with app.app_context():
        today = date.today()
        # Find bills that have a recurrence_rule, and it's time to generate the next one
        # `next_recurrence_date` holds the date of the next iteration that hasn't been created yet.
        pending_recurrences = Bill.query.filter(
            Bill.recurrence_rule.isnot(None),
            Bill.recurrence_rule != '',
            Bill.next_recurrence_date <= today
        ).all()
        
        created = 0
        for bill in pending_recurrences:
            rule = bill.recurrence_rule
            
            # Figure out next date
            next_date = None
            if rule == 'monthly':
                nm = bill.next_recurrence_date.month + 1
                ny = bill.next_recurrence_date.year + (nm - 1) // 12
                nm = ((nm - 1) % 12) + 1
                max_day = calendar.monthrange(ny, nm)[1]
                next_date = date(ny, nm, min(bill.next_recurrence_date.day, max_day))
            elif rule == 'yearly':
                # keep same day/month, advance year
                ny = bill.next_recurrence_date.year + 1
                max_day = calendar.monthrange(ny, bill.next_recurrence_date.month)[1]
                next_date = date(ny, bill.next_recurrence_date.month, min(bill.next_recurrence_date.day, max_day))
            
            if next_date:
                new_bill = Bill(
                    description=bill.description,
                    amount=bill.amount,
                    due_date=bill.next_recurrence_date,
                    type=bill.type,
                    scope=bill.scope,
                    paid=False,
                    user_id=bill.user_id,
                    family_id=bill.family_id,
                    recurrence_rule=rule,
                    next_recurrence_date=next_date
                )
                db.session.add(new_bill)
                
                # Turn off recurrence for the older bill so it doesn't duplicate
                bill.recurrence_rule = None
                bill.next_recurrence_date = None
                created += 1
                
        if created > 0:
            db.session.commit()
            logging.info(f"Geradas {created} contas recorrentes.")
