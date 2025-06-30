from hytempo.core import models
class Component:
    """! Base class for all components in the rocket
    Only models the weight and the name of the component.
    """

    def __init__(
        self, mass: float, name: str, hulltube: bool = True, length: float = 0
    ):
        """! Constructor for the Component class
        @param weight: Weight of the component in kg
        @param name: Name of the component
        @param hulltube: Specifies if the component is covered by the hulltube, if TRUE the a hulltube section with the length of the part will be created.
        @param length: Length of the component in m
        @Attention: Only specify the length if the component adds to the length of the rocket! Otherwise leave it at the default value of 0.
        """
        self.parameters = {"mass": mass,
                            "name": name,
                            "length": length,
                            "in_hulltube": hulltube}
        self.state = {"time": 0}

    def get_mass(self):
        """! Returns the weight of the component
        @return: Weight of the component in kg"""
        return self.parameters["mass"]

    def get_length(self):
        """! Returns the length of the component that contributes to the overall length of the rocket.
        @return: Length of the component in m"""
        if (
            self.parameters["in_hulltube"] is True
        ):  # check if the component is covered by the hulltube
            return 0
        return self.parameters["length"]

    def get_hull_length(self):
        """! Returns the length of the hulltube covering the component.
        @return: Length of the component in m"""
        # check if the component is covered by the hulltube
        if (self.parameters["in_hulltube"] is False):  
            return 0
        return self.parameters["length"]

    def getState(self):
        """! Returns the state of the component as a dict
        @param hdf5_group: HDF5 group to which the state should be written
        @return: State of the component as a dict"""
        return self.state
    
    def getParameters(self):
        """! Returns the parameters of the component
        @return: Parameters of the component as a dict"""
        return self.parameters


class Wetted_part(Component):
    """! Class for modelling wetted parts
    This class is used to model wetted parts like the injection system. It inherits from the Component class and adds method to modell the state changes of the fluid."""

    def __init__(
        self,
        mass: float,
        name: str,
        length: float,
        input: Component,
        model: models.Model,
        hulltube: bool = True,
    ):
        """!Constructor for the Wetted_part class
        @param weight: Weight of the wetted part in kg
        @param name: Name of the wetted part
        @param length: Length of the wetted part in m, only specify if the length of the wetted part contributes to the length of the rocket like in a structural tank
        @param input: Component from which the fluid is injected into the wetted part
        @param model: Model for the state changes of the fluid
        @return: Instance of the Wetted_part class
        @Attention: Only specify the length if the wetted part adds to the length of the rocket! Otherwise leave it at the default value of 0.
        """
        # initialize the parameters and states of the wetted part
        super().__init__(mass=mass, 
                         name=name, 
                         length=length, 
                         hulltube=hulltube)
        self.parameters["fluid"] = input.get_fluid() # extend the paramters with the fluid
        self.input_state = {}
        self.state = {}

        # set the model for the wetted part
        if not isinstance(model, models.Model):
            raise ValueError("Error: Model must be an instance of the Model class")
        self.model = model

        #check if the input component is a tank or a wetted part
        if (isinstance(input, Tank) == 0 and 
            isinstance(input, Wetted_part) == 0):
            raise ValueError("Error: Input component must be a tank or a wetted part")
        # set the input component
        self.input = input

    def updateState(self, calling_state: dict):
        """! Updates the state of the fluid at the output of the component
        This method is used to get the state of the fluid at the output of the component. 
        It is used to model the state changes of the fluid.
        @return: Dict containing the state of the fluid at the output of the component
        """
        # update time
        self.state["time"] = calling_state["time"] 
        
        # get state of the input component 
        self.input_state = self.input.updateState(self.state)  

        # apply model to calculate the state of the fluid at the output
        self.state = self.model.apply_model(self.input_state)  

        return self.state

    def get_fluid(self):
        """! Returns the species of the fluid in the component
        @return: Species of the fluid in the component
        """
        return self.input.get_fluid()


