# HyTEMPO (HyEnD Trajectory EstiMation and Parameter Optimization)

HyTEMPO is a project aimed to provide accurate trajectory estimations and efficient parameter optimazation for our rockets. 

## About HyTEMPO

### Scope
HyTEMPO is a basic trajectory estimator that can be used to optimize rocket parameters subject to certain conditions.
While keeping things simple, HyTEMPO is still aimed to provide relatively accurate estimates for the rockets performance.

### Usage
The notebook ```LiquidRocketStudy.ipynb``` provides an example how HyTEMPO is intended to be used. For a given engine, mass budgets and other design parameters, the rocket class is able to compute most other properties of the rocket starting from those the initial parameters - e.g. the tank volumes, propellant masses, most of the structural mass. The ```TrajectoryEstimator``` class then performs the time integration of the 2D equations of motion.

### Assumptions and limitations
Internally, HyTEMPO runs with several assumptions. First, the atmosphere is assumed to be an ICAO standard atmosphere with no wind. The flight of the rocket is assumed to be perfectly stable. The engine thrust is computed using isentropic expansion with an isentropic coefficient taken from RPA; during the burn time of the rocket the mass flows are assumed to be constant. The drag of the rocket is interpolated using a look-up table: for a wide range of $\frac{l}{d}$ and Mach numbers, $c_d$ values were precomputed and saved in ```sim_results/CD_Map.csv``` (those two parameters were found to have the largest influence on the drag coefficients).

## Quickstart

- Clone the repository:

With https:
  ```bash
  git clone https://github.tik.uni-stuttgart.de/IRS-HyEnD/HyTEMPO.git
  ```

With ssh:
  ```bash
  git clone git@github.tik.uni-stuttgart.de:IRS-HyEnD/HyTEMPO.git
  ```

  <details>
  <summary>Should I choose https or ssh?</summary>
  You can clone the repository over https or ssh. Use https if you only want to obtain the code. Use ssh if you are a registered as developer on the repository and want to push changes to the code base.</details>

- Install [poetry](https://python-poetry.org/docs/):
  
  ```bash
  curl -sSL https://install.python-poetry.org | python3 -
  ```
  
- Install HyTEMPO:

In the HyTEMPO folder, run

  ```bash
  poetry install --with=dev
  ```
## Maintaining the repository

Here are the most important infos on how to maintain this repository.

### Dependency Management with Poetry

We use poetry as build system, for the dependency management and the virtual environment. During the [Quickstart](#quickstart) we installed all dependencies into the virtual environment, therefore:

---
**IMPORTANT**

Run all commands in the next section in the poetry shell. It can be started with `poetry shell`. Alternatively you can run commands with `poetry run <yourcommand>`.

---

Run ```poetry add package_name``` to add the library/package with the name ```package_name``` as dependencie to your project. Use ```poetry add --group dev package_name``` to add ```package_name``` to your ```dev``` dependencies. You can have arbitrary group names.
  
For more information read the [Poetry Documentation](https://python-poetry.org/docs/basic-usage/#initialising-a-pre-existing-project).
