import h5py
import pandas as pd
import os
import numpy as np
import math
import matplotlib.pyplot as plt

# Load HyTEMPO data from HDF5 file
script_folder = os.path.dirname(os.path.abspath(__file__))
hytempo_file = os.path.join(script_folder, 'LuminaSim.h5')

# load the values from the HDF5 file
with h5py.File(hytempo_file, 'r') as f:
    dataset= f['rocket 0']["state"]
    columns = [col.decode() if isinstance(col, bytes) else col for col in dataset.attrs["columns"]]
    
    # get the time data
    t_idx = columns.index("time")
    HyTempo_time = dataset[:, t_idx]

    # get the altitude data
    y_idx = columns.index("y")
    HyTempo_altitude = dataset[:, y_idx]
    
    # get the velocity data
    v_x_idx = columns.index("v_x")
    v_y_idx = columns.index("v_y")
    HyTempo_v_x = dataset[:, v_x_idx]
    HyTempo_v_y = dataset[:, v_y_idx]
    HyTempo_vel = np.sqrt(HyTempo_v_x**2 + HyTempo_v_y**2)

    # get the x position data
    x_idx = columns.index("x")
    HyTempo_x = dataset[:, x_idx]

    # get the angle 
    angle_idx = columns.index("angle")
    HyTempo_angle = dataset[:, angle_idx]



# Load RocketPy data from CSV file
rocketpy_file = os.path.join(script_folder, 'lumina_flight_data.csv') 
rocketpy_data = pd.read_csv(rocketpy_file)

# Extract time, altitude, and velocity from RocketPy data
rocketpy_time = rocketpy_data['# Time (s)'].values
rocketpy_altitude = rocketpy_data[' Altitude AGL (m)'].values
rocketpy_vel = rocketpy_data[' Speed - Velocity Magnitude (m/s)'].values
rocketpy_x = rocketpy_data[' X (m)'].values
rocketpy_y = rocketpy_data[' Y (m)'].values
rocketpy_downrange = np.sqrt(rocketpy_x**2 + rocketpy_y**2)
rocketpy_attitude_angle = rocketpy_data[' Attitude Angle (°)'].values
rocketpy_path_angle = rocketpy_data[' Path Angle (°)'].values
rocketpy_aoa = rocketpy_data[' Angle of Attack (°)'].values

plt.rcParams.update({'font.size':26})
plt.rcParams['text.usetex'] = True
plt.rcParams['lines.linewidth'] = 3
offset_m = 20

# Create savefolder if it doesn't exist
savefolder = os.path.join(script_folder, 'Images')
os.makedirs(savefolder, exist_ok=True)

# Plot the angles over time
plt.figure(figsize=(10,8))
plt.plot(HyTempo_time, HyTempo_angle, label='HyTEMPO', color='tab:blue')
plt.plot(rocketpy_time, rocketpy_attitude_angle, label='RocketPy', color='tab:orange', linestyle='--')
plt.xlabel('Time [s]')
plt.ylabel('Pitch Angle [deg]')
plt.legend()
plt.grid(True)
plt.xlim(0, max(HyTempo_time.max(), rocketpy_time.max()))
plt.ylim(-90, 90)
plt.yticks(np.linspace(-90, 90, 9))

# Add dotted vertical lines for apogees
# RocketPy apogee
apogee_idx_rp = np.argmax(rocketpy_altitude)
apogee_time_rp = rocketpy_time[apogee_idx_rp]
plt.axvline(apogee_time_rp, color='tab:orange', linestyle=':', linewidth=2, label='Apogee RocketPy')
plt.text(apogee_time_rp, 90*0.95, r'\textbf{Apogee RocketPy}', color='tab:orange', rotation=90, va='top', ha='left', fontsize=22)

# HyTEMPO apogee
apogee_idx_ht = np.argmax(HyTempo_altitude)
apogee_time_ht = HyTempo_time[apogee_idx_ht]
plt.axvline(apogee_time_ht, color='tab:blue', linestyle=':', linewidth=2, label='Apogee HyTEMPO')
plt.text(apogee_time_ht, -90*0.1, r'\textbf{Apogee HyTEMPO}', color='tab:blue', rotation=90, va='top', ha='right', fontsize=22)

