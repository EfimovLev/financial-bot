from aiogram.fsm.state import State, StatesGroup

class TransactionStates(StatesGroup):
    waiting_for_amount = State()

class CategoryStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_type = State()
class FeedbackStates(StatesGroup):
    waiting_for_feedback = State()