class Tank(Component):
    """! Class for modelling tanks
    """
    def __init__(self, 
                 name:str,
                 mass: float,
                 volume:float, 
                 fluid:str,
                 fluid_mass:float, 
                 pressure:float, 
                 temperature:float,
                 tank_model:models.Model,
                 input:Component=None, 
                 length: float = 0,
                 hulltube:bool = True):
        """! Constructor for the Tank class
        @param name: Name of the tank
        @param weight: Weight of the tank in kg
        @param volume: Volume of the tank in m^3
        @param fluid: Species of the fluid in the tank
        @param fluid_mass: Mass of the fluid in the tank in kg
        @param pressure: Pressure in the tank in Pa
        @param temperature: Temperature in the tank in K
        @param density: Density of the fluid in the tank in kg/m^3
        @param tank_model: Model for the state changes of the fluid
        @param input: Component from which the fluid is injected into the tank, optional and defaults to None
        @param length: Length of the tank in m, only specify if the length of the tank contributes to the length of the rocket like in a structural tank, optional and defaults to 0
        @return: Instance of the Tank class
        @Attention: Only specify the length if the tank adds to the length of the rocket! Otherwise leave it at the default value of 0.
        """
        # initialize the parameters and states of the tank
        self.parameters = {"name": name,
                           "mass": mass,
                            "volume": volume,
                            "fluid": fluid,
                            "length": length,
                            "volume": volume,
                            "init_pressure": pressure,
                            "init_fluid_mass": fluid_mass,
                            "in_hulltube":hulltube}
        self.state= {"time":0,
                    "fluid_mass":fluid_mass,
                    "pressure":pressure,
                    "temperature":temperature,
                    "massflow":0}
        self.output_state = {"massflow":0,
                             "temperature":0,
                             "pressure":0}
        
        # set the output modell
        self.tank_model = tank_model
        # set the pressurant input component if provided
        if not isinstance(tank_model, models.Model):
            raise ValueError("Error: Model must be an instance of the Model class")
        self.input = input

    def get_mass(self):
        """! Returns the weight of the component including the fluid in the tank
        @return: Weight of the component in kg
        """
        return self.parameters["mass"] + self.state["fluid_mass"]

    def get_fluid_mass(self):
        """! Returns the mass of the fluid in the tank
        @return: Mass of the fluid in the tank in kg
        """
        return self.state["fluid_mass"]

    def get_dry_mass(self):
        """! Returns the dry mass of the tank
        @return: Dry mass of the tank
        """
        return self.parameters["mass"]

    def updateState(self, calling_state: dict):
        """! Returns the state of the fluid at the output of the tank and updates the state of the tank
        @param calling_state: State of the component calling the method
        @return: Dict containing the state of the fluid at the output of the tank
        """
        #update the time of the tank state
        dt = calling_state["time"] - self.state["time"] # calculate time step
        self.state["time"] = calling_state["time"] # update time
        # check if there is an input component 
        if self.input is not None: 
            # tank is propellant tank
            # check if the fluid mass is sufficient
            if self.state['massflow']*dt < self.state["fluid_mass"]:
                # enough propellant is available, udate the state of the tank and provide massflow
                self.output_state = self.tank_model.apply_model(self.state) # apply flow model  
                self.state["fluid_mass"] = self.state["fluid_mass"] - self.output_state["massflow"]*dt  # update fluid mass
                #update internal state for dataexport
                self.state["massflow"] = self.output_state["massflow"]
                self.state["temperature"] = self.output_state["temperature"]
                self.state["pressure"] = self.output_state["pressure"]
            else:
                # not enough propellant is available, set output state to zero and proceed to empty the pressurant tank
                self.state["massflow"]=0
                self.state["fluid_mass"] = 0
                self.state["pressure"] = 0
                self.state["temperature"] = 0
                self.output_state = {"massflow":0,"temperature":0,"pressure":0}
                #call the get state method of the pressurant tank to empty it
                #the massflow of the pressurant is not processed further as it produces no thrust
                #dummy = self.input.updateState(self.state)
        else:
            # tank is pressurant tank, no input component 
            #check if there is fluid in the tank
            if self.state['massflow']*dt < self.state["fluid_mass"]:
                # enough pressurant is available, update the state of the tank and provide massflow
                self.output_state = self.tank_model.apply_model(self.state) # apply flow model  
                self.state["fluid_mass"] = self.state["fluid_mass"] - self.output_state["massflow"]*dt  # update fluid mass
            else: 
                # not enough pressurant is available, set output state to zero
                self.state["massflow"]=0
                self.state["fluid_mass"] = 0
                self.state["pressure"] = 0
                self.state["temperature"] = 0
                self.output_state = {"massflow":0,"temperature":0,"pressure":0}
        return self.output_state    
    
    def get_fluid(self):
        """! Returns the species of the fluid in the tank
        @return: Species of the fluid in the tank"""
        return self.parameters["fluid"]
