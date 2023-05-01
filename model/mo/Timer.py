from datetime import datetime, timedelta

class Timer:
  def __init__(self, time_budget_sec):
    self.time_budget_sec = time_budget_sec
    self.start_time = datetime.now()

  def resume(self):
    if self.time_budget_sec <= 0:
      raise TimeoutError()
    self.start_time = datetime.now()
    return timedelta(seconds = self.time_budget_sec)

  def pause(self):
    end_time = datetime.now()
    dur = (end_time - self.start_time).total_seconds()
    self.time_budget_sec -= dur
    return dur
