import os

import matplotlib as mpl
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import h5py
from hytempo.core import data_handling

class Plotter:
    """ Base Class for plotter classes"""

    def __init__(self, *file_paths):
        """Initialize plotter by specifying an arbitrary number of file paths for the underlying rocket(s)"""
        self.file_paths = file_paths

        self.rockets = data_handling.read_hdf_to_dict(*file_paths)

    def list_rockets(self):
        """ Return a list of all rockets """
        return list(self.rockets.keys())

    def get_chosen_rockets(self, choose_rockets=None):
        """ Return the rockets that were chosen by the parameter choose_rockets
                @param choose_rockets:  A single integer/string or a (mixed) iterable of strings and integers:
                                        interpreted as indices/keys of the rockets to be returned.
                                        Default: return all rockets
        """
        chosen_rockets = {}
        keys = self.list_rockets()

        # Try to iterate over choice parameter
        try:
            for cpar in choose_rockets:
                if isinstance(cpar, int):
                    chosen_rockets[keys[cpar]] = self.rockets[keys[cpar]]
                elif isinstance(cpar, str):
                    chosen_rockets[cpar] = self.rockets[cpar]

        # If not an iterable...
        except TypeError:
            cpar = choose_rockets
            if isinstance(cpar, int):
                chosen_rockets[keys[cpar]] = self.rockets[keys[cpar]]
            elif isinstance(cpar, str):
                chosen_rockets[cpar] = self.rockets[cpar]
            elif cpar is None:
                chosen_rockets = self.rockets
            else:
                raise ValueError("Invalid argument, cannot choose rockets!")

        return chosen_rockets

class TrajectoryPlotter(Plotter):

    def __init__(self,*file_paths):
        """Initialize plotter by specifying an arbitrary number of files for the underlying rocket(s)"""
        Plotter.__init__(self, *file_paths)

    def plot_over_time(self,
                       choose_rockets=None,
                       export_path=None):
        """Plot trajectory data  over time
        @param choose_rockets:  When int or list of ints is given, interpret as indices.
                                If list of strings, interpret as list of keys. Default: return all rockets
        """

        # Initialize plot
        f = plt.figure()
        ax_altitude = f.add_subplot(311)
        ax_velocity = f.add_subplot(312)
        ax_mach = f.add_subplot(313)

        # Plot trajectory for each rocket
        plot_rockets = self.get_chosen_rockets(choose_rockets)
        lines = []
        labels = []

        for key, rocket in plot_rockets.items():
            time = rocket["state"]["time"]
            altitude = rocket["state"]["y"]
            velocity_x = rocket["state"]["v_x"]
            velocity_y = rocket["state"]["v_y"]
            Ma = rocket["state"]["Ma"]
            velocity = np.sqrt(velocity_x ** 2 + velocity_y ** 2)

            l1, = ax_altitude.plot(time, altitude, label=key)
            l2, = ax_velocity.plot(time, velocity, label=key)
            l3, = ax_mach.plot(time, Ma, label=key)
            # Only collect one line per rocket for the legend
            lines.append(l1)
            labels.append(key)

        # Add auxiliary plot elements
        ax_altitude.set_ylabel("Altitude in m")
        ax_velocity.set_ylabel("Velocity in m/s")
        ax_mach.set_ylabel("Mach Number")
        ax_mach.set_xlabel("Time in s")

        # Create a common legend for all subplots
        f.legend(lines, labels, loc='upper right', bbox_to_anchor=(0.98, 0.98))

        # Show and export plot
        f.tight_layout()
        if export_path is None:
            f.savefig("transient_plot.png",dpi = self.dpi)
        else:
            f.savefig(export_path,dpi = self.dpi)

        # Return figure, in case the user wants to modify it
        return f

    def plot_trajectory(self,
                        choose_rockets=None,
                        export_path=None):
        """Plot spatial coordinates of a trajectory """

        # Initialize plot
        f = plt.figure()
        ax = f.add_subplot(111)

        # Plot trajectory for each rocket
        plot_rockets = self.get_chosen_rockets(choose_rockets)

        for key, rocket in plot_rockets.items():
            x = rocket["state"]["x"]
            y = rocket["state"]["y"]
            ax.plot(x, y, label=key )

        # Add auxiliary plot elements
        ax.set_xlabel("Downrange Distance [m]")
        ax.set_ylabel("Altitude [m]")
        # Set limits from 0 to 1.1 times the maximum value
        all_y = np.concatenate([rocket["state"]["y"] for rocket in plot_rockets.values()])
        ax.set_ylim(0, np.nanmax(all_y) * 1.1)
        all_x = np.concatenate([rocket["state"]["x"] for rocket in plot_rockets.values()])
        ax.set_xlim(0, np.nanmax(all_x) * 1.1)
        ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
        ax.grid()

        # Show and export plot
        f.tight_layout()
        if export_path is None:
            f.savefig("trajectory_plot.png",dpi=300)
        else:
            f.savefig(export_path,dpi=300)

        # Return figure, in case the user wants to modify it
        return f


