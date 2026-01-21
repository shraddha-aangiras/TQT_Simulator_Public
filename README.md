# TQT Photonic Quantum Technologies Python Control Code


## Installation
Install all dependencies with `pip install -r requirements.txt`.
Using a virtual environment is recommended, to avoid potential dependency issues.
Other dependencies that must be installed separately are: VISA.

Currently, `pythonnet`,
which provides the .NET framework, does not currently support Python 3.9. and throws an error
when installing via `pip install pythonnet`. Using `pip install --pre pythonnet` instead seems to 
solve the issue.

## Main files
* `experiment.py` defines a single high-level class for controlling the laser, time-tagger, 
and optical power meter
* `interface.py` provides a graphical window for controlling the laser and time-tagger,
while also plotting the single photon counts and optical power
* `example.ipynb` provides an example of how to script measurements
* `config.yaml` stores the hardware address (ports), which must be adapted to the current setup

## Discovering hardware addresses
To connect to the laser and power meter, the hardware address must be provided.
You can find these in the Device Manager (on Windows). 
Alternatively, run the notebook `tqt\utils\hardware.ipynb` which will list all 
serial devices (the laser) and VISA devices (the powermeter).