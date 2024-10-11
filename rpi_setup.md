# Setup steps for raspberry pi image

For this you should obtain a sd card - there may be size limits, this was tested
on 32GB drive.

1. Obtain the Raspberry Pi Imager software from
   https://www.raspberrypi.com/software/ for your platform

1. Insert SD card into card slot

1. Follow the instructions on the Imager application to install recent OS on
   selected device. Here we used a Raspberry Pi 3 and the "Bookworm"
   (2024-07-04) 64 bit OS. It is preferable to setup SSH user and password here.

1. Insert the SD card into the Raspberry Pi and connect to it, either directly with
   a screen and keyboard or via SSH, if configured.

1. Issue the following command

   ```
   sudo rpi-config
   ```
   a. Select the "serial" option
   a. don't enable login (first prompt)
   a. enable the serial (second prompt)
   a. reboot

1. Login again, and ensure the following lines are in
   `/boot/firmware/config.txt`:

   * `enable_uart=1`
   * `dtoverlay=pi3-disable-bt`

   these ensure that the serial is not multiplexed with bluetooth and show up
   as `/dev/ttyAMA0`. Reboot the system.

1. Login again, now create the python environment and install evolver:

   ```
   python3 -m venv evolver
   . evolver/bin/activate
   pip install git+https://github.com/ssec-jhu/evolver-ng
   ```

   For ease of use, you can optionally add the line `. evolver/bin/activate` to
   then end of `~/.bashrc` to have the environment activate at login.

1. Add the systemd unit to run the evolver as a service at startup. Add these
   contents:

   ```
   [Service]
   Environment=EVOLVER_HOST=0.0.0.0 EVOLVER_CONFIG_FILE=/etc/evolver.yml
   ExecStart=/home/pi/evolver/bin/python -m evolver.app.main
   Restart=on-failure
   Type=exec

   [Install]
   WantedBy=multi-user.target
   ```

   To the file: `/etc/systemd/system/evolver.service`.

1. Enable and start the service:

    ```
    sudo systemctl enable evolver
    ```

    ```
    sudo systemctl start evolver
    ```

1. The service should now be running. You can use standard systemctl commands
   such as `sudo systemctl status evolver` to inspect the running application.

   You should now also be able to navigate to the address of the raspberry pi to
   interact with the api.

1. To update software, simply upgrade using pip:

    ```
    . evolver/bin/activate
    pip install --upgrade git+https://github.com/ssec-jhu/evolver-ng
    ```

    and then restart the service:

    ```
    sudo systemctl restart evolver
    ```