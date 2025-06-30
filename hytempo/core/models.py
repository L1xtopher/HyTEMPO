import numpy as np
from pycea import CEA
from scipy.interpolate import RegularGridInterpolator, interp1d


class Model:
    """!Abstract base class for all components in the model.
    This class serves as a template for all components in the model.
    It is not intended to be used directly but rather as an interface to the objects using the provided models
    """

    def apply_model(self, obj):
        """! Definition of the return function of the modelling function.
        This function is used to define the return function of the modelling function and is intended to be overwritten by the child class.
           @attention This function is to be treated as an abstract function and should not be used directly.
        """
        pass


class Scalar_Constant(Model):
    """!This class models a constant behaviour and returns the value given at initialization."""

    def __init__(self, value: float):
        """! Constructor of the constant model.
        @param value: The value to be returned by the model.
        """
        self.value = value

    def set_value(self, value: float):
        """! Function to set the value of the model.
        @param value: The value to be returned by the model.
        """
        self.value = value

    def apply_model(self, obj):
        """! Function to return the value of the model.
        @param obj: The object to be watched by the model. This object is not used by the constant model.
        @return The value of the model.
        """
        return self.value


class Scalar_LUT2D(Model):
    """! This class models a behaviour based on a 2D lookup table.
    This class models a behaviour based on a 2D lookup table. The table is given as a list with the input values as keys and the output values as values.
    """

    def __init__(
        self, table: np.array, xAxis: list, yAxis: list, x: str, y: str
    ):
        """!Constructor of the 2D lookup table model.
        Constructs the 2D lookup table model based on the given table and given axis values. The values are interpolated using a linear interpolation.
        @param table: Array of output values for the LUT
        @param xAxis: List of input values for the LUT along the x-axis (No of rows)
        @param yAxis: List of input values for the LUT along the y-axis (No of columns)
        @param x: Name of the x-axis variable in the watched object (i.e. the rocket)
        @param y: Name of the y-axis variable in the watched object (i.e. the rocket)
        """
        self.x = x
        self.y = y
        self.LUT = RegularGridInterpolator(
            [xAxis, yAxis], table, method="linear", bounds_error=True
        )

    def set_table(
        self, table: np.array, xAxis: list, yAxis: list, x: str, y: str
    ):
        """!Function to change the table of the model.
        Edits the 2D lookup table model based on the given table and given axis values. The values are interpolated using a linear interpolation.
        @param table: Array of output values for the LUT
        @param xAxis: List of input values for the LUT along the x-axis (No of rows)
        @param yAxis: List of input values for the LUT along the y-axis (No of columns)
        @param x: Name of the x-axis variable in the watched object (i.e. the rocket)
        @param y: Name of the y-axis variable in the watched object (i.e. the rocket)
        """
        self.x = x
        self.y = y
        self.LUT = RegularGridInterpolator(
            (xAxis, yAxis),
            table,
            method="linear",
            bounds_error=False,
        )
        return None

    def apply_model(self, input_state: dict, input_parameters: dict):
        """! Function to use the LUT to return a value.
        Returns the value of the LUT at the given input value.
         @param obj: The object to be watched by the model. The object must contain the variables given at initialization of the model.
        @return The output value of the LUT corresponding to the given input value.
        """
        # Search for the x value in the input_state and input_parameters
        if self.x in input_state:
            x_val = input_state[self.x]
        elif self.x in input_parameters:
            x_val = input_parameters[self.x]
        else:
            raise KeyError(f"{self.x} not found in input_state or input_parameters")
        # Search for the y value in the input_state and input_parameters
        if self.y in input_state:
            y_val = input_state[self.y]
        elif self.y in input_parameters:
            y_val = input_parameters[self.y]
        else:
            raise KeyError(f"{self.y} not found in input_state or input_parameters")
        return self.LUT([x_val,y_val])[0]


