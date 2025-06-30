import ambiance
from hytempo.core import components, models
class Engine(components.Component):
    """! Base class for all engines in the rocket"""
    def get_length(self):
        """!
        @brief Returns the length of the engine
        @return length of the engine
        """
        return self.parameters["length"]

    def get_mass(self):
        """!
        @brief Returns the overall mass of the engine
        @return mass of the engine
        """
        return self.parameters["mass"]

    def thrust(self):
        """!
        @brief Returns the thrust of the engine
        @return thrust of the engine
        """
        isp = self.isp_model.apply_model(self.state,self.parameters)  # apply the model to get the isp
        return (
            self.state["massflow"] * isp * 9.81
        )  # return the thrust of the engine

class Liquid_engine(Engine):
    """! Class for a liquid engine"""

    def __init__(
        self,
        name: str,
        mass: float,
        expansion_ratio_nozzle: float,
        input_fuel: components.Component,
        input_oxidizer: components.Component,
        isp_model: models.Model,
        hulltube: bool = True,
        length: float = 0,
    ):
        """!
        @brief Constructor for the liquid engine
        @param name name of the engine
        @param mass mass of the engine
        @param expansion_ratio_nozzle expansion ratio of the nozzle
        @param input_fuel fuel component
        @param input_oxidizer oxidizer component
        @param isp_model isp model
        @param length length of the engine, only specify if the engine contributes to the length of the rocket and there is no hull tube over the engine
        """
        # Initialize the parameters and state of the engine 
        self.parameters = {
            "name": name,
            "length": length,
            "mass": mass,
            "expansion_ratio_nozzle": expansion_ratio_nozzle,
            "in_hulltube": hulltube,
            "fuel": input_fuel.get_fluid(),
            "oxidizer": input_oxidizer.get_fluid()}
        self.state = {
            "time": 0,
            "massflow_fuel": 0,
            "temperature_fuel": 0,
            "pressure_fuel": 0,
            "massflow_ox": 0,
            "temperature_ox": 0,
            "pressure_ox": 0,
            "massflow": 0,
            "O/F": 0,
            "P_cc": 0,
            "P_amb": 0}
        self.input_fuel = input_fuel
        self.input_oxidizer = input_oxidizer
        self.isp_model = isp_model

    def get_mass(self):
        """!
        @brief Returns the overall mass of the engine
        @return mass of the engine including propellant mass
        """
        return self.parameters["mass"]

    def updateState(self, calling_state: dict):
        """!
        @brief Returns the state of the engine
        @param calling_state state of the rocket
        @return state of the engine
        """
        # update the time
        self.state["time"] = calling_state["time"]  
        # get the state of the inputs
        fuel_state = self.input_fuel.updateState(self.state)  
        ox_state = self.input_oxidizer.updateState(self.state)
        self.state["massflow_fuel"] = fuel_state["massflow"]
        self.state["temperature_fuel"] = fuel_state["temperature"]
        self.state["pressure_fuel"] = fuel_state["pressure"]
        self.state["massflow_ox"] = ox_state["massflow"]
        self.state["temperature_ox"] = ox_state["temperature"]
        self.state["pressure_ox"] = ox_state["pressure"]
        #calculate the overall mass flow rates and other parameters
        self.state["massflow"] = ( self.state["massflow_fuel"] + self.state["massflow_ox"])
        try:
            self.state["O/F"] = (self.state["massflow_ox"] / self.state["massflow_fuel"]) 
        except ZeroDivisionError:  # prevent div by zero if the fuel mass flow rate is zero
            self.state["O/F"] = 0
        # set the chamber pressure to the minimum of the fuel and oxidizer pressure
        self.state["P_cc"] = min(self.state["pressure_ox"], self.state["pressure_fuel"])  

        try:
            self.state["P_amb"] = ambiance.Atmosphere(calling_state["y"]).pressure[0]  # get the ambient pressure
        except:
            self.state["P_amb"] = 10e-2


class Solid_engine(Engine):
    """! Class for a solid engine"""
    pass  # Solid engines are not implemented yet, but this class is here for future use

class Hybrid_Engine(Engine):
    """! Class for a hybrid engine"""
    pass # Hybrid engines are not implemented yet, but this class is here for future use