# Add dotted line for Engine Cutoff at 7 seconds
plt.axvline(7, color='black', linestyle=':', linewidth=2, label='Engine Cutoff')
plt.text(7, 90*0.7, r'\textbf{Engine Burnout}', color='black', rotation=90, va='top', ha='right', fontsize=22)
plt.tight_layout()
plt.savefig(os.path.join(savefolder, 'angles_vs_time.png'))

# Plot the aoa over time
plt.figure(figsize=(10,8))
plt.plot(rocketpy_time, rocketpy_aoa, label='AoA', color='tab:orange', linestyle='-')
plt.xlabel('Time [s]')
plt.ylabel('Angle of attack [deg]')
#plt.legend()
plt.grid(True)
plt.xlim(0, rocketpy_time.max())
ymax = 10
plt.ylim(0, ymax)

# Add a dotted vertical line for the apogee
apogee_idx = np.argmax(rocketpy_altitude)
apogee_time = rocketpy_time[apogee_idx]
plt.axvline(apogee_time, color='black', linestyle=':', linewidth=2, label='Apogee')
plt.text(apogee_time, ymax*0.95, r'\textbf{Apogee}', color='black', rotation=90, va='top', ha='right', fontsize=22)
#add dotted line for Engine Cutoff at 7 seconds
plt.axvline(7, color='black', linestyle=':', linewidth=2, label='Engine Cutoff')
plt.text(7, 10*0.95, r'\textbf{Engine Burnout}', color='black', rotation=90, va='top', ha='right', fontsize=22)

plt.tight_layout()
plt.savefig(os.path.join(savefolder, 'AOA_Rocketpy.png'))

# Plot the trajectory in the altitude downrange plane
plt.figure(figsize=(10,8))
plt.plot(HyTempo_x, HyTempo_altitude, label='HyTEMPO', color='tab:blue')
plt.plot(rocketpy_downrange, rocketpy_altitude, label='RocketPy', color='tab:orange', linestyle='--')
plt.xlabel('Downrange Distance [m]')
plt.ylabel('Altitude [m]')
plt.legend()
plt.grid(True)
plt.xlim(0, max(HyTempo_x.max(), rocketpy_downrange.max()))
ymax = max(HyTempo_altitude.max(), rocketpy_altitude.max()) 
ymax = math.ceil(ymax / 500) * 500
plt.ylim(0, ymax)

# Add vertical lines and text for apogees
# RocketPy apogee
apogee_idx_rp = np.argmax(rocketpy_altitude)
apogee_x_rp = rocketpy_downrange[apogee_idx_rp]
plt.axvline(apogee_x_rp, color='tab:orange', linestyle=':', linewidth=2, label='Apogee RocketPy')
plt.text(apogee_x_rp-offset_m, ymax*0.7, r'\textbf{Apogee RocketPy}', color='tab:orange', rotation=90, va='top', ha='right', fontsize=22)

# HyTEMPO apogee
apogee_idx_ht = np.argmax(HyTempo_altitude)
apogee_x_ht = HyTempo_x[apogee_idx_ht]
plt.axvline(apogee_x_ht, color='tab:blue', linestyle=':', linewidth=2, label='Apogee HyTEMPO')
plt.text(apogee_x_ht+offset_m, ymax*0.7, r'\textbf{Apogee HyTEMPO}', color='tab:blue', rotation=90, va='top', ha='left', fontsize=22)

# Add vertical lines for engine cutoff at t=7s for both datasets, using the main line colors
# Find downrange at t=7s for RocketPy
if np.any(rocketpy_time >= 7):
    cutoff_idx_rp = np.searchsorted(rocketpy_time, 7)
    cutoff_x_rp = rocketpy_downrange[cutoff_idx_rp]
    plt.axvline(cutoff_x_rp, color='tab:orange', linestyle=':', linewidth=2, label='Engine Cutoff')
    plt.text(cutoff_x_rp-offset_m, ymax*0.95, r'\textbf{Burnout RocketPy}', color='tab:orange', rotation=90, va='top', ha='right', fontsize=22)

# Find downrange at t=7s for HyTEMPO
if np.any(HyTempo_time >= 7):
    cutoff_idx_ht = np.searchsorted(HyTempo_time, 7)
    cutoff_x_ht = HyTempo_x[cutoff_idx_ht]
    plt.axvline(cutoff_x_ht, color='tab:blue', linestyle=':', linewidth=2, label='Engine Cutoff')
    plt.text(cutoff_x_ht+offset_m, ymax*0.95, r'\textbf{Burnout HyTEMPO}', color='tab:blue', rotation=90, va='top', ha='left', fontsize=22)

