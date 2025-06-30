import math
import os
import inspect
import numpy as np
from scipy.optimize import root_scalar
from CoolProp.CoolProp import PropsSI
from pycea import CEA
from scipy.stats import qmc
from hytempo.core import components, models,engine,rocket
import h5py


class RocketFactory():
    """! This is the abstract base class for all rocket factories. It defines the interface for all factories."""

    def __init__(self):
        pass

    def build_swarm(self):
        pass

    def build_rocket(self):
        pass

    def get_pressurant_volume(self,
                              tank_vol: float,
                              tank_pressure: float,
                              pressurant_pressure_init: float,
                              pressurant_temperature_init: float,
                              pressurant: str):
        """! Calculates the pressurant and volume for a given tank volume, pressure and temperature.
        Ideal gas is assumed for the pressurant.
        @param tank_vol: Volume of the tank
        @param tank_pressure: Pressure of the tank
        @param pressurant_pressure_init: Initial pressure of the pressurant
        @param pressurant_temperature_init: Initial temperature of the pressurant
        @param pressurant: Name of the pressurant
        @return: pressurant volume
        """

        "Pressure margin in pressurant tank at EOL"
        pressure_margin = 1.2
        p_p_eol = pressure_margin * tank_pressure

        def pressurant_residual(V_p:float):
            # Initialize thermodynamic state in pressurant tank
            p_p = pressurant_pressure_init
            rho_p = PropsSI('DMASS',
                               'P', pressurant_pressure_init,
                               'T', pressurant_temperature_init,
                               pressurant)
            m_p = rho_p * V_p
            H_p = (PropsSI('HMASS',
                               'P', pressurant_pressure_init,
                               'T', pressurant_temperature_init,
                               pressurant)
                   * m_p)

            # Initialize thermodynamic state in propellant tank
            m_t = 0     # Assume no pressurant in propellant tank initially
            H_t = 0     # Assume no pressurant in propellant tank initially
            V_t = 0

            # Set mass increment
            dm = m_p / 1e3

            # Loop, end pressure is reached
            while p_p > p_p_eol:
                # Substract mass increment from pressurant tank
                H_p -= dm * H_p/m_p
                m_p -= dm

                # New pressurant pressure from new density and new enthalpy
                rho_p = m_p / V_p
                p_p = PropsSI('P',
                              'DMASS', rho_p,
                              'HMASS', H_p/m_p,
                              pressurant)

                # Add mass increment to propellant tank
                m_t += dm
                H_t += dm * H_p/m_p

                # New pressurant volume in propellant tank
                V_t = m_t / PropsSI('DMASS',
                                    'P', tank_pressure,
                                    'HMASS', H_t / m_t,
                                    pressurant)
            # Residual: tank volume - expelled volume
            return tank_vol - V_t

        # Optimization: find correct pressurant volume, such that residual vanishes
        # Initial guesses are an overestimation, which fits the residual definition
        # sol = root_scalar(pressurant_residual, method="brentq", bracket=[tank_vol/100, tank_vol])
        sol = root_scalar(pressurant_residual, x0=tank_vol/10, x1=tank_vol/2)

        pressurant_vol = sol.root

        return pressurant_vol

    def get_pressurant_vol(self,
                           tank_vol:float,
                           tank_pressure:float,
                           pressurant_pressure_init:float,
                           pressurant_temp_init:float,
                           pressurant_coolprop:str):
            
        #pressurant_coefficent_exp= PropsSI("ISENTROPIC_EXPANSION_COEFFICIENT","T",pressurant_temp_init,"P",pressurant_pressure_init,pressurant_coolprop)
        pressurant_coefficent_exp= 1 # Isothermic expansion
        pressurant_density_init = PropsSI("DMASS","T",pressurant_temp_init,"P",pressurant_pressure_init,pressurant_coolprop)
        pressurant_density_exp = (
            math.pow(
                (tank_pressure / pressurant_pressure_init),
                (1 / pressurant_coefficent_exp),
            )
            * pressurant_density_init
        )
        pressurant_vol = (tank_vol) / (
            (pressurant_density_init / pressurant_density_exp) - 1
        )
        return pressurant_vol

    def get_fluid_mass(
        self,
        fluid_vol: float,
        fluid_temp: float,
        fluid_pressure: float,
        fluid_coolprop: str,
    ):
        fluid_density = PropsSI(
            "DMASS", "T", fluid_temp, "P", fluid_pressure, fluid_coolprop
        )
        fluid_mass = fluid_vol * fluid_density
        return fluid_mass

    def create_hull_tube(
        self,
        component_list: list,
        diameter: float,
        wall_thickness: float = 0.002,
        density_material: float = 1600,
    ):
        hull_length = 0
        for component in component_list:
            hull_length += component.get_hull_length()
        outer_rad = diameter / 2
        inner_rad = outer_rad - wall_thickness
        hull_mass = (
            hull_length
            * math.pi
            * (math.pow(outer_rad, 2) - math.pow(inner_rad, 2))
            * density_material
        )
        hull_tube = components.Component(
            name="Hull Tube",
            mass=hull_mass,
            length=hull_length,
            hulltube=False,
        )
        return hull_tube
    
    def createTank(self,
                    fluid:str,
                    fluidCoolprop:str,
                    rocketDiameter:float,
                    safety:float,
                    volumeTank:float,
                    pressure:float,
                    temperature:float,
                    massflow:float,
                    fluidMass:float,
                    thicknessEndCap:float,
                    tensileStrength:float,
                    layerThicknessCfk:float,
                    ulage:float,
                    Input:components.Component):
        #Calculate the volume including the ullage
        volumeTank = volumeTank * (1 + ulage)                                   
        #Calculate cfk thickness by using Barlow's formula for cylindrical pressure vessels.
        thicknessCfk = pressure * rocketDiameter*safety / (2*tensileStrength)
        # Round up thicknessCfk to the next multiple of layerThicknessCfk
        thicknessCfk = math.ceil(thicknessCfk / layerThicknessCfk) * layerThicknessCfk
        # Calculate the inner diameters of the tank
        innerDiameterCylinder = rocketDiameter - (2 * thicknessCfk)
        innerDiameterSphere = innerDiameterCylinder - (2 * thicknessEndCap)
        #Calculate the max. volume of a spherical tank
        innerVolumeSphere = (4 / 3 * math.pi * math.pow(innerDiameterSphere / 2, 3))
        #Checking if the tank is a cylinder or a sphere"
        if (volumeTank - innerVolumeSphere) <= 0:
            "Spherical tank is sufficient for the given volume. The barlows formula for spherical vessels is not used even if the tank is spherical because the thickness would be unrealisticly small."
            #Calculate the required inner diameter of the sphere
            innerDiameterSphere = math.pow(6 * volumeTank / math.pi, 1 / 3)
            # update inner volume of the sphere
            innerVolumeSphere = volumeTank
            innerDiameterCylinder = (innerDiameterSphere + 2 * thicknessEndCap)
            diameter = innerDiameterCylinder + 2 * thicknessCfk
            innerVolumeCylinder = 0
        else:
            "spherical tank is not sufficient for the given volume, a cylinder is needed"
            # outer diameter is the rocket diameter
            diameter = rocketDiameter
            #get the volume of the cylindrical section
            innerVolumeCylinder = volumeTank - innerVolumeSphere
        "Calculating the cylinder section"
        innerAreaCylinder = math.pi * math.pow(innerDiameterCylinder / 2, 2)
        heightCylinder = innerVolumeCylinder / innerAreaCylinder
        
        "Calculating the component volumes"
        # Volume Alucap is the difference between the inner spherical tank and the cylindrical tank section diamter
        volumeAluCap = 4 / 3 * math.pi * math.pow(innerDiameterCylinder / 2, 3)- innerVolumeSphere
        # Volume CFK cap is the difference between the outer spherical tank and cylindrical tank section diamter
        volumeCfkCap = 4 / 3 * math.pi * (math.pow(diameter/2, 3)- math.pow(innerDiameterCylinder/2, 3))
        # Volume CFK cylinder is the difference between the outer cylindrical tank and the inner cylindrical tank section diamter * the cylindrical height
        volumeCfkCylinder = heightCylinder * (
                                (math.pi * math.pow(diameter / 2, 2))
                                -(math.pi * math.pow(innerDiameterCylinder / 2, 2))
                                )

        "Calculating the masses of the components"
        massAluCap = volumeAluCap * 2700
        massCfkCap = volumeCfkCap * 1600
        massCfkCylinder = volumeCfkCylinder * 1600
        tank_mass = massAluCap + massCfkCap + massCfkCylinder

        "Creating the tank"
        tank_model = models.Fluid_Constant(m_p=massflow,
                                           temperature=temperature,
                                           pressure=pressure)
        tank = components.Tank(name = fluid+"tank",
                               mass=tank_mass,
                               volume= volumeTank,
                               fluid=fluid,
                               fluid_mass= fluidMass,
                               pressure=pressure,
                               temperature=temperature,
                               tank_model=tank_model,
                               length=diameter+heightCylinder,
                               input=Input
                               )
        return tank
