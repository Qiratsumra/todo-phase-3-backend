"""
Direct test of filtering and sorting logic
"""

from dotenv import load_dotenv
load_dotenv()

from database import SessionLocal
from models import Task
from enums import PriorityEnum
from sqlalchemy import desc, asc

# Test direct database queries
db = SessionLocal()

print("="*60)
print("DIRECT DATABASE QUERY TESTS")
print("="*60)

# Test 1: Get all tasks
all_tasks = db.query(Task).all()
print(f"\n1. Total tasks in database: {len(all_tasks)}")
for task in all_tasks[:5]:
    print(f"   - {task.title[:30]}: priority={task.priority}")

# Test 2: Filter by high priority
print("\n2. Filter by HIGH priority:")
high_tasks = db.query(Task).filter(Task.priority == PriorityEnum.HIGH).all()
print(f"   Found {len(high_tasks)} high priority tasks")
for task in high_tasks[:3]:
    print(f"   - {task.title[:30]}: priority={task.priority}")

# Test 3: Sort by priority descending
print("\n3. Sort by priority (descending):")
sorted_tasks = db.query(Task).order_by(desc(Task.priority)).limit(5).all()
for task in sorted_tasks:
    print(f"   - {task.title[:30]}: priority={task.priority}")

# Test 4: Sort by title ascending
print("\n4. Sort by title (ascending):")
sorted_tasks = db.query(Task).order_by(asc(Task.title)).limit(5).all()
for task in sorted_tasks:
    print(f"   - {task.title[:30]}")

# Test 5: Combined filter and sort
print("\n5. Combined: Filter HIGH + Sort by title:")
combined = db.query(Task).filter(Task.priority == PriorityEnum.HIGH).order_by(asc(Task.title)).all()
print(f"   Found {len(combined)} high priority tasks (sorted by title)")
for task in combined[:3]:
    print(f"   - {task.title[:30]}: priority={task.priority}")

db.close()

print("\n" + "="*60)
print("ALL DIRECT DB TESTS COMPLETE")
print("="*60)