class Scalar_LUT1D(Model):
    """! This class models a behaviour based on a 1D lookup table.
    This class models a behaviour based on a 1D lookup table. The table is given as a list with the input values as keys and the output values as values.
    """

    def __init__(self, table: list, xAxis: list, x: str):
        """!Constructor of the 1D lookup table model
        Constructs the 1D lookup table model based on the given table and given axis values. The values are interpolated using a linear interpolation.
        @param table: List of output values for the LUT
        @param xAxis: List of input values for the LUT
        @param x: Name of the x-axis variable in the watched object (i.e. the rocket)
        """
        self.x = x
        self.LUT = interp1d(
            xAxis, table, kind="linear", fill_value="extrapolate"
        )

    def set_table(self, table: list, xAxis: list, x: str):
        """!Function to change the table of the model.
        Changes the 1D lookup table model based on the given table and given axis values. The values are interpolated using a linear interpolation.
        @param table: List of output values for the LUT
        @param xAxis: List of input values for the LUT
        @param x: Name of the x-axis variable in the watched object (i.e. the rocket)
        """
        self.x = x
        self.LUT = interp1d(
            xAxis, table, kind="linear", fill_value="extrapolate"
        )
        return None

    def apply_model(self, obj):
        """! Function to use the LUT to return a value.
        Returns the value of the LUT at the given input value.
        @param value: The input value for the LUT
        @return The output value of the LUT corresponding to the given input value.
        """
        return self.LUT(obj[self.x])[0]


class Scalar_Linear(Model):
    """! This class models a linear behaviour.
    This class models a linear behaviour. The model is given by the equation y = m*x + c.
    """

    def __init__(self, m: float, c: float, x: str):
        """! Constructor of the linear model.
        Constructs the linear model based on the given slope and offset.
        @param m: The slope of the linear model
        @param c: The offset of the linear model
        @param x: Name of the x-axis variable in the watched object (i.e. the rocket)
        """
        self.m = m
        self.c = c
        self.x = x

    def set_function(self, m: float, c: float, x: str):
        """! Function to change the model of the linear model.
        Changes the linear model based on the given slope and offset.
        @param m: The slope of the linear model
        @param c: The offset of the linear model
        @param x: Name of the x-axis variable in the watched object (i.e. the rocket)
        """
        self.m = m
        self.c = c
        self.x = x

    def apply_model(self, input_state: dict):
        """! Function to use the model to return a value.
        Returns the value of the model at the given input value.
        @param obj: The object to be watched by the model. The object must contain the variable given at initialization of the model.
        @return The output value of the model corresponding to the given input value.
        """
        return self.m * input_state[self.x] + self.c


class Fluid_Constant(Model):
    """! This class models a constant behaviour for a fluid flow."""

    def __init__(self, m_p: float, temperature: float, pressure: float):
        """! Constructor of the constant fluid model.
        @param m_p: Mass flow rate of the fluid in kg/s
        @param temperature: Temperature of the fluid in K
        @param pressure: Pressure of the fluid in Pa
        """
        self.m_p = m_p
        self.temperature = temperature
        self.pressure = pressure

    def set_values(self, m_p: float, temperature: float, pressure: float):
        """! Function to change the values of the fluid model.
        Changes the values of the fluid model based on the given values.
        @param m_p: Mass flow rate of the fluid in kg/s
        @param temperature: Temperature of the fluid in K
        @param pressure: Pressure of the fluid in Pa
        """
        self.m_p = m_p
        self.temperature = temperature
        self.pressure = pressure

    def apply_model(self, input_state: dict):
        """! Function to return the values of the fluid model.
        Returns the values of the fluid model.
        @param input_state: The input state of the fluid
        @return The output state of the fluid.
        """
        return {"massflow": self.m_p, "temperature": self.temperature, "pressure": self.pressure}


