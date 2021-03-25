# RAI simulator MVP

## Description

This project is a MVP for an agent-based model of RAI's market behavior. The RAI system, the Uniswap pool and the agents are represented as classes. The agents each have their own strategies and make decisions on whether they should buy, sell, provide liquidity, mint etc based on said strategy in discrete timesteps.

Currently the project is intended to be used for simulations with 1-hour timesteps.

The code is structured as follows: the ``agents`` module contains the classes defining the different kinds of agents who will interact with the different protocols in the ``protocols`` module (the RAI system itself, the Uniswap pool, later some auxiliary lending markets perhaps). The ``utils`` module is intended to contain miscellaneous utility functions as the project requires it.

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

Note: as of writing this, using LongETH agents makes the system diverge really quickly. Any feedback on why you think that might be the case is appreciated.

## Contributing

This project is open to any contribution. Please open an issue if you have anything in mind so that development can be easily coordinated. The priority in my opinion is to look for bugs and add more agents with different strategies.

## Acknowledgements

Thanks to Ameen Soleimani for the idea of an agents based model.