############################################################################################################
# Implementations of the rocket factories
############################################################################################################

def check_for_default_none(func):
    def wrapper(*args, **kwargs):
        sig = inspect.signature(func)
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()

        for name, param in sig.parameters.items():
            # Check: Default is None AND argument takes that default
            if param.default is None and bound.arguments[name] is None:
                raise ValueError(f"Argument '{name}' uses default value None")

        return func(*args, **kwargs)

    return wrapper

class Liquid_CEA_TypeVTank_RegNitrous(RocketFactory):
    """! This factory builds a swarm of rockets with the following characteristics:
    - Single liquid engine with CEA isp model
    - Type V CFK tanks for fuel, oxidizer and pressurant with a constant mass flow rate and pressure
    - The Cd Coefficient is computed by 2d LUT with Mach and L/D. 
    - Regenerative Cooling of the engine with Nitrous oxide and a 10% Pressure loss
    - Variable Values for: diameter, burntime, thrust, oxidizer to fuel ratio, chamber pressure, expansion ratio, pressurant pressure factor and launch angle
    """
    def __init__(self):
        super().__init__()
        print("Setting up factory for rockets with:")
        print(" - Single liquid engine with CEA isp model")
        print(" - Type V CFK tanks for fuel, oxidizer and pressurant")
        print(" - Regenerative cooling with Nitrous oxide")

    @check_for_default_none
    def build_swarm(self,
                    hdf_file=None,
                    diameters=None,
                    burnTimes=None,
                    thrusts=None,
                    ofs=None,
                    chamberPressures=None,
                    expansionRatios=None,
                    pressurantPressureFactors=None,
                    launchAngles=None,
                    componentList: list=None,
                    fuel: str=None,
                    ox: str=None,
                    pressurant: str=None,
                    dragCoefficient: np.array=None,
                    engineMass: float=None,
                    engineLength: float=None,
                    fuelTankSafetyFactor: float = 3.0,
                    FuelTankUllage: float = 0.0,
                    oxTankSafetyFactor: float = 3.0,
                    OxTankUllage: float = 0.7,
                    pressurantTankSafetyFactor: float = 3.0,
                    thicknessEndCap: float = 0.0015,
                    cfrpTensileStrength: float = 600.0,
                    engineEfficiency: float = 0.90,
                    fuelTemp: float = 300.0,
                    oxTemp: float = 300.0,
                    pressurantTemp: float = 300.0,
                    deltaPRegen: float = 0.1,
                    deltaPLines: float = 0.01,
                    deltaPInjector: float = 0.2,
                    layerThicknessCfk: float = 0.001,
                    rail_height: float = 15.0,
                    railTipOffAngle:float = 2, # value from experience, the launch angle will be reduced by this value to integrate the rail tip off
                    nRockets: int = 0,  # default value will be overwritten later if explicitly set
                    fuelCoolpropName="",
                    oxCoolpropName="",
                    pressurantCoolpropName="",
                    ):
        """
        Constructor of the factory
        @param diameters: Lower and upper bounds of the diameters
        @param burnTimes: Lower and upper bounds of the burntimes
        @param thrusts: Lower and upper bounds of the thrusts
        @param ofs: Lower and upper bounds of the oxidizer to fuel ratios
        @param chamberPressures: Lower and upper bounds of the chamber pressures
        @param expansionRatios: Lower and upper bounds of the expansion ratios
        @param pressurantPressureFactors: Lower and upper bounds of the pressurant pressure factors
        @param launchAngles: Lower and upper bounds of the launch angles
        @param componentList: List of components
        @param fuel: Fuel fluid
        @param ox: Oxidizer fluid
        @param pressurant: Pressurant fluid
        @param dragCoefficient: Drag coefficient LUT including the axis
        @param engineMass: Mass of the engine
        @param engineLength: Length of the engine, only specify if the length of the engine contributes to the length of the rocket
        @param fuelTankSafetyFactor: Safety factor of the fuel tank
        @param oxTankSafetyFactor: Safety factor of the oxidizer tank
        @param pressurantTankSafetyFactor: Safety factor of the pressurant tank
        @param thicknessEndCap: Thickness of the aluminium end cap of the tank, defaults to 0.0015m
        @param cfrpTensileStrength: Tensile strength of the CFK, defaults to 600MPa
        @param engineEfficiency: Efficiency of the engine, defaults to 0.9
        @param fuelTemp: Temperature of the fuel, defaults to 300K
        @param oxTemp: Temperature of the oxidizer, defaults to 300K
        @param pressurantTemp: Temperature of the pressurant, defaults to 300K
        @param deltaPRegen: Pressure loss in the regenerative cooling, defaults to 0.1
        @param deltaPLines: Pressure loss in the lines, defaults to 0.01
        @param fuelCoolpropName: Coolprop name of the fuel,only specify if the coolprop name is different from the fuel name in CEA, defaults to an empty string
        @param oxCoolpropName: Coolprop name of the oxidizer,only specify if the coolprop name is different from the oxidizer name in CEA, defaults to an empty string
        @param pressurantCoolpropName: Coolprop name of the pressurant,only specify if the coolprop name is different from the pressurant name in CEA, defaults to an empty string
        """

        # Perform the LHS to get samples of the parameters
        # Create an array of the parameters
        parameterList = [diameters,
                         burnTimes,
                         thrusts,
                         ofs,
                         chamberPressures,
                         expansionRatios,
                         pressurantPressureFactors,
                         launchAngles
                         ]
        # Determine the dimension the sample space
        VarParamIndex = [
            i for i, param in enumerate(parameterList) if isinstance(param, list)
        ]
        dimSampleSpace = len(VarParamIndex)

        # Determine the number of rockets to build
        if nRockets == 0: #if nRockets is not explicitly set, use a default value 
            nRockets = dimSampleSpace * 10 # cons
            
        elif  dimSampleSpace == 0 and nRockets == 0: 
            nRockets = 1 # if no variable parameters are given, only one rocket is built

        # Check if the sample space has any variable parameters
        if dimSampleSpace > 0:
            # Create the LHS sampler
            sampler = qmc.LatinHypercube(d=dimSampleSpace)
            # Create the sample
            sample = sampler.random(n=nRockets)
            # scale the sample to the bounds
            # Create  bounds from all lists in parameterList
            l_bounds = [parameterList[i][0] for i in VarParamIndex]
            u_bounds = [parameterList[i][1] for i in VarParamIndex]
            rocketsParametersDynamic = qmc.scale(sample, l_bounds, u_bounds)
        # create the full parameter list for the rockets
        rocketsParameters = []
        for i in range(nRockets):
            rocketParameter = []
            for j, param in enumerate(parameterList):
                if j in VarParamIndex:
                    # varaible parameter, get the parameter from the sample
                    rocketParameter.append(rocketsParametersDynamic[i][VarParamIndex.index(j)])
                else:
                    # static paramter get the parameter from the list
                    rocketParameter.append(param)
            rocketsParameters.append(rocketParameter)
        # write the variable and constant parameters to the hdf5 file
        # Create an attribute set describing variable and static parameters
        attribute_set = {}
        for idx, param in enumerate(parameterList):
            param_name = [
                "diameter", "burnTime", "thrust", "of", "chamberPressure",
                "expansionRatio", "pressurantPressureFactor", "launchAngle"
            ][idx]
            if isinstance(param, list):
                attribute_set[param_name] = {
                    "variable": True,
                    "range": (param[0], param[1])
                }
            else:
                attribute_set[param_name] = {
                    "variable": False,
                    "value": param
                }


        # set static parameters
        # Cd Coefficient LUT 
        LUTdragCoefficient = {"x":dragCoefficient[1:,0],
                            "y":dragCoefficient[0,1:],
                            "Lut":dragCoefficient[1:, 1:]
                            }
        # create PyCea object for calculating of massflow
        cea = CEA(oxName= ox,fuelName= fuel, fac_CR=None, units="metric")
        #coolprop names of propellant and pressurant
        if not fuelCoolpropName:
            fuelCoolpropName = fuel
        if not oxCoolpropName:
            oxCoolpropName = ox
        if not pressurantCoolpropName:
            pressurantCoolpropName = pressurant
    
        #create the rocket list
        rockets = []
        print("Start building rockets!")
        for i , rocketParameters in enumerate(rocketsParameters):
            print("Buildung rocket: ",i+1," of ",nRockets)
            #set the dynamic parameters of the rocket
            diameter = rocketParameters[0]
            burnTime = rocketParameters[1]
            thrust = rocketParameters[2]
            of = rocketParameters[3]
            chamberPressure = rocketParameters[4]
            expansionRatio = rocketParameters[5]
            pressurantPressureFactor = rocketParameters[6]
            launchAngle = rocketParameters[7]

            ##calculate the tanks sizes and pressures
            #get the isp for the given parameters
            isp = engineEfficiency * cea.estimate_Ambient_Isp(Pc=chamberPressure,
                                    MR=of,
                                    eps=expansionRatio,
                                    Pamb= 101325,
                                    frozen=0, 
                                    frozenAtThroat=1)[0]
            #calculate the mass flow from the thrust and isp
            massflow = thrust / (isp *9.81)

            # calculate individual mass flows
            fuelMassFlow = massflow/(of+1)
            oxMassFlow = massflow/(1/of+1)

            # calculate the propellant masses
            fuelMass = fuelMassFlow * burnTime
            oxMass = oxMassFlow * burnTime

            # calculate the propellant tank pressures
            fuelTankPressure = (chamberPressure * 
                                (1 + deltaPLines) * 
                                (1 + deltaPInjector))
            oxTankPressure = (chamberPressure *
                              (1 + deltaPLines) *
                              (1 + deltaPRegen) *
                              (1 + deltaPInjector))

            # calculate the propellant tank volumes
            fuelDensity = PropsSI("DMASS",
                                                   "T",fuelTemp,
                                                   "P",fuelTankPressure,
                                                   fuelCoolpropName)
            fuelTankVolume = fuelMass / fuelDensity * (1 + FuelTankUllage) 

            oxDensity = PropsSI("DMASS",
                                                "T",oxTemp,
                                                "P",oxTankPressure,
                                                oxCoolpropName)
            oxTankVolume = oxMass / oxDensity * (1 + OxTankUllage) 
            # calculate the propellant tank pressures
            pressurantTankPressure = max(fuelTankPressure, oxTankPressure) * pressurantPressureFactor
            pressurantTankVolumeOX = self.get_pressurant_volume(
                tank_vol=oxTankVolume,
                tank_pressure=oxTankPressure,
                pressurant_pressure_init=pressurantTankPressure,
                pressurant_temperature_init=pressurantTemp,
                pressurant=pressurantCoolpropName
            )
            pressurantTankVolumeFuel = self.get_pressurant_volume(
                tank_vol=fuelTankVolume,
                tank_pressure=fuelTankPressure,
                pressurant_pressure_init=pressurantTankPressure,
                pressurant_temperature_init=pressurantTemp,
                pressurant=pressurantCoolpropName
            )
            pressurantTankVolume = pressurantTankVolumeOX + pressurantTankVolumeFuel
            # calculate the pressurant mass
            pressurantMass = pressurantTankVolume * PropsSI("DMASS",
                                                            "T",pressurantTemp,
                                                            "P",pressurantTankPressure,
                                                            pressurantCoolpropName)
            
            ##calculate the pressurant massflow
            # get the volume flow rates of the propellants
            VolFlowFuel = fuelMassFlow / PropsSI("DMASS",
                                                        "T",fuelTemp,
                                                        "P",fuelTankPressure,
                                                        fuelCoolpropName)
            VolFlowOx = oxMassFlow / PropsSI("DMASS",
                                                        "T",oxTemp,
                                                        "P",oxTankPressure,
                                                        oxCoolpropName)
            VolFlowPressurant = VolFlowFuel + VolFlowOx 

            # calculate the pressurant mass flow rate
            pressurantMassFlow = VolFlowPressurant * PropsSI("DMASS",
                                                                "T",pressurantTemp,
                                                                "P",pressurantTankPressure,
                                                                pressurantCoolpropName)
            #create the metadata set for the rocket
            rocketParameters = {"diameter": diameter,
                                "burnTime": burnTime,
                                "thrust": thrust,
                                "of": of,
                                "chamberPressure": chamberPressure,
                                "expansionRatio": expansionRatio,
                                "pressurantTankPressure": pressurantTankPressure,
                                "launchAngle": launchAngle-railTipOffAngle, # reduce the launch angle by the rail tip off angle
                                }
            # build the rocket
            rocketSample = self.build_rocket(name = "Rocket_"+str(i), 
                                             burnTime=burnTime,
                                       componentList=componentList,
                                       cfrpTensileStrength=cfrpTensileStrength,
                                       deltaPLines=deltaPLines,
                                       deltaPRegen=deltaPRegen,
                                       deltaPInjector=deltaPInjector,
                                       diameter=diameter,
                                       dragCoefficient=LUTdragCoefficient,
                                       engineEfficiency=engineEfficiency,
                                       engineLength=engineLength,
                                       engineMass=engineMass,
                                       expansionRatio=expansionRatio,
                                       fuel=fuel,
                                       fuelCoolpropName=fuelCoolpropName,
                                       fuelMass=fuelMass,
                                       fuelMassFlow=fuelMassFlow,
                                       fuelTankPressure=fuelTankPressure,
                                       fuelTankSafetyFactor=fuelTankSafetyFactor,
                                       fuelTankVolume=fuelTankVolume,
                                       fuelTemp=fuelTemp,
                                       ox=ox,
                                       oxCoolpropName=oxCoolpropName,
                                       oxMass=oxMass,
                                       oxMassFlow=oxMassFlow,
                                       oxTankPressure=oxTankPressure,
                                       oxTankSafetyFactor=oxTankSafetyFactor,
                                       oxTankVolume=oxTankVolume,
                                       oxTemp=oxTemp,
                                       pressurant=pressurant,
                                       pressurantCoolpropName=pressurantCoolpropName,
                                       pressurantMass=pressurantMass,
                                       pressurantMassFlow=pressurantMassFlow,
                                       pressurantTankPressure=pressurantTankPressure,
                                       pressurantTankSafetyFactor=pressurantTankSafetyFactor,
                                       pressurantTankVolume=pressurantTankVolume,
                                       pressurantTemp=pressurantTemp,
                                       rail_height=rail_height,
                                       rocketParameters=rocketParameters,
                                       thicknessEndCap=thicknessEndCap,
                                       layerThicknessCfk=layerThicknessCfk,
                                       )
            rockets.append(rocketSample)
        return rockets
              
    def build_rocket(self,
                     name:str,
                    burnTime: float,
                    componentList: list,
                    cfrpTensileStrength: float,
                    deltaPLines: float,
                    deltaPRegen: float,
                    deltaPInjector: float,
                    diameter: float,
                    dragCoefficient:dict,
                    engineEfficiency: float,
                    engineLength: float,
                    engineMass: float,
                    expansionRatio: float,
                    fuel:str,
                    fuelCoolpropName:str,
                    fuelMass: float,
                    fuelMassFlow: float,
                    fuelTankPressure: float,
                    fuelTankSafetyFactor: float,
                    fuelTankVolume: float,
                    fuelTemp: float,
                    ox:str,
                    oxCoolpropName:str,
                    oxMass: float,
                    oxMassFlow: float,
                    oxTankPressure: float,
                    oxTankSafetyFactor: float,
                    oxTankVolume: float,
                    oxTemp: float,
                    pressurant:str,
                    pressurantCoolpropName:str,
                    pressurantMass:float,
                    pressurantMassFlow: float,
                    pressurantTankPressure: float,
                    pressurantTankSafetyFactor: float,
                    pressurantTankVolume: float,
                    pressurantTemp: float,
                    rail_height: float,
                    rocketParameters: dict,
                    thicknessEndCap: float,
                    layerThicknessCfk: float,
                    ):
        parts = []
        for part in componentList:
            parts.append(part)
        pressurant_tank = self.createTank(fluid=pressurant,
                                        fluidCoolprop = pressurantCoolpropName,
                                        rocketDiameter=diameter,
                                        safety=pressurantTankSafetyFactor,
                                        volumeTank = pressurantTankVolume,
                                        pressure=pressurantTankPressure,
                                        temperature= pressurantTemp,
                                        massflow=pressurantMassFlow,
                                        fluidMass=pressurantMass,
                                        thicknessEndCap=thicknessEndCap,
                                        tensileStrength=cfrpTensileStrength,
                                        layerThicknessCfk=layerThicknessCfk,
                                        ulage=0.0,
                                        Input=None
                                        )
        fuel_tank = self.createTank(fluid=fuel,
                                    fluidCoolprop = fuelCoolpropName,
                                    rocketDiameter=diameter,
                                    safety=fuelTankSafetyFactor,
                                    volumeTank = fuelTankVolume,
                                    pressure=fuelTankPressure,
                                    temperature= fuelTemp,
                                    massflow = fuelMassFlow,
                                    fluidMass = fuelMass,
                                    thicknessEndCap=thicknessEndCap,
                                    tensileStrength=cfrpTensileStrength,
                                    layerThicknessCfk=layerThicknessCfk,
                                    Input = pressurant_tank,
                                    ulage=0.01
                                    )
        ox_tank = self.createTank(fluid=ox,
                                    fluidCoolprop = oxCoolpropName,
                                    rocketDiameter=diameter,
                                    safety=oxTankSafetyFactor,
                                    volumeTank = oxTankVolume,
                                    massflow=oxMassFlow,
                                    temperature= oxTemp,
                                    fluidMass=oxMass,
                                    pressure=oxTankPressure,
                                    thicknessEndCap=thicknessEndCap,
                                    tensileStrength=cfrpTensileStrength,
                                    layerThicknessCfk=layerThicknessCfk,
                                    Input = pressurant_tank,
                                    ulage=0.1
                                    )
        
        #write tanks into tank list
        tanks = [fuel_tank,ox_tank,pressurant_tank]
        
        #create the propellant lines
        LineModel = models.Fluid_Linear(m_p_m=1,m_p_c=0,
                                            T_m=1,T_c=0,
                                            P_m=1-deltaPLines,P_c=0)
        fuelLine = components.Wetted_part(name="Fuel Line",
                                             mass=0.4,
                                             length=0.2,
                                             input=fuel_tank,
                                             model=LineModel,
                                             hulltube=True)
        oxLine = components.Wetted_part(name="Oxidizer Line",
                                             mass=0.4,  
                                             length=0.2,  
                                             input=ox_tank,
                                             model=LineModel,
                                             hulltube=True)
        #add to components list
        parts.append(fuelLine)
        parts.append(oxLine)
        
        #create the regenerative cooling componenent
        regModel = models.Fluid_Linear(m_p_m=1, m_p_c=0,
                                       T_m=1, T_c=0,
                                       P_m=1-deltaPRegen, P_c=0)
        reg_cooling = components.Wetted_part(name="Regenerative Cooling",
                                                mass=0.0,  # Placeholder mass
                                                length=0.0,  # Placeholder length
                                                input=ox_tank,
                                                model=regModel,
                                                hulltube=False)
        #add to components list
        parts.append(reg_cooling)

        #create the injector
        injectorModel = models.Fluid_Linear(m_p_m=1, m_p_c=0,
                                            T_m=1, T_c=0,
                                            P_m=1-deltaPInjector, P_c=0)
        injectorFuel = components.Wetted_part(name="Injector Fuel",
                                                mass=0.0,  # Placeholder mass
                                                length=0.0,  # Placeholder length
                                                input=fuelLine,
                                                model=injectorModel,
                                                hulltube=False)
        injectorOx = components.Wetted_part(name="Injector Oxidizer",
                                                mass=0.0,  # Placeholder mass
                                                length=0.0,  # Placeholder length
                                                input=reg_cooling,
                                                model=injectorModel,
                                                hulltube=False)
        #add injector to components list
        parts.append(injectorFuel)
        parts.append(injectorOx)    

        #create rocket engine
        isp_model = models.ISP_CEA_Biprop(engineEfficiency=engineEfficiency)
        rocket_engine = engine.Liquid_engine(name="Engine",
                                             mass=engineMass,
                                             expansion_ratio_nozzle=expansionRatio,
                                             input_oxidizer=injectorOx,
                                             input_fuel=injectorFuel,
                                             isp_model=isp_model)
        
        "add engine to engine list"
        engines = [rocket_engine]
        "Build rocket"
        "combine all components into a full component list"
        full_components = parts+[self.create_hull_tube(component_list=parts+engines+tanks,diameter=diameter)]
        drag_model = models.Scalar_LUT2D(table= dragCoefficient["Lut"],
                                        xAxis= dragCoefficient["x"],
                                        yAxis= dragCoefficient["y"],
                                        x="Ma",
                                        y="L/D")
        finished_rocket = rocket.Rocket(name=name,
                                        rail_height = rail_height,
                                        component_list=full_components,
                                        tank_list=tanks,
                                        engine_list=engines,
                                        drag_model=drag_model,
                                        parameters = rocketParameters)
        return finished_rocket 