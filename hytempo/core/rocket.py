from math import cos, radians, sin, tan

import ambiance
import numpy as np

from hytempo.core import components, engine, models


class Rocket(components.Component):
    def __init__(self,
                 name:str,
                 parameters:dict,
                 component_list:list,
                 tank_list:list,
                 engine_list:list,
                 drag_model:models.Model,
                 rail_height:float):
        """!Constructor for the rocket.
        @param name: Name of the rocket.
        @param diameter: Diameter of the rocket.
        @param launch_angle: Launch angle of the rocket.
        @param component_list: List of components of the rocket.
        @param tank_list: List of tanks of the rocket.
        @param engine_list: List of engines of the rocket.
        @param drag_model: Drag model of the rocket.
        @param rail_height: Height of the rail. Default is 5.
        @param burn_time: Burn time of the rocket. Default is 0.
        @param of: O/F ratio of the rocket.Default is 0.0.
        """
        self.name = name
        self.onrail = True
        self.drag_model = drag_model
        self.tank_list = tank_list
        self.component_list = component_list
        self.engine_list = engine_list
        self.rail_height = rail_height
        #initialize the paramter dict
        self.parameters = {"Length":self.get_length(),
                           "L/D":self.get_length()/parameters["diameter"],
                           "Frontal_area":parameters["diameter"]**2*np.pi/4,
                           "Diameter":parameters["diameter"],
                           "launchAngle":parameters["launchAngle"],
                           "burnTime":parameters["burnTime"],
                           "of":parameters["of"],
                           "chamberPressure":parameters["chamberPressure"],
                           "expansionRatio":parameters["expansionRatio"],
                           "pressurantTankPressure":parameters["pressurantTankPressure"],
                           "thrust":parameters["thrust"]}
        #add the provided parameters to the parameter dict
        self.parameters.update(parameters)
        #initialize the state of the rocket
        self.state = {"time":0,
                    "O/F": parameters["of"],
                    "mass":self.get_mass(),
                    "thrust":0,
                    "drag":0,
                    "angle": parameters["launchAngle"],
                    "x":0,
                    "y":0,
                    "v_x":0,
                    "v_y":0,
                    "a_x":0,
                    "a_y":0,
                    "Ma":0,
                    "onRail":True
                    }
    def get_length(self):
        """!Get the length of the rocket.
        @return: Length of the rocket in m."""
        length = 0
        for component in self.component_list:
            length += component.get_length()
        for tank in self.tank_list:
            length += tank.get_length()
        for engine in self.engine_list:
            length += engine.get_length()
        return length

    def get_of(self):
        """!Get the O/F ratio of the rocket.
        @return: O/F ratio of the rocket."""
        return self.state["O/F"]

    def get_eps(self):
        """!Get the O/F ratio of the rocket.
        @return: O/F ratio of the rocket."""
        return self.engine_list[0].state["expansion_ratio_nozzle"]

    def get_tank_pressure(self):
        """!Get the pressure of the tanks of the rocket.
        @return: Pressure of the tanks of the rocket."""
        return self.tank_list[0].state["pressure"]

    def compute_right_hand_side(
        self, time: float, position_and_velocity: np.ndarray
    ):
        """! Computes the right hand side of the ODE using the current state of the rocket.
        @param time: Time of the state.
        @param position_and_velocity: Position and velocity of the state.
        @return: Right hand side of the ODE in the format of [v_x,v_y,a_x,a_y]."""
        "Update the state of the rocket."
        self.state["time"] = time
        self.state["x"] = position_and_velocity[0]
        self.state["y"] = position_and_velocity[1]
        self.state["v_x"] = position_and_velocity[2]
        self.state["v_y"] = position_and_velocity[3]
        try:
            self.state["Ma"] = (np.sqrt(self.state["v_x"] ** 2 + self.state["v_y"] ** 2)/
                                ambiance.Atmosphere(self.state["y"]).speed_of_sound[0])
        except:
            self.state["Ma"] = (np.sqrt(self.state["v_x"] ** 2 + self.state["v_y"] ** 2)/ 
                                ambiance.Atmosphere(80000).speed_of_sound[0])
        if self.state["onRail"] == False:
            # calculate the angle of the rocket from the speed components
            self.state["angle"] = (np.arctan2(self.state["v_y"], self.state["v_x"]) * 180 / np.pi)

        for engine in self.engine_list:
            engine.updateState(self.state)
        self.state["mass"] = self.get_mass()
        self.state["thrust"] = self.compute_thrust()
        self.state["drag"] = self.compute_drag()
        # Compute the normal acceleration of the rocket.
        normal_accelaration = (
            self.state["thrust"] - self.state["drag"]
        ) / self.state["mass"]
        # Split normal acceleration into x and y components.
        if self.state["onRail"] == False:
            self.state["a_y"] = (
                sin(radians(self.state["angle"])) * normal_accelaration - 9.81
            )
            self.state["a_x"] = (
                cos(radians(self.state["angle"])) * normal_accelaration
            )
       
        else:
            self.state["a_y"] = (
                sin(radians(self.state["angle"])) * normal_accelaration - 9.81
            )
            self.state["a_x"] = self.state["a_y"] / tan(
                radians(self.state["angle"])
            )
        return self.state

    def get_mass(self):
        """!Get the mass of the rocket.
        @return: Mass of the rocket in kg.
        """
        weight = 0
        for component in self.component_list:
            weight += component.get_mass()
        for tank in self.tank_list:
            weight += tank.get_mass()
        for engine in self.engine_list:
            weight += engine.get_mass()
        return weight

    def get_dry_mass(self):
        """!Get the dry mass of the rocket.
        @return: Dry mass of the rocket in kg.
        """
        weight = 0
        for component in self.component_list:
            weight += component.get_mass()
        for tank in self.tank_list:
            weight += tank.get_dry_mass()
        for engine in self.engine_list:
            weight += engine.get_dry_mass()
        return weight

    def compute_thrust(self):
        """!Computes the thrust of the rocket.
        @return: Thrust of the rocket in N."""
        thrust = 0
        for engine in self.engine_list:
            thrust += engine.thrust()
        return thrust

    def compute_drag(self):
        """! Computes the drag of the rocket
        This method computes the drag of the rocket based on the current state of the rocket and the drag model.
        @return: Drag of the rocket in N
        """
        try:
            density = ambiance.Atmosphere(self.state["y"]).density[0]
        except:
            density = 10e-6
            print(
                "Warning: The altitude is out of the atmosphere model range. The density is set to 10e-6 kg/m^3."
            )

        return (
            self.drag_model.apply_model(self.state, self.parameters)
            * self.parameters["Frontal_area"]
            * 0.5
            * density
            * (self.state["v_x"] ** 2 + self.state["v_y"] ** 2)
        )