class CorrelationPlotter(Plotter):
    """ A plotter class that plots the correlation coefficients of a performance metric and an arbitrary number of
        other rocket attributes.
    """
    def __init__(self, *file_paths):
        """Initialize plotter by specifying an arbitrary number of file paths for the underlying rocket(s)"""
        Plotter.__init__(self, *file_paths)
        raise NotImplemented("Correlation Plotter is not implemented!")

class PerformancePlotter(Plotter):
    """A plotter class that serves to plot rocket performance over arbitrary metrics."""

    def __init__(self,*file_paths):
        """Initialize plotter by specifying an arbitrary number of files for the underlying rocket(s)"""
        Plotter.__init__(self, *file_paths)

    def plot_1D(self,
                x:str,
                y:str or list,
                xlabel:str=None,
                ylabel:str=None,
                export_path=None):
        """Plot performance metric y over metric x. Specify metrics in the format 'key1.key2. ... .keyN' """

        # Extract metric x
        xList = x.split(".")

        # Recursively adress dict entry
        xData = np.zeros((len(self.rockets, )))
        for i, rocket in enumerate(self.rockets.values()):
            try:
                temp = rocket
                for key in xList:
                    temp = temp[key]
                xData[i] = temp
            except KeyError as e:
                xData[i] = np.nan

        # Setup Plot
        #set matplotlib parameters for latex, font size and line width
        mpl.rcParams["text.usetex"] = True
        mpl.rcParams["font.size"] = 22
        mpl.rcParams["lines.linewidth"] = 3 
        mpl.rcParams["figure.figsize"] = (10, 8)
        f = plt.figure()

        ax = f.add_subplot(111)
        # check if y is a list or a single string
        if isinstance(y, str):
            yList = [y]
        else :
            yList = y

        for y_item in yList: 
            # Extract metric y
            yNameList = y_item.split(".")

            # Recursively adress dict entry
            yData = np.zeros((len(self.rockets, )))
            for i, rocket in enumerate(self.rockets.values()):
                try:
                    temp = rocket
                    for key in yNameList:
                        temp = temp[key]
                    yData[i] = temp
                except KeyError as e:
                    yData[i] = np.nan

            # Remove nan values and order by x
            mask = ~np.isnan(xData) & ~np.isnan(yData)
            xData = xData[mask]
            yData = yData[mask]

            ind = np.argsort(xData)
            xData = xData[ind]
            yData = yData[ind]

            # Plot
            ax.plot(xData, yData,label=y_item)

        if xlabel is None:
            ax.set_xlabel(f"{x}")
        else:
            ax.set_xlabel(xlabel)
        if ylabel is None:
            ax.set_ylabel(f"{y}")
        else:
            ax.set_ylabel(ylabel)
        ax.grid()
        ax.set_xlim(np.nanmin(xData), np.nanmax(xData))
        ax.set_ylim(np.nanmin(yData)*0.95, np.nanmax(yData)*1.05)
        # Use scientific notation for axis labels
        ax.ticklabel_format(style='sci', axis='both', scilimits=(0,0))
        # Adjust the offset text position for better appearance
        ax.xaxis.get_offset_text().set_fontsize(18)
        ax.yaxis.get_offset_text().set_fontsize(18)
        f.tight_layout()
        if export_path is None:
            f.savefig("performance_plot_1D.png",dpi=300)
        else:
            f.savefig(export_path,dpi=300)

        # Return figure, in case the user wants to modify it
        return f


    def plot_2D(self,
                x:str,
                y:str,
                z:str,
                xlabel:str=None,
                ylabel:str=None,
                zlabel:str=None,
                export_path=None):
        """Plot performance metric z over metrics x and y . Specify metrics in the format 'key1.key2. ... .keyN' """

        # Extract metric x
        xList = x.split(".")

        # Recursively adress dict entry
        xData = np.zeros((len(self.rockets, )))
        for i, rocket in enumerate(self.rockets.values()):
            try:
                temp = rocket
                for key in xList:
                    temp = temp[key]
                xData[i] = temp
            except KeyError as e:
                xData[i] = np.nan

        # Extract metric y
        yList = y.split(".")

        # Recursively adress dict entry
        yData = np.zeros((len(self.rockets, )))
        for i, rocket in enumerate(self.rockets.values()):
            try:
                temp = rocket
                for key in yList:
                    temp = temp[key]
                yData[i] = temp
            except KeyError as e:
                yData[i] = np.nan

        # Extract metric z
        zList = z.split(".")

        # Recursively adress dict entry
        zData = np.zeros((len(self.rockets, )))
        for i, rocket in enumerate(self.rockets.values()):
            try:
                temp = rocket
                for key in zList:
                    temp = temp[key]
                zData[i] = temp
            except KeyError as e:
                zData[i] = np.nan

        # Remove any nan values from all arrays
        for i, (xx, yy, zz) in enumerate(zip(xData, yData, zData)):
            if np.isnan(xx) or np.isnan(yy) or np.isnan(zz):
                xData[i] = np.nan
                yData[i] = np.nan
                zData[i] = np.nan

        xData = xData[~np.isnan(xData)]
        yData = yData[~np.isnan(yData)]
        zData = zData[~np.isnan(zData)]

        # Plot
        # Set matplotlib parameters for latex, font size and line width
        mpl.rcParams["text.usetex"] = True
        mpl.rcParams["font.size"] = 22
        #set figure size
        mpl.rcParams["figure.figsize"] = (10, 8)

        f = plt.figure()
        ax = f.add_subplot(111)

        tcf = ax.tricontourf(xData, yData, zData)

        cb = f.colorbar(tcf)

        if xlabel is None:
            ax.set_xlabel(f"{x}")
        else:
            ax.set_xlabel(xlabel)
        if ylabel is None:
            ax.set_ylabel(f"{y}")
        else:
            ax.set_ylabel(ylabel)
        if zlabel is None:
            cb.set_label(z)
        else:
            cb.set_label(zlabel)
        # Use scientific notation for axis labels
        ax.ticklabel_format(style='sci', axis='both', scilimits=(0,0))
        # Adjust the offset text position for better appearance
        ax.xaxis.get_offset_text().set_fontsize(18)
        ax.yaxis.get_offset_text().set_fontsize(18)
        f.tight_layout()
        if export_path is None:
            f.savefig("performance_plot_2D.png",dpi=300)
        else:
            f.savefig(export_path,dpi=300)

        # Return figure, in case the user wants to modify it
        return f
    def plot_2D_Slice(self,
                x:str,
                y:str,
                value:str,
                fixed_params:dict,
                z:str= None,
                xlabel:str=None,
                ylabel:str=None,
                value_label:str=None,
                zlabel:str=None,
                export_path=None):
        """ Plot 2 D slices of a n dimensional space."""
        # ========== Perform input checks ==============
        # get the dimensionality of the input data 

        # fixed parameters and singular slice mode

        # fixed parameters and multiple slices mode


        # ========== Extract data from dicts ==============
        
        # ========== Create continous hyperplane ==========

        # ========== Create 2D plots ==============
        

