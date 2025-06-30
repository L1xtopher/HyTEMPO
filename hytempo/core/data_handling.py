import os
import h5py
import pandas as pd
import numpy as np
from collections import defaultdict
from datetime import datetime
from hytempo.core.components import Component

class Observer:
    """
    Represents the single recipient (Observer).
    It registers with multiple information sources and pulls data when needed.
    """
    def __init__(self,
                 safeFile: h5py.File,
                 rocket: Component):
        """
        Initializes the Observer with a name and an empty list of sources.
        @param safeFile: The file to save the data to.
        """
        self.file = safeFile
        self.rocket = rocket
        self.sources = []
        self.received_updates = {} # To store the latest data from each source
        #add the information sources 
        self.rocket_group_name = self.add_PrimaryNodeSource(self.rocket)
        self.add_ComponentNodeSources(self.rocket)
        self.add_TankNodeSources(self.rocket)
        self.add_EngineNodeSources(self.rocket)

        #init the state datasets
        for source in self.sources:
            #get the state
            data_dict = source[0].getState()

            #get the hdf_group
            hdf_group = self.file[source[1]]

            # get the keys from the dict
            keys = list(data_dict.keys()) 
            
            #transform dict into array
            values = np.array(list(data_dict.values()), dtype='float64') 
            
            # Write the received data to the corresponding HDF5 group
            dataset = hdf_group.create_dataset(
                "state",
                shape=(1, len(values)),
                maxshape=(None, len(values)),
                dtype='float64'
            )
            #dataset.resize((1, len(values)))
            dataset[0, :] = values
            
            # Store the keys as an attribute for column headers
            dataset.attrs["columns"] = np.array(keys, dtype='S')
            
    def add_PrimaryNodeSource(self, rocket: Component):
        """
        Registers a rocket node source with this recipient.
        """        
        # Create and name the rocket group based on the number of top-level groups
        id = count_top_level_groups(self.file)
        rocket_group_name = f"rocket {str(id)}"
        rocket_group = self.file.create_group(rocket_group_name)
        
        # Add rocket parameters as attributes
        for key, value in rocket.parameters.items():
            rocket_group.attrs[key] = value

        # Register the source and the rocket group in the HDF5 file
        self.sources.append([rocket, rocket_group_name])
        return rocket_group_name
    
    def add_ComponentNodeSources(self, rocket: Component):
        """
        Registers the components of the rocket as secondary sources.
        """
        # create a component group in the HDF5 file
        rocket_group = self.file[self.rocket_group_name]
        components_group = rocket_group.create_group("components")

        for component in rocket.component_list:
            #create a subgroup under the rocket group for the component in the HDF5 file
            component_group_name = component.parameters["name"]
            component_group = components_group.create_group(component_group_name)
            for key, value in component.parameters.items():
                component_group.attrs[key] = value
            #register component and its group as a source
            self.sources.append([component, component_group.name])

    
    def add_TankNodeSources(self, rocket: Component):
        """
        Registers the tanks of the rocket as secondary sources.
        """
        # create a tank group in the HDF5 file
        rocket_group = self.file[self.rocket_group_name]
        tanks_group = rocket_group.create_group("tanks")

        for tank in rocket.tank_list:
            #create a subgroup under the rocket group for the tank in the HDF5 file
            tank_group_name = tank.parameters["name"]
            tank_group = tanks_group.create_group(tank_group_name)
            for key, value in tank.parameters.items():
                tank_group.attrs[key] = value
            #register each tank and their group as a source
            self.sources.append([tank, tank_group.name])

    def add_EngineNodeSources(self, rocket: Component):
        """
        Registers the engines of the rocket as secondary sources.
        """
        # create an engine group in the HDF5 file
        rocket_group = self.file[self.rocket_group_name]
        engines_group = rocket_group.create_group("engines")

        for engine in rocket.engine_list:
            #create a subgroup under the rocket group for the engine in the HDF5 file
            engine_group_name = engine.parameters["name"]
            engine_group = engines_group.create_group(engine_group_name)
            for key, value in engine.parameters.items():
                engine_group.attrs[key] = value
            #register each engine and their group as a source
            self.sources.append([engine, engine_group.name])

    def remove_source(self, source: Component):
        """
        Unregisters an information source from this recipient.
        """
        if source in self._sources:
            self.sources.remove(source)
            print(f"[{self.name}]: Unregistered from source '{source.name}'")
            if source.name in self.received_updates:
                del self.received_updates[source.name]
        else:
            print(f"[{self.name}]: Not registered with source '{source.name}'")

    def pull_updates(self):
        """
        This is the 'update' method called by the recipient.
        It iterates through all registered sources and pulls their latest data.
        """
        for source in self.sources:
            current_data = source[0].getState()

            # Write the received data to the corresponding HDF5 group
            group = self.file[source[1]]
            write_state_to_hdf5(group, current_data)

    def calculateMetrics(self):
        """
        This extracts the performance metrics of the trajectory and stores it in a dataset that is added to a rocket group
        """

        # max velocity
        # get the columns for the state dataset
        columns = [col.decode() if isinstance(col, bytes) else col 
                   for col in self.file[self.rocket_group_name]["state"].attrs["columns"]]
        v_x_idx = columns.index("v_x")
        v_y_idx = columns.index("v_y")
        v_x = self.file[self.rocket_group_name]["state"][:, v_x_idx]
        v_y = self.file[self.rocket_group_name]["state"][:, v_y_idx]
        max_velocity = np.max(np.sqrt(v_x**2 + v_y**2))

        # max mach number
        ma_idx = columns.index("Ma")
        max_ma = np.max(self.file[self.rocket_group_name]["state"][:, ma_idx])

        # apogee (max y)
        y_idx = columns.index("y")
        y = self.file[self.rocket_group_name]["state"][:, y_idx]
        max_y = np.max(y)

        # wet and dry mass
        mass_idx = columns.index("mass")
        wet_mass = self.file[self.rocket_group_name]["state"][0, mass_idx]
        dry_mass = self.file[self.rocket_group_name]["state"][-1, mass_idx]

        # create a dataset that contains all of the metrics and add it to the rocket node
        metrics = np.array([max_velocity, max_ma, max_y, wet_mass, dry_mass], dtype='float64')
        metric_names = np.array(["max_velocity", "max_ma", "apogee", "wet_mass", "dry_mass"], dtype='S')
        ds = self.file[self.rocket_group_name].create_dataset("metrics", data=metrics)
        ds.attrs["columns"] = metric_names



