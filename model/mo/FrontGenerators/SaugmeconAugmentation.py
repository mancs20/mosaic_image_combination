from dataclasses import dataclass


@dataclass
class SaugmeconAugmentation:
    delta: float
    guard: float
    # smallest difference in the augmented objective between two different solutions that the solver must be able to
    # tell apart: k * guard, see compute_saugmecon_augmentation
    min_difference: float


def compute_saugmecon_augmentation(range_array):
    """
    Augmented objective of Saugmecon (solver independent, it only works with numbers):

        obj = f_0 + delta * sum_i (f_i / r_i)      with   delta = 1 / k - guard

    r_i is the range of objective i (best - nadir), objectives 1..p-1, and k is the number of objectives with r_i > 0
    (k = p - 1, p being the number of objectives, when no objective is constant). The guard makes delta strictly
    smaller than 1 / k.
      * Two solutions with a different f_0: the difference in obj is at least 1 - delta * k = k * guard, because the
        augmentation of a solution minus the augmentation of the other is at most k * delta (each (f_i - f_i') / r_i
        is at most 1). So the best f_0 always wins.
      * Two solutions with the same f_0, one better by at least 1 in some f_i and not worse in the others (it
        dominates the other): the difference in obj is at least delta / r_i >= delta / r_max. The solver must tell it
        apart, if not it may return the dominated solution.
    The solver must tell apart min(k * guard, delta / r_max). The guard is the one that makes both equal,
    k * guard = (1 / k - guard) / r_max, that is guard = 1 / (k * (k * r_max + 1)), so the smallest difference is
    k * guard = 1 / (k * r_max + 1): as large as possible, it only depends on the ranges of the problem.
    With 2 objectives (k = 1) it is obj = f_0 + f_1 / (r_1 + 1), the lexicographic order of (f_0, f_1).

    range_array: range of objectives 1..p-1
    """
    # an objective with range 0 is constant, it does not take part in the augmentation
    active_ranges = [r for r in range_array if r > 0]
    k = max(len(active_ranges), 1)
    r_max = max(active_ranges, default=1)
    guard = 1.0 / (k * (k * r_max + 1))
    delta = 1.0 / k - guard
    min_difference = k * guard
    return SaugmeconAugmentation(delta, guard, min_difference)
