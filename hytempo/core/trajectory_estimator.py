# from math import cos, radians, sin
import numpy as np
import pandas as pd
from scipy.integrate import solve_ivp, LSODA
from hytempo.core.data_handling import count_top_level_groups,Observer
from hytempo.core import rocket


class TrajectoryEstimator:
    def __init__(self, rocket: rocket.Rocket, hdf_file,rail_tip_off_angle=20.0):
        """!Constructor for the trajectory estimator.
        @param rocket: Rocket object.
        @param fullreadout: Boolean to determine whether the full readout of
        the trajectory should be saved.
        """
        self.rocket = rocket
        self.observer = Observer(hdf_file,rocket)
        self.filename = hdf_file.filename
        self.rail_tip_off_angle = rail_tip_off_angle

    def integrate_trajectory(self):
        """! Integrate the trajectory of the rocket.
        @return: Trajectory of the rocket in the format of [x,y,v_x,v_y]."""
        "Define event function to stop integration when rocket hits the ground"

        def hit_ground(t, y):
            return y[1]

        hit_ground.terminal = True
        hit_ground.direction = -1

        # Solve trajectory using Scipy's LSODA funtion for manual timestepping
        solver = LSODA(fun=self.compute_right_hand_side,
                       t0=0,
                       t_bound=400,
                       y0=np.array([0,0,0,0]),
                       max_step=0.1
                       )

        # Initialize solution lists
        t = []
        y = []

        while solver.status == "running":
            # Check if the rocket has left the rail in the last step
            if self.rocket.state["onRail"] and self.rocket.state["y"] > self.rocket.rail_height:
                # Disconnect the rocket from the rail
                self.rocket.state["onRail"] = False
                
                # apply the rail tip off angle to the rocket
                #new_angle = self.rocket.state["angle"] - self.rail_tip_off_angle
                #rocket_speed = np.sqrt(solver.y[2] ** 2 + solver.y[3] ** 2)
                #solver._lsoda_solver._y[2] = rocket_speed * np.cos(np.radians(new_angle))
                #solver._lsoda_solver._y[3] = rocket_speed * np.sin(np.radians(new_angle))
            # perform the next step of the solver
            solver.step()

            # Check, if rocket hit the ground
            if solver.y[1] < 0:
                break

            # Append current solution to solution list
            t.append(solver.t)
            y.append(solver.y)

            # Update the observer with the current state
            self.observer.pull_updates()

        # Assemble solution data into trajectory
        trajectory = (np.array(t), np.array(y))

        # Export metrics from the hdf
        self.observer.calculateMetrics()

        return trajectory

    def get_apogee(self, trajectory) -> float:
        """!Get the apogee of the rocket.
        @param trajectory: trajectory of the rocket.
        @return: Apogee of the rocket in m.
        """
        return np.max(trajectory.y[1])

    def get_max_velocity(self, trajectory) -> float:
        """!Get the maximum velocity of the rocket.
        @param trajectory: trajectory of the rocket.
        @return: Maximum velocity of the rocket in m/s.
        """
        return np.max(np.sqrt(trajectory.y[2] ** 2 + trajectory.y[3] ** 2))

    def compute_right_hand_side(
        self, time: float, position_and_velocity: np.ndarray
    ):
        """!Compute the right hand side of the ODE.
        @param time: Time of the simulation.
        @param position_and_velocity: Position and velocity of the rocket.
        @return: Right hand side of the ODE in the format of [v_x,v_y,a_x,a_y].
        """
        "Compute the right hand side of the ODE using the rocket object."
        current_state = self.rocket.compute_right_hand_side(
            time, position_and_velocity
        )

        "Return the right hand side of the ODE."
        return np.array(
            [
                current_state["v_x"],
                current_state["v_y"],
                current_state["a_x"],
                current_state["a_y"],
            ]
        )


    def export_readout(self, path, name="export"):
        """!Export the full readout of the trajectory to a csv file.
        @param path: Path to the csv file.
        @param name: Name of the csv file.
        """
        csv_file_path = path + "\ " + name + ".csv"
        self.readout.to_csv(csv_file_path, index=False, sep=";", decimal=",")
        print(f"DataFrame exported to {csv_file_path}")
        
    def export_data_to_hdf5(trajectory, rocket, readout_df, hdf_file):
        '''it would be nice to genrate a unique rocket id -> maybe one making it easy to see which parameters are being simulated
        rocket_group_name = f"rocket {rocket.id}"
        '''
        id = count_top_level_groups(hdf_file)
        rocket_group_name = f"rocket {str(id)}"
        group = hdf_file.create_group(rocket_group_name)
    
        # Save trajectory data
        trajectory_group = group.create_group("trajectory")
        dset_time = trajectory_group.create_dataset("time", data=trajectory.t)
        dset_time.attrs["description"] = "Time steps of the rocket trajectory in seconds"
    
        dset_states = trajectory_group.create_dataset("states", data=trajectory.y)
        dset_states.attrs["description"] = (
            "Rocket state vectors over time: rows = [x, y, vx, vy], columns = time steps"
        )
        dset_states.attrs["state_order"] = ["x", "y", "vx", "vy"]
    
        # Save rocket metadata as attributes
        metadata_group = group.create_group("metadata")

        allowed_keys = {"Diameter", "Length", "mass", "burn_time"} 
        for key, value in rocket.state.items():
            if key in allowed_keys:
                metadata_group.attrs[key] = value               
            
        # Save readout data
        readout_group = group.create_group("readout")
        for column in readout_df.columns:
            readout_group.create_dataset(column, data=readout_df[column].values)
    