def create_hdf5_file(name, overwrite=False):
    # Go two levels up from current file location
    base_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..")
    )
    results_dir = os.path.join(base_dir, "results")

    # Ensure 'results' directory exists
    os.makedirs(results_dir, exist_ok=True)

    # Ensure file has .h5 extension
    if not name.endswith(".h5"):
        name += ".h5"

    file_path = os.path.join(results_dir, name)

    # If file exists and overwrite is False, add timestamp
    if not overwrite and os.path.exists(file_path):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name_without_ext = name.rsplit(".", 1)[0]
        name = f"{name_without_ext}_{timestamp}.h5"
        file_path = os.path.join(results_dir, name)

    # Create the HDF5 file
    return h5py.File(file_path, "w")

def close_hdf5_file(file: h5py.File):
    """ Close an h5py file and return the file path for reading from the file later on. """
    file_path = file.filename

    file.close()

    return file_path

def createStateParameterGroup(hdf_file, rocket_group_name,rocket):
    """!Create a metadata group for the rocket in the HDF5 file.
    @param hdf_file: HDF5 file to create the metadata group in.
    @param rocket_group_name: Name of the rocket group.
    @param rocket: Rocket object containing metadata.
    @return: Metadata group object.
    """
    metadata_group = hdf_file[rocket_group_name].create_group("metadata")
    # Add rocket parameters as attributes
    for key, value in rocket.parameters.items():
        metadata_group.attrs[key] = value

def count_top_level_groups(hdf_file):
    """
    Counts the number of top-level groups in the given HDF5 file.

    Parameters:
        hdf_file (h5py.File): An open HDF5 file.

    Returns:
        int: The number of top-level groups.
    """
    return sum(1 for key in hdf_file.keys() if isinstance(hdf_file[key], h5py.Group))

def write_state_to_hdf5(hdf_group, data_dict):
    """Writes a dictionary of state parameters to an open HDF5 group."""
    # get the values from the dict
    values = np.array(list(data_dict.values()), dtype='float64')
    # Append new row to existing dataset
    dataset = hdf_group["state"]
    dataset.resize((dataset.shape[0] + 1), axis=0)
    dataset[-1,:] = values

def write_to_hdf5(hdf_group, data_dict):
    """
    Recursively writes data from a nested dictionary to an open HDF5 group or file.

    Parameters:
    - hdf_group: An open h5py.Group or h5py.File object.
    - data_dict: A nested dictionary where:
        - keys become group/dataset names
        - values can be:
            - primitives or numpy arrays → stored as datasets
            - dictionaries → stored as nested groups
            - tuples of (data, attrs_dict) for datasets with attributes
    """
    for key, value in data_dict.items():
        if isinstance(value, dict):
            # Recursively write nested groups
            subgroup = hdf_group.create_group(key)
            write_to_hdf5(subgroup, value)

        elif isinstance(value, tuple) and isinstance(value[0], np.ndarray) and isinstance(value[1], dict):
            # Dataset with attributes
            dataset = hdf_group.create_dataset(key, data=value[0])
            for attr_key, attr_val in value[1].items():
                dataset.attrs[attr_key] = attr_val

        elif isinstance(value, np.ndarray):
            # Simple dataset
            hdf_group.create_dataset(key, data=value)
        else:
            raise ValueError(f"Unsupported value type for key '{key}': {type(value)}")

