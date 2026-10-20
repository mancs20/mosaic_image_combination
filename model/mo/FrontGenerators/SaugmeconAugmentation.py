from dataclasses import dataclass

# Subtracted from 1 / k to make delta strictly smaller than 1 / k, see compute_saugmecon_augmentation
DEFAULT_GUARD = 1e-6


@dataclass
class SaugmeconAugmentation:
    delta: float
    guard: float
    # smallest difference in the augmented objective between two different solutions that the solver must be able to
    # tell apart: min(k * guard, delta / r_max), see compute_saugmecon_augmentation
    min_difference: float


def compute_saugmecon_augmentation(range_array, guard=DEFAULT_GUARD):
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
        dominates the other): the difference in obj is at least delta / r_i. The solver must tell it apart, if not it
        may return the dominated solution.
    The smallest difference to tell apart is min(k * guard, delta / r_max), r_max being the largest range.

    range_array: range of objectives 1..p-1
    """
    # an objective with range 0 is constant, it does not take part in the augmentation
    active_ranges = [r for r in range_array if r > 0]
    k = max(len(active_ranges), 1)
    delta = 1.0 / k - guard
    min_difference = min([k * guard] + [delta / r for r in active_ranges])
    return SaugmeconAugmentation(delta, guard, min_difference)