class OneD_Plotter:
    """Class to plot the trajectories and other data related to the simulation."""

    def __init__(self, trajectory):
        """Constructor. Takes a trajectory as input.
        @param trajectory (_type_): Trajectory as returned by the TrajectoryEstimator / scipy.integrate.solve_ivp.
        """
        self.trajectory = trajectory

    def plot_trajectory_positions(self):
        """Plots the trajectory of the rocket in the x-y plane."""
        # plt.rcParams["text.usetex"] = True
        mpl.rcParams["figure.dpi"] = 300
        fig, ax = plt.subplots()
        ax.plot(self.trajectory.y[0], self.trajectory.y[1])
        ax.set_xlabel(r"downrange")
        ax.set_ylabel(r"altitude")
        ax.set_title(r"Trajectory of the rocket")
        plt.show()

    def plot_normal_velocity(self):
        """Plots the normal velocity of the rocket over time."""
        # plt.rcParams["text.usetex"] = True
        mpl.rcParams["figure.dpi"] = 300
        fig, ax = plt.subplots()
        normal_velocities = np.sqrt(
            self.trajectory.y[2] ** 2 + self.trajectory.y[3] ** 2
        )
        ax.plot(self.trajectory.t, normal_velocities)
        ax.set_xlabel(r"time")
        ax.set_ylabel(r"velocity")
        ax.set_title(r"Normal velocity of the rocket")
        plt.show()


