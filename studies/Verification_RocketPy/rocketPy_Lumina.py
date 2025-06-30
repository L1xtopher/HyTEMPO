import datetime
import os
from math import exp
from rocketpy import Environment, SolidMotor, Rocket, Flight,LiquidMotor,Fluid, LiquidMotor, CylindricalTank,SphericalTank, MassFlowRateBasedTank

#get the path to the current file
current_file_path = os.path.dirname(os.path.abspath(__file__))
drag_path = os.path.join(current_file_path,"lumina_Cd.csv")

#rocketpy tutorial
###########################################################################
env = Environment(latitude=32.990254, longitude=-106.974998, elevation=0)
tomorrow = datetime.date.today() + datetime.timedelta(days=1)
env.set_date(
    (tomorrow.year, tomorrow.month, tomorrow.day, 12)
) 
env.set_atmospheric_model(type="Forecast", file="GFS")
########################################################################### 
# Define fluids
oxidizer_liq = Fluid(name="N2O_l", density=766.644)
oxidizer_gas = Fluid(name="N2O_g", density=1.9277)
fuel_liq = Fluid(name="ethanol_l", density=789)
fuel_gas = Fluid(name="ethanol_g", density=1.59)
pressurant_gas = Fluid(name="He_g", density=32.03655)

# Define tanks geometry
ethanolTankShape = SphericalTank(radius = 0.0591272)
noxTankShape = CylindricalTank(radius = 0.062, height = 0.387277557723518, spherical_caps = True)
pressurantTankShape = CylindricalTank(radius = 0.062, height = 0.29858172538363636, spherical_caps = True)
# Define tanks
oxidizer_tank = MassFlowRateBasedTank(
    name="oxidizer tank",
    geometry=noxTankShape,
    flux_time=7,
    initial_liquid_mass=2.561638,
    initial_gas_mass=0.0,
    liquid_mass_flow_rate_in=0,
    liquid_mass_flow_rate_out=0.3659,
    gas_mass_flow_rate_in=0,
    gas_mass_flow_rate_out=0,
    liquid=oxidizer_liq,
    gas=oxidizer_gas,
)

fuel_tank = MassFlowRateBasedTank(
    name="fuel tank",
    geometry=ethanolTankShape,
    flux_time=7,
    initial_liquid_mass=0.53368,
    initial_gas_mass=0.0001,
    liquid_mass_flow_rate_in=0,
    liquid_mass_flow_rate_out=0.07624,
    gas_mass_flow_rate_in=0,
    gas_mass_flow_rate_out=0,
    liquid=fuel_liq,
    gas=fuel_gas,
)

pressurant_tank = MassFlowRateBasedTank(
    name="pressurant tank",
    geometry=pressurantTankShape,
    flux_time=[7,60],
    initial_liquid_mass=0.0,
    initial_gas_mass=0.07370127899889856,
    liquid_mass_flow_rate_in=0,
    liquid_mass_flow_rate_out=0,
    gas_mass_flow_rate_in=0,
    gas_mass_flow_rate_out=0,
    liquid=pressurant_gas,
    gas=pressurant_gas,
)
# Define the motor
example_liquid = LiquidMotor(
    thrust_source=1000,
    dry_mass=2,
    dry_inertia=(0.125, 0.125, 0.002),
    nozzle_radius=0.04,
    center_of_dry_mass_position=1.75,
    nozzle_position=0,
    burn_time=7,
    coordinate_system_orientation="nozzle_to_combustion_chamber",
)
example_liquid.add_tank(tank=oxidizer_tank, position=0.5)
example_liquid.add_tank(tank=fuel_tank, position=1.5)
example_liquid.add_tank(tank=pressurant_tank, position=2.5)

###########################################################################


lumina = Rocket(
    radius=0.062,
    mass=16.637,
    inertia=(6.321, 6.321, 0.034),
    power_off_drag=drag_path,
    power_on_drag=drag_path,
    center_of_mass_without_motor=2.0,
    coordinate_system_orientation="tail_to_nose",
)

lumina.add_motor(example_liquid, position=0)

nose_cone = lumina.add_nose(
    length=0.469, kind="von karman", position=3.6241136300203802
)

fin_set = lumina.add_trapezoidal_fins(
    n=4,
    root_chord=0.120,
    tip_chord=0.060,
    span=0.110,
    position=0.2,
    cant_angle=0.5)

tail = lumina.add_tail(
    top_radius=0.062, bottom_radius=0.0435, length=0.060, position=0.0
)
test_flight = Flight(
    rocket=lumina, environment=env, rail_length=15, inclination=85, heading=0
    )
test_flight.export_data(
    "lumina_flight_data.csv",
    "altitude",
    "x","y","z",
    "vx","vy","vz",
    "speed",
    "attitude_angle",
    "path_angle",
    "angle_of_attack"
)