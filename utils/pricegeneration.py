import numpy as np 

def boundedRandomWalk(length, lower_bound,  upper_bound, start, end, std):
    '''

    Taken from user igrinis on Stack Overflow: https://stackoverflow.com/a/47005958/5433929

    From the post:

    You can see it as a solution of geometric problem. 
    The trend_line is connecting your start and end points, and have margins defined by lower_bound and upper_bound. 
    rand is your random walk, rand_trend it's trend line and rand_deltas is it's deviation from the rand trend line. 
    We collocate the trend lines, and want to make sure that deltas don't exceed margins. When rand_deltas exceeds the allowed margin, we "fold" the excess back to the bounds.
    At the end you add the resulting random deltas to the start=>end trend line, thus receiving the desired bounded random walk.
    The std parameter corresponds to the amount of variance of the random walk.
    In this version "std" is not promised to be the "interval". 


    '''
    assert (lower_bound <= start and lower_bound <= end)
    assert (start <= upper_bound and end <= upper_bound)

    bounds = upper_bound - lower_bound

    rand = (std * (np.random.random_sample(length) - 0.5)).cumsum()
    rand_trend = np.linspace(rand[0], rand[-1], length)
    rand_deltas = (rand - rand_trend)
    rand_deltas /= np.max([1, (rand_deltas.max()-rand_deltas.min())/bounds])

    trend_line = np.linspace(start, end, length)
    upper_bound_delta = upper_bound - trend_line
    lower_bound_delta = lower_bound - trend_line

    upper_slips_mask = (rand_deltas-upper_bound_delta) >= 0
    upper_deltas =  rand_deltas - upper_bound_delta
    rand_deltas[upper_slips_mask] = (upper_bound_delta - upper_deltas)[upper_slips_mask]

    lower_slips_mask = (lower_bound_delta-rand_deltas) >= 0
    lower_deltas =  lower_bound_delta - rand_deltas
    rand_deltas[lower_slips_mask] = (lower_bound_delta + lower_deltas)[lower_slips_mask]

    return trend_line + rand_deltas