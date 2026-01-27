# TQT Photonic Quantum Technologies Python Control Code

## Installation & Setup
### 1. Windows (Clickable)
* **Important:** Extract the files from the `.zip` folder first.
1. Open the `setup` folder and double-click **`install.bat`**.
2. Go back to the main folder and double-click **`run.bat`**.

### 2. macOS (Clickable)
1. Open Terminal and `cd` to the downloaded folder.
2. Run these two lines to fix permissions:
   ```bash
   xattr -c setup/*.command && chmod +x setup/*.command
   xattr -c *.command && chmod +x *.command```
3. Open the setup folder and double-click install.command.
4. Go back to the main folder and double-click run.command

### 3. Windows (Command Prompt)
1. Clone the repo and navigate to directory
2. Run the below lines to finish setup installations
    ```cd setup
    install.bat
    cd ..```
3. To run the script, use `run.bat`

### 4. macOS (Terminal)
1. Clone the repo and navigate to directory
2. Run the below lines to finish setup installations
    ```cd setup
    ./install.command
    cd ..```
3. To run the script, use `./run.command`

## Main files
* `interface.py` provides a graphical window for controlling the laser and time-tagger,
while also plotting the single photon counts and optical power
* `experiment.py` defines a single high-level class for controlling the laser, time-tagger, 
and optical power meter
* `example.ipynb` provides an example of how to script measurements