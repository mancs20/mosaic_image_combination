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


class WallClockTimer(Timer):
  """Timer whose budget is the wall-clock time since its creation: everything counts (the solver and also the Python
  work around it), not only the time spent inside the solver."""
  def __init__(self, time_budget_sec):
    self.total_budget_sec = time_budget_sec
    self.creation_time = datetime.now()
    super().__init__(time_budget_sec)

  @property
  def time_budget_sec(self):
    return self.total_budget_sec - (datetime.now() - self.creation_time).total_seconds()

  @time_budget_sec.setter
  def time_budget_sec(self, value):
    # the remaining budget is always computed from the wall clock, a value assigned (Timer.__init__ and
    # Timer.pause do it) is ignored
    pass

  def pause(self):
    # only the duration of the last solver call is returned (used by the statistics of the solver)
    return (datetime.now() - self.start_time).total_seconds()
