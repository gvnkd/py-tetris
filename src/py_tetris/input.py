"""DAS/ARR key-repeat timing (pure logic, no pygame)."""

from py_tetris.constants import ARR_INTERVAL, DAS_DELAY


class AutoRepeat:
    """One held key: immediate step on press, first repeat after DAS_DELAY,
    then one step per ARR_INTERVAL while held."""

    def __init__(self) -> None:
        self.active: bool = False
        self.timer: float = 0.0
        self.das_passed: bool = False

    def press(self) -> None:
        self.active = True
        self.timer = 0.0
        self.das_passed = False

    def release(self) -> None:
        self.active = False
        self.timer = 0.0
        self.das_passed = False

    def tick(self, dt: float) -> int:
        """Advance by dt milliseconds; return how many repeat steps are due."""
        if not self.active:
            return 0
        self.timer += dt / 1000.0
        steps = 0
        if not self.das_passed:
            if self.timer >= DAS_DELAY:
                self.timer -= DAS_DELAY
                self.das_passed = True
                steps = 1
        while self.das_passed and self.timer >= ARR_INTERVAL:
            self.timer -= ARR_INTERVAL
            steps += 1
        return steps
