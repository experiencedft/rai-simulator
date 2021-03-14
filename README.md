# RAI simulator MVP

## Description

This project is a MVP for an agent-based model of RAI's market behavior. The RAI system, the Uniswap pool and the agents are represented as classes. The agents each have their own strategies and make decisions on whether they should buy, sell, provide liquidity, mint etc based on said strategy in discrete timesteps.

Currently the project only implements one type of agents and is intended to be used for simulations with 1-hour timesteps.

## Prerequisites

Install Python 3.7 or higher.

Install Matplotlib:

```bash
pip install matplotlib
```

Install Numpy:

```bash
pip install numpy
```

## Usage

Clone the repo.

Open the ``config.ini`` file and enter your desired simulation parameters following instructions there. Save your parameters.

Run the simulation:

```bash
python simulation.py
```

The results are saved in the ``results`` folder.