plt.tight_layout()
plt.savefig(os.path.join(savefolder, 'trajectory_altitude_downrange.png'))


# Plot altitude vs time
plt.figure(figsize=(10,8))
plt.plot(HyTempo_time, HyTempo_altitude, label='HyTEMPO', color='tab:blue')
plt.plot(rocketpy_time, rocketpy_altitude, label='RocketPy', color='tab:orange', linestyle='--')
plt.xlabel('Time [s]')
plt.ylabel('Altitude [m]')
plt.legend()
plt.grid(True)
plt.xlim(0, max(HyTempo_time.max(), rocketpy_time.max()))
ymax = max(HyTempo_altitude.max(), rocketpy_altitude.max()) 
ymax = math.ceil(ymax / 500) * 500
plt.ylim(0, ymax)
#add dotted line for Engine Cutoff at 7 seconds
plt.axvline(7, color='black', linestyle=':', linewidth=2, label='Engine Cutoff')
plt.text(7, ymax*0.95, r'\textbf{Engine Burnout}', color='black', rotation=90, va='top', ha='right', fontsize=22)
# Add a dotted vertical line for the rpapogee
apogee_idx = np.argmax(rocketpy_altitude)
apogee_time = rocketpy_time[apogee_idx]
plt.axvline(apogee_time, color='tab:orange', linestyle=':', linewidth=2, label='Apogee')
plt.text(apogee_time, ymax*0.7, r'\textbf{Apogee RocketPy}', color='tab:orange', rotation=90, va='top', ha='left', fontsize=22)
# Add a dotted vertical line for the rpapogee
apogee_idx = np.argmax(HyTempo_altitude)
apogee_time = HyTempo_time[apogee_idx]
plt.axvline(apogee_time, color='tab:blue', linestyle=':', linewidth=2, label='Apogee')
plt.text(apogee_time, ymax*0.7, r'\textbf{Apogee HyTempo}', color='tab:blue', rotation=90, va='top', ha='right', fontsize=22)

plt.tight_layout()
plt.savefig(os.path.join(savefolder, 'altitude_vs_time.png'))




# Plot velocity vs time
plt.figure(figsize=(10, 8))
plt.plot(HyTempo_time, HyTempo_vel, label='HyTEMPO', color='tab:blue')
plt.plot(rocketpy_time, rocketpy_vel, label='RocketPy', color='tab:orange', linestyle='--')
plt.xlabel('Time [s]')
plt.ylabel('Velocity [m/s]')
plt.legend()
plt.grid(True)
plt.xlim(0, max(HyTempo_time.max(), rocketpy_time.max()))
plt.ylim(0, 300)
# Add a dotted vertical line for RocketPy apogee
apogee_idx_rp = np.argmax(rocketpy_altitude)
apogee_time_rp = rocketpy_time[apogee_idx_rp]
plt.axvline(apogee_time_rp, color='tab:orange', linestyle=':', linewidth=2, label='Apogee RocketPy')
plt.text(apogee_time_rp*1.01, 300*0.85, r'\textbf{Apogee RocketPy}', color='tab:orange', rotation=90, va='top', ha='left', fontsize=22)

# Add a dotted vertical line for HyTEMPO apogee
apogee_idx_ht = np.argmax(HyTempo_altitude)
apogee_time_ht = HyTempo_time[apogee_idx_ht]
plt.axvline(apogee_time_ht, color='tab:blue', linestyle=':', linewidth=2, label='Apogee HyTEMPO')
plt.text(apogee_time_ht*0.99, 300*0.85, r'\textbf{Apogee HyTEMPO}', color='tab:blue', rotation=90, va='top', ha='right', fontsize=22)

# Add dotted vertical lines for burnout (engine cutoff) at t=7s for both datasets
plt.axvline(7, color='black', linestyle=':', linewidth=2, label='Engine Cutoff')
plt.text(7*0.95, 300*0.4, r'\textbf{Engine Burnout}', color='black', rotation=90, va='top', ha='right', fontsize=22)

plt.tight_layout()
plt.savefig(os.path.join(savefolder, 'velocity_vs_time.png'))