def read_hdf_to_dict(*file_paths):
    """
        Imports multiple HDF5 files and stores their contents in a nested dictionary.

        Parameters:
        -----------
        file_paths : list of str
            List of paths to HDF5 files.

        Returns:
        --------
        dict
            Nested dictionary representing all top-level groups (with unique keys),
            subgroups, attributes, and datasets with column-based data.
        """
    result = {}
    name_counter = defaultdict(int)

    def process_group(group):
        """
        Recursively processes an HDF5 group into a nested dict.
        """
        data_dict = {}
        # Import group attributes (decode bytes if necessary)
        for attr_key, attr_val in group.attrs.items():
            if isinstance(attr_val, bytes):
                try:
                    data_dict[attr_key] = attr_val.decode('utf-8')
                except Exception:
                    data_dict[attr_key] = attr_val
            else:
                data_dict[attr_key] = attr_val

        # Iterate over items in the group
        for name, item in group.items():
            if isinstance(item, h5py.Group):
                # Subgroup: recurse
                data_dict[name] = process_group(item)
            elif isinstance(item, h5py.Dataset):
                # Dataset: load data according to 'columns' attribute
                cols = item.attrs.get('columns')
                arr = item[...]  # Load entire dataset
                if cols is None:
                    # No columns attribute: store raw array
                    data_dict[name] = arr
                else:
                    # Decode column names if they are bytes
                    try:
                        # Handle bytes in columns list
                        raw_cols = list(cols)
                        columns = [c.decode('utf-8') if isinstance(c, (bytes, bytearray)) else c for c in raw_cols]
                        arr = np.atleast_2d(arr)
                        if arr.shape[1] != len(columns):
                            raise ValueError(
                                f"Dataset '{name}' shape {arr.shape} doesn't match number of columns {len(columns)}"
                            )
                        # Map each column name to its data slice
                        col_dict = {columns[i]: arr[:, i] for i in range(len(columns))}
                        data_dict[name] = col_dict
                    except Exception:
                        # Fallback: store raw array
                        data_dict[name] = arr
        return data_dict

    # Process each file
    for path in file_paths:
        with h5py.File(path, 'r') as h5file:
            for grp_name, grp in h5file.items():
                # Manage duplicate top-level names
                name_counter[grp_name] += 1
                unique_name = grp_name if name_counter[grp_name] == 1 else f"{grp_name}_{name_counter[grp_name]}"
                # Process the group and store
                result[unique_name] = process_group(grp)

    return result


def write_rocket_metrics_to_hdf(metadata_group, sim, rocket, trajectory):
    """Writes rocket performance metrics as attributes into the metadata group."""
    rocket_metrics = {
        "apogee": sim.get_apogee(trajectory),
        "max_velocity": sim.get_max_velocity(trajectory),
        "max_mach_number": max(sim.readout["Ma"]),
        "wet_mass": rocket.get_mass(),
        "dry_mass": rocket.get_dry_mass(),
    }

    for key, value in rocket_metrics.items():
        metadata_group.attrs[key] = value


def extract_rocket_metrics(
    file_path,
    param_x="burn_time",
    param_y="Diameter",
    metrics=("apogee", "max_velocity", "max_mach_number")
):
    """
    Extracts rocket metadata and metrics from an HDF5 file.
    
    :param file_path: Path to the HDF5 file.
    :param param_x: Name of the first parameter (x-axis for plotting).
    :param param_y: Name of the second parameter (y-axis for plotting).
    :param metrics: Tuple of metric names to extract.
    :return: pandas DataFrame containing all extracted data.
    """
    results = []

    with h5py.File(file_path, "r") as hdf:
        for rocket_group in hdf:
            group = hdf[rocket_group]
            if "metadata" not in group:
                continue
            
            metadata = group["metadata"].attrs

            try:
                # Collect specified parameters and all requested metrics
                entry = {
                    param_x: metadata[param_x],
                    param_y: metadata[param_y],
                }
                for metric in metrics:
                    entry[metric] = metadata.get(metric, None)
                results.append(entry)
            except KeyError as e:
                print(f"Missing data in {rocket_group}: {e}")
                continue

    return pd.DataFrame(results)