class Fluid_Linear(Model):
    """! This class models a linear behaviour for a fluid flow."""

    def __init__(
        self,
        m_p_m: float,
        m_p_c: float,
        T_m: float,
        T_c: float,
        P_m: float,
        P_c: float,
    ):
        """! Constructor of the linear fluid model.
        @param m_p_m: Linear coefficient of the mass flow rate
        @param m_p_c: Constant offset of the mass flow rate
        @param T_m: Linear coefficient of the temperature
        @param T_c: Constant offset of the temperature
        @param P_m: Linear coefficient of the pressure
        @param P_c: Constant offset of the pressure
        """
        self.m_p_m = m_p_m
        self.m_p_c = m_p_c
        self.T_m = T_m
        self.T_c = T_c
        self.P_m = P_m
        self.P_c = P_c

    def set_values(
        self,
        m_p_m: float,
        m_p_c: float,
        T_m: float,
        T_c: float,
        P_m: float,
        P_c: float,
    ):
        """! Function to change the values of the fluid model.
        Changes the values of the fluid model based on the given values.
        @param m_p_m: New linear coefficient of the mass flow rate
        @param m_p_c: New constant offset of the mass flow rate
        @param T_m: New linear coefficient of the temperature
        @param T_c: New constant offset of the temperature
        @param P_m: New linear coefficient of the pressure
        @param P_c: New constant offset of the pressure
        """
        self.m_p_m = m_p_m
        self.m_p_c = m_p_c
        self.T_m = T_m
        self.T_c = T_c
        self.P_m = P_m
        self.P_c = P_c

    def apply_model(self, input_state: dict):
        """! Function to return the values of the fluid model.
        Returns the values of the fluid model.
        @param input_state: The input state of the fluid
        @return The output state of the fluid.
        """
        output_state = {}
        output_state["massflow"] = self.m_p_m * input_state["massflow"] + self.m_p_c
        output_state["temperature"] = self.T_m * input_state["temperature"] + self.T_c
        output_state["pressure"] = self.P_m * input_state["pressure"] + self.P_c
        return output_state


class ISP_CEA_Biprop(Model):
    """! This class models the ISP of a bipropellant engine using the CEA library."""
    def __init__(self,engineEfficiency:float):
        """! Constructor of the CEA bipropellant ISP model.
        Initializes the CEA library and the engine efficiency.
        """
        self.cea = None
        self.engine_efficiency = engineEfficiency # set the engine efficiency

    def apply_model(self,input_state:dict,input_parameters:dict):
        """! Function to calculate the ISP of the engine.
        Calculates the ISP of the engine using the CEA library.
        @param input_state: The input state of the engine
        @return The ISP of the engine.
        """
        if self.cea == None:                        # check if the CEA object is initialized
                self.cea = CEA(                     #initialize CEA object with the given propellants
                    oxName=input_parameters["oxidizer"],
                    fuelName=input_parameters["fuel"],
                    fac_CR=None, units="metric")
                
        if input_state["P_cc"] > 0:                 # check if the chamber pressure is greater than 0
            isp = self.engine_efficiency * self.cea.estimate_Ambient_Isp(Pc=input_state["P_cc"],
                                                                         MR=input_state["O/F"] , 
                                                                         eps=input_parameters["expansion_ratio_nozzle"],
                                                                         Pamb=input_state["P_amb"],
                                                                         frozen=0,
                                                                         frozenAtThroat=1)[0]
        else: # if the chamber pressure is 0, the ISP is set to 0
            isp = 0        
        return isp
    
class ISP_CEA_Solid(Model):
    """! This class models the ISP of a solid rocket engine using the CEA library."""

    def __init__(self):
        self.cea = None  # initialize CEA object

    def apply_model(self, input_state: dict):
        """! Function to calculate the ISP of the engine.
        Calculates the ISP of the engine using the CEA library.
        @param input_state: The input state of the engine
        @return The ISP of the engine.
        """
        if self.cea == None:  # check if the CEA object is initialized
            self.cea = CEA(  # initialize CEA object with the given propellants
                PropName=input_state["Prop"], fac_CR=None, units="metric"
            )
        if (
            input_state["P_cc"] > 0
        ):  # check if the chamber pressure is greater than 0
            isp = self.cea.estimate_Ambient_Isp(
                Pc=input_state["P_cc"],
                MR=input_state["O/F"],
                eps=input_state["expansion_ratio_nozzle"],
                Pamb=input_state["P_amb"],
                frozen=0,
                frozenAtThroat=1,
            )[0]
        else:  # if the chamber pressure is 0, the ISP is set to 0
            isp = 0
        return isp
