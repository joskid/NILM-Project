"""
Utility class for dealing with timeseries data.
"""

# pylint: disable=E1101

import numpy as np


class TimeSeries(object):
    """
    Object for holding, manipulating, and loading power timeseries data.
    """
    def __init__(self, name='', path=None):
        self.name = name
        if path is not None:
            self.array = np.genfromtxt(path, dtype=[('time', np.uint32),
                                                    ('power', np.float32)])
            self.array = np.sort(self.array)
        else:
            self.array = np.rec.array((0, 2), dtype=[('time', np.uint32),
                                                     ('power', np.float32)])

    @property
    def times(self):
        """Returns the array of times in the series."""
        return self.array['time']

    @property
    def powers(self):
        """Returns the array of powers in the series."""
        return self.array['power']

    @powers.setter
    def powers(self, power_array):
        """Set the powers in the series to a copy of the given array-."""
        self.array['power'] = power_array.copy()

    def indicators(self, threshold=np.float32(0.0)):
        """
        Returns the boolean on-off indicators for the timeseries, given a power
        threshold.
        """
        return np.apply_along_axis(lambda x: (x > threshold), 0, self.powers)

    def __add__(self, ts):
        """
        Add two timeseries together, based on the intersection of their
        timestamps.
        """
        indices1 = np.in1d(self.times, ts.times, assume_unique=True)
        indices2 = np.in1d(ts.times, self.times, assume_unique=True)

        ts_sum = TimeSeries()
        ts_sum.array = self.array[indices1]
        ts_sum.powers += ts.powers[indices2]

        return ts_sum

    def __sub__(self, ts):
        """
        Subtract two timeseries, based on the intersection of their timestamps.
        """
        indices1 = np.in1d(self.times, ts.times, assume_unique=True)
        indices2 = np.in1d(ts.times, self.times, assume_unique=True)

        ts_diff = TimeSeries()
        ts_diff.array = self.array[indices1]
        ts_diff.powers -= ts.powers[indices2]

        return ts_diff

    def intersect(self, ts):
        """
        Modify self to only contain the timestamps present in the given
        timeseries.
        """
        indices = np.in1d(self.times, ts.times, assume_unique=True)

        self.array = self.array[indices]

    def pad(self, max_pad):
        """
        Pad the timeseries data so that there are no missing values. We fill in
        missing power values using the previous power value in the series.
        """
        width = self.times[-1] - self.times[0] + 1
        padded_array = np.rec.array((0, 2), dtype=[('time', np.uint32),
                                                   ('power', np.float32)])
        padded_array.resize(width)

        cnt = 0
        for i in xrange(len(self.times)-1):
            padded_array[cnt] = (np.uint32(self.times[i]), self.powers[i])
            cnt += 1

            if self.times[i+1] - self.times[i] > max_pad:
                continue

            for t in xrange(self.times[i]+1, self.times[i+1]):
                padded_array[cnt] = (np.uint32(t), self.powers[i])
                cnt += 1

        padded_array[cnt] = (np.uint32(self.times[-1]), self.powers[-1])
        padded_array.resize(cnt + 1)

        self.array = padded_array

    def activations(self, threshold=np.float32(0.0)):
        """
        Returns the device activations as a list of [start, end) index tuples.
        We assume that a device turning on and off is an entire activation.
        """
        activations = []

        ind = self.indicators(threshold)
        in_interval = ind[0]

        if in_interval:
            start = 0

        for i in xrange(len(ind)):
            if not ind[i] and in_interval:
                in_interval = False
                activations.append((start, i))

            if ind[i] and not in_interval:
                in_interval = True
                start = i

        if in_interval:
            activations.append((start, len(ind)))

        return activations

    def write(self, path):
        """
        Write the timeseries data to the given path.
        """
        with open(path, 'w') as fd:
            for i in self.array:
                fd.write('%s %s\n' % (i[0], i[1]))
