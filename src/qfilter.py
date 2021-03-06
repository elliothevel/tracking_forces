"""
This file takes converted trajectory data from the tracked images and filters 
the raw angle configurations. It also calculates the velocity and acceleration
at each time step. 
"""
import sys
import os
import pickle
import numpy as np
import scipy.interpolate
import scipy.signal
import argparse
import matplotlib.pyplot as plt

from util import *
from convert import convert_frames

def moving_average(interval, window_size):
    window = np.ones(int(window_size))/float(window_size)
    return np.convolve(interval, window, 'same')

def filter_spline(x, s, k):
    t = range(len(x))
    s = scipy.interpolate.UnivariateSpline(t, x, s=s, k=k)
    return s(t)

def low_pass_fir(x, N, fs, fc):
    fc = fc/(0.5*fs)
    b, a = scipy.signal.butter(N, fc)
    y = scipy.signal.lfilter(b, a, x)
    x_filtered = np.append(y[N:], np.zeros(N))
    return x_filtered

def filter_trajectory(x, filter_type, filter_options):
    """Filters the signal x(t)."""
    if filter_type == 'moving_average':
        return moving_average(x, int(filter_options['bin_width']))
    elif filter_type == 'smoothing_spline':
        return filter_spline(x, float(filter_options['filter_s']),
                                float(filter_options['filter_k']))
    elif filter_type == 'low_pass_fir':  
        return low_pass_fir(x, int(filter_options['filter_n']),
                               float(filter_options['filter_fs']),
                               float(filter_options['filter_fc']))

def calc_vel_and_accel(x, dt):
    """Uses finite-differencing to calculate the velocity and acceleration."""
    v = np.gradient(x)/dt
    a = np.gradient(v)/dt
    return v, a
    
def filter_data(file_name, file_path, dt, dim=2, ref_index=0, 
                filter_type='moving_average', filter_options={}):
    """ 
    Loads the trajectories, filters them, and calculates velocities and
    accelerations. 
    """
    assert filter_type in ['moving_average', 
                           'smoothing_spline', 
                           'low_pass_fir'], "invalid filter type"
    if filter_options['filter_plot'] == 'True':
        plot_filtered_traj = True
    else:
        plot_filtered_traj = False
    print '-'*25+'FILTER'+'-'*25

    # Load the trajectories from file.
    print 'Loading data...',
    data = load_file('%s%s' %(file_path, file_name))
    print 'done (Loaded data from %s%s)' %(file_path, file_name)

    # Initialize empty arrays to hold filtered data.
    n_steps, n_q = np.shape(data['q'])
    q_filtered = np.empty((n_steps, n_q))
    v_filtered = np.empty((n_steps, n_q))
    a_filtered = np.empty((n_steps, n_q))

    # Here we convert all configurations to be relative to some reference,
    # specified as some frame in time. This reference needs to be saved to
    # build the whisker system later.
    ref = data['q'][ref_index]
    data['q'] = get_relative_configs(data['q'], data['q'][ref_index], dim)
        
    # Here we check if any angles are greater than two radians. This can 
    # happen for bad frames in which the whisker image is really short. 
    # This causes the links to fold on themselves to fit into the given 
    # length. If this happens we simply throw out the frame and use the 
    # previous frame again.
    for i in range(1,n_steps):
        if np.any(data['q'][i]>1.0): 
            pass
            #print 'TEST'
            #data['q'][i,:] = data['q'][i-1,:]

    # For each angle in the trajectory, filter the raw angle and then compute
    # the velocity and accelerations.
    print 'Filtering and computing finite differences...',
    for i in range(n_q):
        ang_traj = data['q'][:,i]            
        filtered_ang_traj = filter_trajectory(ang_traj, filter_type,
                                                        filter_options)
        v, a = calc_vel_and_accel(filtered_ang_traj, dt)
        q_filtered[:,i] = filtered_ang_traj
        v_filtered[:,i] = v
        a_filtered[:,i] = a
    
        if plot_filtered_traj:
            t = np.array(range(len(ang_traj)))
            plt.plot(t, ang_traj, t, filtered_ang_traj)
            plt.show()

    print 'done'     

    FILTERED_DATA = {'q': q_filtered, 'v': v_filtered, 'a': a_filtered, 
            'cp': data['CP'], 'ref': ref, 'link_length': data['link_length']}

    # Save the results to a file.
    print 'Saving to file...',
    f = open('%s%s.p' %(file_path, os.path.splitext(file_name)[0]+'_filtered'), 'w')
    pickle.dump(FILTERED_DATA, f)
    f.close()
    print 'done (Saved to %s%s_filtered.p)' %(file_path,
            os.path.splitext(file_name)[0])
    return FILTERED_DATA