class TwoD_plotter:
    """! Class for plotting 2D data with contour lines and hatching for initial acceleration"""

    def __init__(
        self,
        initial_acceleration,
        criticalAcc,
        yaxis: str,
        yrange: list,
        xaxis: str,
        xrange: list,
    ):
        """! Constructor for the TwoD_plotter class
        @param initial_acceleration: 2D array with the initial acceleration values
        @param criticalAcc: Critical acceleration value
        @param yaxis: Label for the y-axis
        @param yrange: Range for the y-axis
        @param xaxis: Label for the x-axis
        @param xrange: Range for the x-axis
        @return: Instance of the TwoD_plotter class
        """
        self.extent = [xrange[0], xrange[-1], yrange[0], yrange[-1]]
        self.CRITICAL_ACCELERATION = criticalAcc
        self.initial_acceleration = initial_acceleration
        self.xaxis = xaxis
        self.yaxis = yaxis

    def plot_2d(self, data, name: str):
        """! Plot the 2D data with contour lines and hatching for the initial acceleration
        @param data: 2D array with the data to plot
        @param name: Name of the plot
        """
        data_plot = data.T
        initial_accelerations_plot = self.initial_acceleration.T
        # Define the color map
        data_colors = [
            "#c51b7d",
            "#de77ae",
            "#f1b6da",
            "#fde0ef",
            "#e6f5d0",
            "#b8e186",
            "#7fbc41",
            "#4d9221",
        ]
        data_cmap = mcolors.LinearSegmentedColormap.from_list(
            "my_colormap", data_colors
        )
        # plot the KDE: draw the function
        data_fig, data_ax = plt.subplots(figsize=(3.8, 3.0))
        data_im = data_ax.imshow(
            data_plot,
            origin="lower",
            cmap=data_cmap,
            extent=self.extent,
            aspect="auto",
        )
        # find the minimum and maximum without considering NaNs
        min_data = np.nanmin(data_plot)
        max_data = np.nanmax(data_plot)
        # draw the contour lines
        initial_acceleration_cs = data_ax.contourf(
            initial_accelerations_plot > self.CRITICAL_ACCELERATION,
            levels=[0, 0.5, 1],
            alpha=0,
            hatches=[".", ""],
            colors="none",
            extent=self.extent,
        )
        initial_acceleration_cset = data_ax.contour(
            initial_accelerations_plot,
            levels=[self.CRITICAL_ACCELERATION],
            linewidths=1,
            extent=self.extent,
            colors="red",
        )
        # draw the contour lines
        cset = data_ax.contour(
            data_plot,
            np.arange(min_data, max_data, (max_data - min_data) / 8),
            linewidths=1,
            extent=self.extent,
            colors="black",
        )
        data_ax.clabel(
            cset, inline=True, inline_spacing=20, fmt=r"$%1.1f$", fontsize=10
        )
        data_ax.clabel(
            initial_acceleration_cset,
            inline=True,
            inline_spacing=30,
            fmt="acc. %1.0f ",
            fontsize=10,
        )
        (
            acceleration_artists,
            acceleration_labels,
        ) = initial_acceleration_cs.legend_elements()
        acceleration_labels = [
            r"init. acc. $<"
            + str(self.CRITICAL_ACCELERATION)
            + r"\frac{m}{s^2}$",
            r"init. acc. $>"
            + str(self.CRITICAL_ACCELERATION)
            + r"\frac{m}{s^2}$",
        ]
        data_ax.legend(
            acceleration_artists,
            acceleration_labels,
            handleheight=2,
            framealpha=1,
            bbox_to_anchor=(1.3, 1),
            loc="upper left",
        )
        # draw the colorbar
        data_fig.colorbar(data_im, ax=data_ax, location="right")
        # add axis labels
        data_fig.suptitle(name)
        data_ax.set_xlabel(self.xaxis)
        data_ax.set_ylabel(self.yaxis)
        plt.show()