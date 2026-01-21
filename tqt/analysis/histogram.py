"""
Histogram functions for analyzing time tag files

Includes:
    1) Temporal cross correlation functions
        Used for g2 measurements, etc.
        This function can be used for short cross-correlations (i.e. with correlated photon pairs) where time
        delays are on the order of nanoseconds *or* for longer cross-correlation measurements, such as with
        pseudo-thermal sources, where the histogram width is into the micro/millisecond regime
"""

import numpy as np
import matplotlib.pyplot as plt
from math import floor, ceil
from tqdm import tqdm

from tqt.utils.io import IO


def cross_correlation_histogram(
    tags=None, ch_a=1, ch_b=2, bin_width=100, hist_width=50000
):
    """
    Calculates a cross-correlation histogram between two time-tagger channels.
    This can be useful for g2 measurements, or simple lab checks such as the timing difference between two photon paths.

    Parameters
    ----------
    tags: numpy array imported from a time-tage text file
    ch_a: channel integer value to use as Channel A (must be an integer between 1 and 16, inclusive)
    ch_b: integer value to use as Channel B (must be an integer between 1 and 16, inclusive)
    bin_width: width of each individual bin in the histogram [ns]
    hist_width: the histogram ranges from -hist_widtht to +hist_width [ns]

    Returns
    -------
    hist: the histogram count values (y-values in a histogram plot)
    hist_bins: the central value of each bin (x-values in a histogram plot)
    hist_norm: (normalized) histogram count frequencies (see Kevin's notes on how to normalize using single counts)
    """

    a = tags[(tags[:, 0] == ch_a), 1]
    b = tags[(tags[:, 0] == ch_b), 1]
    T = np.max(tags[:, 1]) * 0.15625  # total measurement time [ns]

    n_bins = ceil(2 * hist_width / bin_width)

    hist = np.zeros(n_bins)
    hist_bins = np.linspace(-hist_width, hist_width, n_bins)

    start_ind = 0

    j = 0
    for i in tqdm(range(a.shape[0])):
        a_t = a[i]
        while j < b.shape[0]:
            b_t = b[j]
            dt = (b_t - a_t) * 0.15625  # [ns]
            if dt < -hist_width:
                start_ind = j
            elif dt > hist_width:
                break
            else:
                bin_ind = floor((dt + hist_width) / bin_width)
                if bin_ind < hist.shape[0]:
                    hist[bin_ind] += 1
                else:
                    pass
                    # warnings.warn("Outside the bounds for the histogram")

            j += 1

        j = start_ind
        i += 1

    accidentals = (bin_width / T) * (a.shape[0] * b.shape[0])
    hist_norm = hist / accidentals
    return hist, hist_bins, hist_norm


if __name__ == "__main__":

    plt.close("all")

    io = IO(path=IO.default_path.parent.joinpath("qoqi/analysis/example_data"))

    # example data is for an attenuated coherent laser source
    tags = io.load_timetags(filename="time_tags_coherent.txt")

    hist, hist_bins, hist_norm = cross_correlation_histogram(
        tags=tags, bin_width=200000 / 100, hist_width=200000
    )

    fig, ax = plt.subplots(1, 1)
    ax.plot(hist_bins, hist_norm)
    ax.set(xlabel="Time delay (ns)", ylabel="Counts")
    plt.show()
